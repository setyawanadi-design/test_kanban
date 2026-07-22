import os
import sys
import uvicorn
import argparse
import webbrowser
import threading
import io
import csv
from typing import List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, Response, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import database

# Initialize the SQLite database
database.init_db()

app = FastAPI(title="Document Board API")

# Mount Static Files directory for index.html, style.css, script.js
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

# --- WebSocket Connection Manager ---

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections[:]:
            try:
                await connection.send_text(message)
            except Exception:
                if connection in self.active_connections:
                    self.active_connections.remove(connection)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Maintain active connection; discard incoming client messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# --- Pydantic Models for Data Sanitization & Input Validation ---

class CategoryModel(BaseModel):
    id: str = Field(..., min_length=1)
    label: str = Field(..., min_length=1)
    color: str = Field(..., min_length=4)

class ColumnModel(BaseModel):
    id: str = Field(..., min_length=1)
    label: str = Field(..., min_length=1)
    color: str = Field(..., min_length=4)
    is_intake: Optional[bool] = False

class CardModel(BaseModel):
    id: str = Field(..., min_length=1)
    text: str = Field(..., min_length=1)
    column_id: str = Field(..., min_length=1)
    category_id: str = Field(..., min_length=1)
    created_at: str

class NoteModel(BaseModel):
    id: str = Field(..., min_length=1)
    text: str

class PostDataModel(BaseModel):
    action: str = Field(..., min_length=1)
    version: Optional[int] = None

    # create action
    card: Optional[str] = None
    column_id: Optional[str] = None
    category_id: Optional[str] = None
    created_at: Optional[str] = None

    # update_cards action
    cards: Optional[List[CardModel]] = None

    # update_notes action
    notes: Optional[List[NoteModel]] = None

    # configure action
    board_title: Optional[str] = None
    columns: Optional[List[ColumnModel]] = None
    categories: Optional[List[CategoryModel]] = None

    # delete action
    card_id: Optional[str] = None

# --- Custom Root & Fallback routes to support SPAs / static serving ---

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return HTMLResponse("index.html not found", status_code=404)

# --- API Endpoints ---

@app.get("/api/data")
async def get_data():
    return database.get_board_data()

@app.post("/api/data")
async def post_data(body: PostDataModel):
    current_version = database.get_version()

    # Check if a layout sync issue occurred
    if body.version is not None and body.version != current_version:
        raise HTTPException(status_code=409, detail="Syncing layouts.")

    action = body.action
    new_version = current_version

    if action == "create":
        if not body.card or not body.column_id or not body.category_id:
            raise HTTPException(status_code=420, detail="Missing required fields for create action")
        card_id = "c-" + os.urandom(4).hex()
        created_at = body.created_at if body.created_at else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        new_version = database.add_card(card_id, body.card, body.column_id, body.category_id, created_at)

    elif action == "update_cards":
        if body.cards is None:
            raise HTTPException(status_code=420, detail="Missing cards for update_cards action")
        cards_data = [c.model_dump() for c in body.cards]
        new_version = database.update_cards_batch(cards_data)

    elif action == "delete":
        # Supports deleting via card_id
        if not body.card_id:
            raise HTTPException(status_code=420, detail="Missing card_id for delete action")
        new_version = database.delete_card(body.card_id, body.card or "", body.column_id or "")

    elif action == "configure":
        if not body.board_title or body.columns is None or body.categories is None:
            raise HTTPException(status_code=420, detail="Missing configurations parameters")
        cols = [c.model_dump() for c in body.columns]
        cats = [c.model_dump() for c in body.categories]
        new_version = database.configure_board(body.board_title, cols, cats)

    elif action == "update_notes":
        if body.notes is None:
            raise HTTPException(status_code=420, detail="Missing notes for update_notes action")
        notes_data = [n.model_dump() for n in body.notes]
        new_version = database.update_notes(notes_data)

    else:
        raise HTTPException(status_code=400, detail=f"Unsupported action: {action}")

    # Broadcast layout/card change event to all other clients in real-time!
    await manager.broadcast("reload")

    return {"ok": True, "new_version": new_version}

@app.get("/api/export")
async def export_log():
    data = database.get_board_data()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["time", "action", "card", "detail"])
    for h in data["history"]:
        writer.writerow([h.get("time", ""), h.get("action", ""), h.get("card", ""), h.get("detail", "")])

    headers = {
        "Content-Disposition": 'attachment; filename="document-board-log.csv"',
        "Content-Type": "text/csv; charset=utf-8"
    }
    return Response(content=buf.getvalue(), headers=headers)

@app.get("/api/backup")
async def backup_data():
    data = database.get_board_data()
    import json
    headers = {
        "Content-Disposition": 'attachment; filename="document-board-backup.json"',
        "Content-Type": "application/json"
    }
    return Response(content=json.dumps(data, indent=2), headers=headers)

@app.post("/api/restore")
async def restore_data(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Malformed payload")

    # Basic structural check
    if "board_title" not in body or "columns" not in body:
        raise HTTPException(status_code=420, detail="Invalid backup file layout")

    database.restore_backup(body)

    # Broadcast full restore change to all other active clients in real-time
    await manager.broadcast("reload")

    return {"ok": True}

# Mount static files handler last so that API routes take precedence
app.mount("/", StaticFiles(directory=STATIC_DIR), name="static")

def main():
    parser = argparse.ArgumentParser(description="Document Board Server - Modern Modular Architecture")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"), help="Host IP to bind the server to (use '0.0.0.0' for remote hosting)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "8825")), help="Port number to listen on")
    parser.add_argument("--no-browser", action="store_true", default=os.environ.get("NO_BROWSER", "false").lower() == "true", help="Do not automatically open a web browser")
    args = parser.parse_args()

    print(f"Starting modular document board on http://{args.host}:{args.port}...")

    # Automatically launch browser if binding to localhost/127.0.0.1 and --no-browser isn't set
    if not args.no_browser and args.host in ("127.0.0.1", "localhost"):
        threading.Timer(0.6, lambda: webbrowser.open(f"http://{args.host}:{args.port}/")).start()

    try:
        uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    except KeyboardInterrupt:
        print("\nStopping server.")
        sys.exit(0)

if __name__ == "__main__":
    main()
