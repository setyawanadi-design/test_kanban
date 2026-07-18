#!/usr/bin/env python3
"""
Document Board - Final Polish: Toolbar Shortcuts, Unified Buttons & Light Mode Contrast
"""

import json
import csv
import io
import os
import sys
import uuid
import webbrowser
import threading
import argparse
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(HERE, "board_data.json")
PORT = 8825

# Vibrant colors for Tracking
TRACKING_SWATCHES = [
    "#16a085", "#27ae60", "#2980b9", "#8e44ad",
    "#2c3e50", "#f39c12", "#d35400", "#c0392b", "#7f8c8d"
]

DEFAULT_CATEGORIES = [
    {"id": "cat_1", "label": "Standard", "color": "#2980b9"},
    {"id": "cat_2", "label": "Urgent", "color": "#c0392b"},
    {"id": "cat_3", "label": "Pending Docs", "color": "#f39c12"}
]

DEFAULT_COLUMNS = [
    {"id": "col_intake", "label": "Intake", "color": "#2b3647", "is_intake": True},
    {"id": "col_file", "label": "File", "color": "#27ae60", "is_intake": False},
    {"id": "col_handoff", "label": "Handoff", "color": "#8e44ad", "is_intake": False},
    {"id": "col_doing", "label": "Doing", "color": "#f39c12", "is_intake": False},
    {"id": "col_done", "label": "Done", "color": "#7f8c8d", "is_intake": False},
]

DEFAULT_DATA = {
    "version": 1,
    "board_title": "Document board",
    "categories": DEFAULT_CATEGORIES,
    "columns": DEFAULT_COLUMNS,
    "cards": [],
    "history": [],
    "notes": [],
}

def migrate_data(data):
    if "categories" not in data:
        data["categories"] = DEFAULT_CATEGORIES

    if "columns" not in data or any(c.get("allow_add") for c in data.get("columns", [])):
        data["columns"] = DEFAULT_COLUMNS

        migrated_cards = []
        for c in data.get("cards", []):
            target_col = "col_intake" if (c.get("column_id", "").startswith("col_receive")) else c.get("column_id", "col_intake")

            migrated_cards.append({
                "id": c.get("id", "c-" + uuid.uuid4().hex[:8]),
                "text": c.get("text", ""),
                "column_id": target_col,
                "category_id": c.get("category_id", "cat_1"),
                "created_at": c.get("created_at", now_str())
            })
        data["cards"] = migrated_cards

    for c in data.get("cards", []):
        if "created_at" not in c:
            c["created_at"] = now_str()
        if "category_id" not in c:
            c["category_id"] = "cat_1"

    clean_history = []
    for h in data.get("history", []):
        clean_history.append({
            "time": h.get("time", ""),
            "action": h.get("action", ""),
            "card": h.get("card", ""),
            "detail": h.get("detail", ""),
        })
    data["history"] = clean_history

    old_notes = data.get("notes", [])
    if isinstance(old_notes, str):
        if old_notes.strip():
            data["notes"] = [{"id": "n-" + uuid.uuid4().hex[:8], "text": old_notes}]
        else:
            data["notes"] = []

    data.setdefault("version", 1)
    data.setdefault("notes", [])
    return data

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        data = migrate_data(data)
        data.setdefault("board_title", "Document board")
        data.setdefault("categories", DEFAULT_CATEGORIES)
        data.setdefault("columns", DEFAULT_COLUMNS)
        data.setdefault("cards", [])
        data.setdefault("history", [])
        data.setdefault("notes", [])
        return data
    return json.loads(json.dumps(DEFAULT_DATA))

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log_event(data, action, card_text, detail=""):
    data["history"].append({
        "time": now_str(),
        "action": action,
        "card": card_text,
        "detail": detail,
    })

PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Document board</title>
<style>
  :root {
    --bg-main: #2b3647; --bg-col: #3b495a; --bg-header: #202835;
    --text-light: #ecf0f1; --border-subtle: rgba(255,255,255,0.08);
    --radius: 4px; --card-text: #ffffff; --meta-text: rgba(255,255,255,0.6);
    --btn-action-bg: rgba(0,0,0,0.2); --input-bg: rgba(0,0,0,0.25);
    --input-text: #fff; --note-bg: #d35400; --note-text: #fff;
  }
  body.light-theme {
    --bg-main: #0079bf; --bg-col: #cbd5e1; --bg-header: #0067a3;
    --text-light: #172b4d; --border-subtle: rgba(0,0,0,0.15);
    --card-text: #ffffff; --meta-text: rgba(255,255,255,0.8);
    --btn-action-bg: rgba(0,0,0,0.15); --input-bg: #ffffff;
    --input-text: #172b4d; --note-bg: #fff9c4; --note-text: #333;
  }

  * { box-sizing: border-box; }
  body { margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg-main); color: var(--text-light); overflow: hidden; }

  /* Modal Background Lock */
  body.modal-open main { pointer-events: none; user-select: none; opacity: 0.5; filter: blur(1px); transition: 0.15s ease; }

  header { display: flex; justify-content: space-between; align-items: center; padding: 10px 20px; background: var(--bg-header); border-bottom: 1px solid rgba(0,0,0,0.15); height: 53px; overflow-x: auto; }
  h1 { font-size: 16px; font-weight: 600; margin: 0; color: #fff; flex-shrink: 0; margin-right: 16px; }

  .header-actions { display: flex; gap: 4px; align-items: center; }
  .header-btn { height: 32px; display: flex; align-items: center; justify-content: center; gap: 6px; padding: 0 10px; border-radius: var(--radius); border: none; background: transparent; cursor: pointer; font-size: 14px; color: rgba(255,255,255,0.8); font-family: inherit; font-weight: bold; white-space: nowrap; }
  .header-btn:hover { background: rgba(255,255,255,0.15); color: #fff; }
  .header-btn span { font-size: 11px; opacity: 0.6; font-family: monospace; font-weight: normal; }

  .divider { width: 1px; height: 20px; background: var(--border-subtle); margin: 0 8px; }

  main { display: flex; gap: 16px; padding: 16px; overflow: hidden; height: calc(100vh - 53px); transition: 0.15s ease; }
  #board-scroll-area { flex: 1; min-width: 0; overflow-x: auto; overflow-y: hidden; }

  .board-wrapper { display: flex; gap: 12px; align-items: flex-start; height: 100%; min-width: 100%; }
  .board-col { flex: 0 0 280px; display: flex; flex-direction: column; background: var(--bg-col); border-radius: var(--radius); height: 100%; box-shadow: 0 1px 2px rgba(0,0,0,0.15); overflow: hidden; }
  .board-wrapper.stretched .board-col { flex: 1 1 250px; max-width: 380px; }

  /* Sticky Notes */
  #sticky-note-panel {
      width: 320px; flex-shrink: 0; display: flex; flex-direction: column;
      background: var(--bg-col); border-radius: var(--radius);
      box-shadow: -2px 4px 12px rgba(0,0,0,0.15); border-top-right-radius: 24px;
  }
  main.stretched-mode #sticky-note-panel { display: none; }
  .note-header { font-weight: bold; font-size: 13px; padding: 12px 14px; border-bottom: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center; }
  #sticky-notes-list { flex: 1; overflow-y: auto; padding: 14px; display: flex; flex-direction: column; gap: 12px; }

  .individual-note { background: var(--note-bg); color: var(--note-text); border-radius: var(--radius); padding: 12px; position: relative; box-shadow: 0 2px 5px rgba(0,0,0,0.15); }
  .individual-note-text { font-size: 13px; white-space: pre-wrap; line-height: 1.4; min-height: 20px; word-wrap: break-word; padding-bottom: 16px; }

  /* Shared Action Buttons */
  .card-actions { display: flex; gap: 4px; opacity: 0; transition: opacity 0.1s ease; }
  .card:hover .card-actions, .card:focus .card-actions, .individual-note:hover .card-actions { opacity: 1; }
  .card-btn { background: var(--btn-action-bg); border: none; color: #fff; padding: 2px 6px; border-radius: 2px; cursor: pointer; font-size: 10px; }
  .card-btn.del-btn:hover { background: #e74c3c; }
  .card-btn.edit-btn:hover { background: #3498db; }

  /* Board Internals */
  .col-head { padding: 12px 14px; font-size: 14px; font-weight: bold; display: flex; align-items: center; color: #ffffff; text-shadow: 0 1px 2px rgba(0,0,0,0.3); border-bottom: 1px solid rgba(0,0,0,0.1); }
  .drop-zone { padding: 10px; display: flex; flex-direction: column; gap: 10px; overflow-y: auto; flex: 1; }

  .card { border-radius: var(--radius); padding: 10px 12px; font-size: 14px; line-height: 1.4; color: var(--card-text); cursor: grab; position: relative; box-shadow: 0 2px 4px rgba(0,0,0,0.15); border: 1px solid rgba(0,0,0,0.1); word-wrap: break-word; white-space: pre-wrap; outline: none; transition: transform 0.1s; }
  .card:focus { outline: 2px solid #fff; outline-offset: 2px; }
  .card.keyboard-dragging { opacity: 0.8; outline: 3px dashed #fff; outline-offset: 2px; transform: scale(1.02); z-index: 10; }

  .pill-badge { display: inline-block; padding: 2px 6px; border-radius: 10px; font-size: 10px; font-weight: bold; color: #fff; margin-bottom: 6px; background: rgba(255,255,255,0.2); border: 1px solid rgba(255,255,255,0.4); }
  .card-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 8px; font-size: 11px; color: var(--meta-text); }

  .add-container { padding: 10px 10px 0 10px; display: flex; flex-direction: column; border-bottom: 1px solid var(--border-subtle); background: rgba(0,0,0,0.03); }
  .add-card-btn { border: none; background: transparent; color: #7f8c8d; font-size: 13px; text-align: left; padding: 8px; cursor: pointer; border-radius: var(--radius); width: 100%; outline: none; margin-bottom: 10px; }
  body:not(.light-theme) .add-card-btn { color: #bdc3c7; }
  .add-card-btn:focus, .add-card-btn:hover { background: rgba(0,0,0,0.05); color: var(--text-light); }

  .add-row { display: none; gap: 6px; padding-bottom: 10px; flex-direction: column; }
  .add-row.open { display: flex; }
  .add-row textarea { width: 100%; font-family: inherit; font-size: 13px; padding: 8px; border-radius: var(--radius); border: 1px solid rgba(0,0,0,0.15); background: #fff; color: #333; outline: none; resize: vertical; min-height: 55px; box-shadow: inset 0 1px 3px rgba(0,0,0,0.05); }
  .pill-selector { display: flex; gap: 6px; overflow-x: auto; padding-bottom: 4px; }
  .pill-option { padding: 4px 10px; border-radius: 12px; font-size: 11px; cursor: pointer; color: #fff; opacity: 0.5; border: 2px solid transparent; white-space: nowrap; transition: 0.1s; }
  .pill-option.selected { opacity: 1; border-color: #fff; transform: scale(1.05); }
  .btn-group { display: flex; gap: 6px; justify-content: flex-end; }
  .btn-group button { padding: 6px 14px; border-radius: var(--radius); border: none; background: #5aac44; color: #fff; cursor: pointer; font-weight: bold; font-size: 12px; }
  .btn-group .btn-cancel { background: transparent; color: #7f8c8d; }

  /* Modals */
  .overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.6); align-items: flex-start; justify-content: center; padding-top: 60px; z-index: 50; }
  .overlay.open { display: flex; }
  .modal { background: var(--bg-col); border-radius: var(--radius); width: 520px; box-shadow: 0 8px 16px rgba(0,0,0,0.3); padding: 24px; max-height: 85vh; overflow-y: auto; }
  .modal h2 { font-size: 18px; margin: 0 0 16px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 8px; }
  .modal h3 { font-size: 12px; margin: 20px 0 10px; color: #7f8c8d; text-transform: uppercase; }
  .modal input[type="text"] { width: 100%; background: var(--input-bg); color: var(--input-text); border: 1px solid var(--border-subtle); padding: 8px 12px; border-radius: var(--radius); margin-bottom: 12px; outline: none; }
  .config-row { display: flex; align-items: center; gap: 8px; background: rgba(0,0,0,0.03); padding: 6px 10px; border-radius: var(--radius); border: 1px solid var(--border-subtle); margin-bottom: 8px; }
  .config-row input[type="text"] { margin-bottom: 0; flex: 1; }
  .swatch-row { display: flex; gap: 4px; flex-wrap: wrap; width: 120px;}
  .swatch { width: 16px; height: 16px; border-radius: 3px; cursor: pointer; border: 2px solid transparent; }
  .swatch.selected { border-color: var(--text-light); }
  .config-del { background: none; border: none; color: #7f8c8d; font-size: 18px; cursor: pointer; padding: 0 4px; border-radius: 4px; }
  .modal-footer { display: flex; justify-content: flex-end; gap: 10px; margin-top: 24px; }
  .btn-primary { padding: 8px 20px; border-radius: var(--radius); border: none; background: #5aac44; color: #fff; cursor: pointer; font-weight: bold; }
  .btn-secondary { padding: 8px 16px; border-radius: var(--radius); border: none; background: rgba(0,0,0,0.05); color: var(--text-light); border: 1px solid var(--border-subtle); cursor: pointer; }

  /* Cheat Sheet Grid */
  .help-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 10px; }
  .help-col { display: flex; flex-direction: column; gap: 8px; }
  .help-item { display: flex; justify-content: space-between; font-size: 13px; border-bottom: 1px solid var(--border-subtle); padding-bottom: 4px; }
  .kbd { background: rgba(0,0,0,0.2); padding: 2px 6px; border-radius: 4px; font-family: monospace; color: #fff; font-size: 11px; font-weight: bold; border: 1px solid rgba(255,255,255,0.1); }
  body.light-theme .kbd { background: #fff; color: #333; border: 1px solid #ccc; box-shadow: 0 1px 1px rgba(0,0,0,0.1); }
</style>
</head>
<body>
<header>
  <h1 id="board-title">Document board</h1>
  <div class="header-actions">
    <button class="header-btn" onclick="triggerAddCard()">+ Card <span>(N)</span></button>
    <button class="header-btn" onclick="addStickyNote()">+ Note <span>(M)</span></button>
    <div class="divider"></div>
    <button class="header-btn" onclick="toggleHelp()">? <span>(?)</span></button>
    <button id="theme-btn" class="header-btn" onclick="toggleTheme()">&#9681; <span>(T)</span></button>
    <button id="stretch-btn" class="header-btn" onclick="toggleStretch()">&#8596; <span>(S)</span></button>
    <button class="header-btn" onclick="saveBackup()">&#128190; <span>(Shift+B)</span></button>
    <button class="header-btn" onclick="document.getElementById('restore-file').click()">&#128194; <span>(Shift+R)</span></button>
    <input type="file" id="restore-file" accept="application/json" style="display:none" onchange="loadBackup(event)">
    <button class="header-btn" onclick="exportLog()">&#8681; <span>(Shift+E)</span></button>
    <button class="header-btn" onclick="openConfig()">&#9881; <span>(C)</span></button>
  </div>
</header>
<main id="main-container">
  <div id="board-scroll-area"><div id="board"></div></div>
  <div id="sticky-note-panel">
    <div class="note-header">Information Board</div>
    <div id="sticky-notes-list"></div>
  </div>
</main>

<div class="overlay" id="help-overlay">
  <div class="modal" style="width: 600px;">
    <h2>Keyboard Shortcuts</h2>
    <div class="help-grid">
      <div class="help-col">
        <h3>General Actions</h3>
        <div class="help-item"><span>Toggle Shortcuts Menu</span> <span class="kbd">?</span></div>
        <div class="help-item"><span>Add New Card</span> <span class="kbd">N</span></div>
        <div class="help-item"><span>Add New Sticky Note</span> <span class="kbd">M</span></div>
        <div class="help-item"><span>Toggle Stretch Mode</span> <span class="kbd">S</span></div>
        <div class="help-item"><span>Toggle Light/Dark Theme</span> <span class="kbd">T</span></div>
        <div class="help-item"><span>Open Configuration</span> <span class="kbd">C</span></div>
        <div class="help-item"><span>Save Backup (Download)</span> <span class="kbd">Shift + B</span></div>
        <div class="help-item"><span>Restore Backup (Upload)</span> <span class="kbd">Shift + R</span></div>
        <div class="help-item"><span>Export Action Log (CSV)</span> <span class="kbd">Shift + E</span></div>
      </div>
      <div class="help-col">
        <h3>Card Navigation & Control</h3>
        <div class="help-item"><span>Select / Focus Cards</span> <span class="kbd">Arrows</span> or <span class="kbd">H J K L</span></div>
        <div class="help-item"><span>Pick Up / Drop Card</span> <span class="kbd">Space</span></div>
        <div class="help-item"><span>Edit Selected Card</span> <span class="kbd">E</span></div>
        <div class="help-item"><span>Delete Selected Card</span> <span class="kbd">Delete</span></div>
        <div class="help-item"><span>Cancel / Close Menu</span> <span class="kbd">Escape</span></div>
        <h3>While Typing (New/Edit)</h3>
        <div class="help-item"><span>Cycle Categories (Pills)</span> <span class="kbd">Alt + &#8592; / &#8594;</span></div>
        <div class="help-item"><span>Save / Submit</span> <span class="kbd">Enter</span></div>
        <div class="help-item"><span>New Line in Description</span> <span class="kbd">Shift + Enter</span></div>
      </div>
    </div>
    <div class="modal-footer"><button class="btn-secondary" onclick="closeOverlay('help-overlay')">Close</button></div>
  </div>
</div>

<div class="overlay" id="overlay">
  <div class="modal">
    <h2>Configure Board Layout</h2>
    <label>Board Name</label>
    <input type="text" id="cfg-title">
    <h3>Intake Categories (Pills)</h3>
    <div id="cfg-cat-list"></div>
    <div class="config-row">
      <input type="text" id="cfg-new-cat" placeholder="New Category Name">
      <button class="btn-secondary" onclick="addCategoryDraft()">Add</button>
    </div>
    <h3>Tracking Columns</h3>
    <div id="cfg-track-cols"></div>
    <div class="config-row">
      <input type="text" id="cfg-new-track" placeholder="New Tracking Column Name">
      <button class="btn-secondary" onclick="addColumnDraft()">Add</button>
    </div>
    <div class="modal-footer">
      <button class="btn-secondary" onclick="closeOverlay('overlay')">Cancel</button>
      <button class="btn-primary" onclick="saveConfig()">Save Changes</button>
    </div>
  </div>
</div>

<div class="overlay" id="card-edit-overlay">
  <div class="modal">
    <h2>Edit Card</h2>
    <div id="edit-pill-selector" style="margin-bottom: 12px;"></div>
    <textarea id="edit-card-textarea" style="width:100%; min-height:120px; font-family:inherit; padding:10px; border-radius:4px; border:1px solid var(--border-subtle); background:var(--input-bg); color:var(--input-text); outline:none; resize:vertical;"></textarea>
    <div class="modal-footer">
      <button class="btn-secondary" onclick="closeOverlay('card-edit-overlay')">Cancel</button>
      <button class="btn-primary" onclick="saveEditCard()">Save Content</button>
    </div>
  </div>
</div>

<div class="overlay" id="note-edit-overlay">
  <div class="modal">
    <h2>Edit Note</h2>
    <textarea id="edit-note-textarea" style="width:100%; min-height:120px; font-family:inherit; padding:10px; border-radius:4px; border:1px solid var(--border-subtle); background:var(--input-bg); color:var(--input-text); outline:none; resize:vertical;"></textarea>
    <div class="modal-footer">
      <button class="btn-secondary" onclick="closeOverlay('note-edit-overlay')">Cancel</button>
      <button class="btn-primary" onclick="saveEditNote()">Save Note</button>
    </div>
  </div>
</div>

<script>
const TRACKING_SWATCHES = __TRACKING_SWATCHES__;

let boardTitle = "Document board";
let categories = [];
let columns = [];
let cards = [];
let notes = [];
let boardVersion = 1;
let draftColumns = [];
let draftCategories = [];
let activeEditCardId = null;
let activeEditCategoryId = null;
let activeEditNoteId = null;
let kbDraggingCard = null;

let isStretched = localStorage.getItem('boardStretched') === 'true';
let isLight = localStorage.getItem('boardLightTheme') === 'true';
applyThemeUI();
applyStretchUI();

function toggleTheme() { isLight = !isLight; localStorage.setItem('boardLightTheme', isLight); applyThemeUI(); }
function applyThemeUI() { document.body.classList.toggle('light-theme', isLight); }
function toggleStretch() { isStretched = !isStretched; localStorage.setItem('boardStretched', isStretched); applyStretchUI(); render(); }
function applyStretchUI() {
    const wrap = document.querySelector('.board-wrapper');
    const main = document.getElementById('main-container');
    if(wrap) wrap.classList.toggle('stretched', isStretched);
    if(main) main.classList.toggle('stretched-mode', isStretched);
}

// Modal Locking Logic
function openOverlay(id, focusTargetId) {
    document.getElementById(id).classList.add('open');
    document.body.classList.add('modal-open');
    if (focusTargetId) {
        setTimeout(() => document.getElementById(focusTargetId).focus(), 50);
    }
}
function closeOverlay(id) {
    document.getElementById(id).classList.remove('open');
    document.body.classList.remove('modal-open');
    activeEditCardId = null;
    activeEditCategoryId = null;
    activeEditNoteId = null;
}
function toggleHelp() {
    const el = document.getElementById('help-overlay');
    if(el.classList.contains('open')) closeOverlay('help-overlay');
    else openOverlay('help-overlay');
}

function triggerAddCard() {
    const btn = document.querySelector('.add-card-btn');
    const row = document.querySelector('.add-row');
    const input = row ? row.querySelector('textarea') : null;
    if (row && row.classList.contains('open') && input) input.focus();
    else if (btn) btn.click();
}

function genId(prefix) { return prefix + '-' + Math.random().toString(36).substring(2, 10); }
function getFormattedDate() {
    const d = new Date(); const p = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${p(d.getMonth()+1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}:${p(d.getSeconds())}`;
}

async function loadData() {
  const res = await fetch('/api/data');
  const data = await res.json();
  boardTitle = data.board_title;
  categories = data.categories || [];
  columns = data.columns;
  cards = data.cards;
  notes = data.notes || [];
  boardVersion = data.version || 1;
  document.getElementById('board-title').textContent = boardTitle;
  render();
  renderStickyNotes();
}

async function post(body) {
  body.version = boardVersion;
  try {
      const res = await fetch('/api/data', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      if (res.status === 409) { alert((await res.json()).error); await loadData(); return false; }
      if (res.ok) { boardVersion = (await res.json()).new_version; return true; }
      return false;
  } catch (e) { return false; }
}

let noteDebounce;
function scheduleNoteSave() {
    clearTimeout(noteDebounce);
    noteDebounce = setTimeout(async () => {
        await post({ action: 'update_notes', notes: notes });
    }, 500);
}

function renderStickyNotes() {
    const list = document.getElementById('sticky-notes-list');
    list.innerHTML = '';
    notes.forEach(note => {
        const wrapper = document.createElement('div'); wrapper.className = 'individual-note';

        const actions = document.createElement('div'); actions.className = 'card-actions';
        actions.style.position = 'absolute'; actions.style.top = '8px'; actions.style.right = '8px';

        const editBtn = document.createElement('button'); editBtn.className = 'card-btn edit-btn'; editBtn.textContent = 'edit';
        editBtn.onclick = () => { openEditNote(note.id); };

        const delBtn = document.createElement('button'); delBtn.className = 'card-btn del-btn'; delBtn.textContent = 'del';
        delBtn.onclick = () => { notes = notes.filter(x => x.id !== note.id); renderStickyNotes(); scheduleNoteSave(); };

        actions.appendChild(editBtn); actions.appendChild(delBtn);
        wrapper.appendChild(actions);

        const textDiv = document.createElement('div'); textDiv.className = 'individual-note-text';
        textDiv.textContent = note.text || "Empty Note";
        wrapper.appendChild(textDiv);

        list.appendChild(wrapper);
    });
}
function openEditNote(id) {
    activeEditNoteId = id;
    const noteObj = notes.find(x => x.id === id);
    document.getElementById('edit-note-textarea').value = noteObj.text;
    openOverlay('note-edit-overlay', 'edit-note-textarea');
}
async function saveEditNote() {
    if(!activeEditNoteId) return;
    const val = document.getElementById('edit-note-textarea').value.trim();
    const noteObj = notes.find(x => x.id === activeEditNoteId);
    if(noteObj) noteObj.text = val;
    closeOverlay('note-edit-overlay');
    renderStickyNotes();
    scheduleNoteSave();
}
document.getElementById('edit-note-textarea').addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); saveEditNote(); }
});

function addStickyNote() {
    const newId = genId('note');
    notes.push({ id: newId, text: '' });
    renderStickyNotes(); scheduleNoteSave();
    openEditNote(newId);
}

function render() {
  const board = document.getElementById('board'); board.innerHTML = '';
  board.className = 'board-wrapper' + (isStretched ? ' stretched' : '');

  columns.forEach(colData => {
    const col = document.createElement('div'); col.className = 'board-col'; col.dataset.colId = colData.id;
    const head = document.createElement('div'); head.className = 'col-head'; head.style.backgroundColor = colData.color; head.textContent = colData.label;
    col.appendChild(head);

    const zone = document.createElement('div'); zone.className = 'drop-zone'; zone.dataset.colId = colData.id;

    if (colData.is_intake) {
        const addContainer = document.createElement('div'); addContainer.className = 'add-container';
        const addBtn = document.createElement('button'); addBtn.className = 'add-card-btn'; addBtn.textContent = '+ Add card (N)';
        const addRow = document.createElement('div'); addRow.className = 'add-row';
        const pillHeader = document.createElement('div'); pillHeader.style.fontSize = '11px'; pillHeader.style.color = '#7f8c8d'; pillHeader.style.marginBottom = '6px'; pillHeader.textContent = 'Category (Alt + \u2190/\u2192)';

        const pillSelector = document.createElement('div'); pillSelector.className = 'pill-selector';
        let selectedPillId = categories.length > 0 ? categories[0].id : null;

        const renderPills = () => {
            pillSelector.innerHTML = '';
            categories.forEach(cat => {
                const p = document.createElement('div'); p.className = 'pill-option' + (selectedPillId === cat.id ? ' selected' : '');
                p.style.backgroundColor = cat.color; p.textContent = cat.label;
                p.onclick = () => { selectedPillId = cat.id; renderPills(); }; pillSelector.appendChild(p);
            });
        }; renderPills();

        const cycleAddPills = (dir) => {
            if (categories.length === 0) return;
            let idx = categories.findIndex(c => c.id === selectedPillId);
            idx = (idx === -1) ? 0 : (idx + dir + categories.length) % categories.length;
            selectedPillId = categories[idx].id; renderPills();
        };

        const input = document.createElement('textarea'); input.placeholder = 'Task title...\\n(Shift+Enter for desc)';
        const btnGroup = document.createElement('div'); btnGroup.className = 'btn-group';
        const goBtn = document.createElement('button'); goBtn.textContent = 'Add';
        const cancelBtn = document.createElement('button'); cancelBtn.textContent = 'Cancel'; cancelBtn.className = 'btn-cancel';

        const closeAdd = () => { addRow.classList.remove('open'); addBtn.style.display = 'block'; input.value = ''; };
        const doAdd = async () => {
          const val = input.value.trim(); if (!val) { closeAdd(); return; }
          const id = genId('card'); const ts = getFormattedDate();
          cards.push({ id, text: val, column_id: colData.id, category_id: selectedPillId, created_at: ts }); closeAdd();
          const ok = await post({ action: 'create', card: val, column_id: colData.id, category_id: selectedPillId, created_at: ts }); if (ok) render();
        };

        goBtn.onclick = doAdd; cancelBtn.onclick = closeAdd;
        input.addEventListener('keydown', e => {
            if (e.altKey && e.key === 'ArrowLeft') { e.preventDefault(); cycleAddPills(-1); }
            else if (e.altKey && e.key === 'ArrowRight') { e.preventDefault(); cycleAddPills(1); }
            else if (e.key === 'Escape') closeAdd();
            else if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); doAdd(); }
        });
        addBtn.onclick = () => { addBtn.style.display = 'none'; addRow.classList.add('open'); input.focus(); };
        btnGroup.appendChild(cancelBtn); btnGroup.appendChild(goBtn);
        addRow.appendChild(pillHeader); addRow.appendChild(pillSelector); addRow.appendChild(input); addRow.appendChild(btnGroup);
        addContainer.appendChild(addBtn); addContainer.appendChild(addRow); col.appendChild(addContainer);
    }
    setupDropZone(zone, colData.id); renderCardsInto(zone, colData); col.appendChild(zone); board.appendChild(col);
  });
}

function renderCardsInto(container, columnData) {
  const targetCards = cards.filter(c => c.column_id === columnData.id);
  targetCards.forEach(c => {
    const cardEl = document.createElement('div'); cardEl.className = 'card'; cardEl.draggable = true; cardEl.dataset.id = c.id; cardEl.tabIndex = 0;
    const cat = categories.find(x => x.id === c.category_id); cardEl.style.background = cat ? cat.color : 'var(--bg-col)';
    if (cat) { const badge = document.createElement('div'); badge.className = 'pill-badge'; badge.textContent = cat.label; cardEl.appendChild(badge); }
    const lines = c.text.split('\\n');
    const titleEl = document.createElement('div'); titleEl.style.fontWeight = 'bold'; titleEl.textContent = lines[0]; cardEl.appendChild(titleEl);
    if (lines.length > 1) { const descEl = document.createElement('div'); descEl.style.fontSize = '12px'; descEl.style.marginTop = '6px'; descEl.style.opacity = '0.9'; descEl.textContent = lines.slice(1).join('\\n'); cardEl.appendChild(descEl); }
    const footerEl = document.createElement('div'); footerEl.className = 'card-footer';
    const timeEl = document.createElement('span'); timeEl.textContent = c.created_at ? c.created_at.substring(0, 16) : ''; footerEl.appendChild(timeEl);
    const actionsEl = document.createElement('div'); actionsEl.className = 'card-actions';
    const editBtn = document.createElement('button'); editBtn.className = 'card-btn edit-btn'; editBtn.textContent = 'edit'; editBtn.onclick = (e) => { e.stopPropagation(); openEditCard(c.id); };
    const del = document.createElement('button'); del.className = 'card-btn del-btn'; del.textContent = 'del';
    del.onclick = async (e) => { e.stopPropagation(); cards = cards.filter(x => x.id !== c.id); const ok = await post({ action: 'delete', card: c.text, column_id: columnData.id }); if (ok) render(); };
    actionsEl.appendChild(editBtn); actionsEl.appendChild(del); footerEl.appendChild(actionsEl); cardEl.appendChild(footerEl);
    cardEl.addEventListener('dragstart', e => { if(kbDraggingCard) return e.preventDefault(); cardEl.classList.add('dragging'); e.dataTransfer.setData('text/plain', c.id); });
    cardEl.addEventListener('dragend', () => cardEl.classList.remove('dragging'));
    container.appendChild(cardEl);
  });
}

// Global Keyboard Router
document.addEventListener('keydown', async (e) => {
    const isInput = ['TEXTAREA', 'INPUT'].includes(document.activeElement.tagName);
    const hasOverlayOpen = document.body.classList.contains('modal-open');

    if (e.key === 'Escape') {
        if(hasOverlayOpen) {
            document.querySelectorAll('.overlay.open').forEach(el => el.classList.remove('open'));
            document.body.classList.remove('modal-open');
            activeEditCardId = null;
            activeEditCategoryId = null;
            activeEditNoteId = null;
        }
        return;
    }

    if (isInput) return; // Ignore hotkeys when typing

    const key = e.key.toLowerCase();

    // Global Menu Toggles
    if (!hasOverlayOpen && !kbDraggingCard) {
        if (key === '?') { e.preventDefault(); toggleHelp(); return; }
        if (key === 'n') { e.preventDefault(); triggerAddCard(); return; }
        if (key === 'm') { e.preventDefault(); addStickyNote(); return; }
        if (key === 's') { e.preventDefault(); toggleStretch(); return; }
        if (key === 't') { e.preventDefault(); toggleTheme(); return; }
        if (key === 'c') { e.preventDefault(); openConfig(); return; }

        if (e.shiftKey && key === 'b') { e.preventDefault(); saveBackup(); return; }
        if (e.shiftKey && key === 'r') { e.preventDefault(); document.getElementById('restore-file').click(); return; }
        if (e.shiftKey && key === 'e') { e.preventDefault(); exportLog(); return; }
    }

    // Card Focus & Drag Navigation Engine
    if (hasOverlayOpen) return;

    const active = document.activeElement;
    const isCard = active.classList.contains('card');
    const isDirKey = ['arrowup','arrowdown','arrowleft','arrowright','h','j','k','l'].includes(key);

    if (!kbDraggingCard && isDirKey) {
        e.preventDefault();
        const allCards = Array.from(document.querySelectorAll('.card'));
        if (allCards.length === 0) return;

        if (!isCard) { allCards[0].focus(); return; }

        if (['j', 'arrowdown'].includes(key)) {
            const next = active.nextElementSibling;
            if (next && next.classList.contains('card')) next.focus();
        } else if (['k', 'arrowup'].includes(key)) {
            const prev = active.previousElementSibling;
            if (prev && prev.classList.contains('card')) prev.focus();
        } else if (['l', 'arrowright'].includes(key)) {
            const cols = Array.from(document.querySelectorAll('.board-col'));
            let idx = cols.indexOf(active.closest('.board-col'));
            while(idx < cols.length - 1) {
                idx++;
                const c = cols[idx].querySelector('.card');
                if(c) { c.focus(); break; }
            }
        } else if (['h', 'arrowleft'].includes(key)) {
            const cols = Array.from(document.querySelectorAll('.board-col'));
            let idx = cols.indexOf(active.closest('.board-col'));
            while(idx > 0) {
                idx--;
                const c = cols[idx].querySelector('.card');
                if(c) { c.focus(); break; }
            }
        }
        return;
    }

    if (isCard && !kbDraggingCard) {
        if (key === 'e') { e.preventDefault(); active.querySelector('.edit-btn').click(); }
        if (key === 'delete' || key === 'backspace') { e.preventDefault(); active.querySelector('.del-btn').click(); }
        if (key === ' ' || key === 'spacebar') { e.preventDefault(); kbDraggingCard = active; active.classList.add('keyboard-dragging'); }
    } else if (kbDraggingCard) {
        e.preventDefault();
        if (key === 'enter' || key === ' ' || key === 'spacebar') {
            kbDraggingCard.classList.remove('keyboard-dragging');
            const newColId = kbDraggingCard.closest('.board-col').dataset.colId;
            const cardId = kbDraggingCard.dataset.id;

            const domCards = document.querySelectorAll('.card');
            const newCardsArray = [];
            domCards.forEach(el => {
                const cObj = cards.find(x => x.id === el.dataset.id);
                if (cObj) { if (cObj.id === cardId) cObj.column_id = newColId; newCardsArray.push(cObj); }
            }); cards = newCardsArray;
            await post({ action: 'update_cards', cards: cards }); render();
            setTimeout(() => { const el = document.querySelector(`[data-id='${cardId}']`); if(el) el.focus(); }, 50);
            kbDraggingCard = null; return;
        }
        const currentZone = kbDraggingCard.closest('.drop-zone');
        const currentCol = kbDraggingCard.closest('.board-col');

        if (['arrowleft', 'h'].includes(key)) {
            const prevCol = currentCol.previousElementSibling;
            if (prevCol) { prevCol.querySelector('.drop-zone').appendChild(kbDraggingCard); kbDraggingCard.focus(); }
        } else if (['arrowright', 'l'].includes(key)) {
            const nextCol = currentCol.nextElementSibling;
            if (nextCol) { nextCol.querySelector('.drop-zone').appendChild(kbDraggingCard); kbDraggingCard.focus(); }
        } else if (['arrowup', 'k'].includes(key)) {
            const prevCard = kbDraggingCard.previousElementSibling;
            if (prevCard && prevCard.classList.contains('card')) { currentZone.insertBefore(kbDraggingCard, prevCard); kbDraggingCard.focus(); }
        } else if (['arrowdown', 'j'].includes(key)) {
            const nextCard = kbDraggingCard.nextElementSibling;
            if (nextCard && nextCard.classList.contains('card')) { currentZone.insertBefore(kbDraggingCard, nextCard.nextElementSibling); kbDraggingCard.focus(); }
        }
    }
});

function renderEditPills() {
    const container = document.getElementById('edit-pill-selector');
    container.innerHTML = '<div style="font-size:11px; color:#7f8c8d; margin-bottom:6px;">Category (Alt + \u2190/\u2192)</div>';
    const wrap = document.createElement('div'); wrap.className = 'pill-selector';
    categories.forEach(cat => {
        const p = document.createElement('div'); p.className = 'pill-option' + (activeEditCategoryId === cat.id ? ' selected' : '');
        p.style.backgroundColor = cat.color; p.textContent = cat.label;
        p.onclick = () => { activeEditCategoryId = cat.id; renderEditPills(); }; wrap.appendChild(p);
    }); container.appendChild(wrap);
}
function cycleEditPills(dir) {
    if (categories.length === 0) return;
    let idx = categories.findIndex(c => c.id === activeEditCategoryId);
    idx = (idx === -1) ? 0 : (idx + dir + categories.length) % categories.length;
    activeEditCategoryId = categories[idx].id; renderEditPills();
}
document.getElementById('edit-card-textarea').addEventListener('keydown', e => {
    if (e.altKey && e.key === 'ArrowLeft') { e.preventDefault(); cycleEditPills(-1); }
    else if (e.altKey && e.key === 'ArrowRight') { e.preventDefault(); cycleEditPills(1); }
    else if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); saveEditCard(); }
});

function openEditCard(id) {
    activeEditCardId = id; const cardObj = cards.find(x => x.id === id); activeEditCategoryId = cardObj.category_id;
    renderEditPills(); document.getElementById('edit-card-textarea').value = cardObj.text;
    openOverlay('card-edit-overlay', 'edit-card-textarea');
}
async function saveEditCard() {
    if(!activeEditCardId) return; const val = document.getElementById('edit-card-textarea').value.trim();
    if(val) { const cardObj = cards.find(x => x.id === activeEditCardId); cardObj.text = val; cardObj.category_id = activeEditCategoryId; }
    closeOverlay('card-edit-overlay'); await post({ action: 'update_cards', cards: cards }); render();
}

function getDragAfterElement(container, y) {
  const draggables = [...container.querySelectorAll('.card:not(.dragging)')];
  return draggables.reduce((closest, child) => {
    const box = child.getBoundingClientRect(); const offset = y - box.top - box.height / 2;
    if (offset < 0 && offset > closest.offset) return { offset: offset, element: child }; return closest;
  }, { offset: Number.NEGATIVE_INFINITY }).element;
}
function clearDropIndicators() { document.querySelectorAll('.card').forEach(c => c.classList.remove('drag-target')); }

function setupDropZone(zone, columnId) {
  zone.addEventListener('dragover', e => { e.preventDefault(); zone.classList.add('dragover'); clearDropIndicators(); const after = getDragAfterElement(zone, e.clientY); if (after) after.classList.add('drag-target'); });
  zone.addEventListener('dragleave', () => { zone.classList.remove('dragover'); clearDropIndicators(); });
  zone.addEventListener('drop', async e => {
    e.preventDefault(); zone.classList.remove('dragover'); clearDropIndicators();
    const id = e.dataTransfer.getData('text/plain'); if (!id) return;
    const after = getDragAfterElement(zone, e.clientY); const obj = cards.find(x => x.id === id); if (!obj) return;
    obj.column_id = columnId; const draggedEl = document.querySelector(`[data-id='${id}']`);
    if (draggedEl) { if (after == null) zone.appendChild(draggedEl); else zone.insertBefore(draggedEl, after); }
    const domCards = document.querySelectorAll('.card'); const newCardsArray = [];
    domCards.forEach(el => { const cObj = cards.find(x => x.id === el.dataset.id); if (cObj) newCardsArray.push(cObj); });
    cards.forEach(c => { if (!newCardsArray.includes(c)) newCardsArray.push(c); }); cards = newCardsArray;
    await post({ action: 'update_cards', cards: cards }); render();
  });
}

function exportLog() { window.location.href = '/api/export'; }
function saveBackup() { window.location.href = '/api/backup'; }
async function loadBackup(event) {
  const file = event.target.files[0]; if (!file) return;
  const text = await file.text();
  try {
    const res = await fetch('/api/restore', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: text });
    if(res.ok) { await loadData(); alert('Backup recovered.'); } else alert('Rejected.');
  } catch (err) { alert('Invalid file.'); } event.target.value = '';
}

function openConfig() {
  draftColumns = JSON.parse(JSON.stringify(columns.filter(c => !c.is_intake))); draftCategories = JSON.parse(JSON.stringify(categories));
  document.getElementById('cfg-title').value = boardTitle; renderConfigLists();
  openOverlay('overlay', 'cfg-title');
}

function renderConfigLists() {
  const catWrap = document.getElementById('cfg-cat-list'); const trackWrap = document.getElementById('cfg-track-cols');
  catWrap.innerHTML = ''; trackWrap.innerHTML = '';
  draftCategories.forEach((cat, idx) => {
    const row = document.createElement('div'); row.className = 'config-row';
    const input = document.createElement('input'); input.type = 'text'; input.value = cat.label; input.oninput = () => { draftCategories[idx].label = input.value; };
    const swatchRow = document.createElement('div'); swatchRow.className = 'swatch-row';
    TRACKING_SWATCHES.forEach(color => {
      const sw = document.createElement('div'); sw.className = 'swatch' + (cat.color === color ? ' selected' : '');
      sw.style.background = color; sw.onclick = () => { draftCategories[idx].color = color; renderConfigLists(); }; swatchRow.appendChild(sw);
    });
    const del = document.createElement('button'); del.className = 'config-del'; del.innerHTML = '&times;'; del.title = "Delete";
    del.onclick = () => { draftCategories.splice(idx, 1); renderConfigLists(); };
    row.appendChild(input); row.appendChild(swatchRow); row.appendChild(del); catWrap.appendChild(row);
  });

  draftColumns.forEach((col, idx) => {
    const row = document.createElement('div'); row.className = 'config-row';
    const input = document.createElement('input'); input.type = 'text'; input.value = col.label; input.oninput = () => { draftColumns[idx].label = input.value; };
    const swatchRow = document.createElement('div'); swatchRow.className = 'swatch-row';
    TRACKING_SWATCHES.forEach(color => {
      const sw = document.createElement('div'); sw.className = 'swatch' + (col.color === color ? ' selected' : '');
      sw.style.background = color; sw.onclick = () => { draftColumns[idx].color = color; renderConfigLists(); }; swatchRow.appendChild(sw);
    });
    const actionBlock = document.createElement('div'); actionBlock.style.display = 'flex'; actionBlock.style.gap = '2px';
    const upBtn = document.createElement('button'); upBtn.className = 'config-del'; upBtn.innerHTML = '&#8593;'; upBtn.title = "Move Up";
    upBtn.onclick = () => { if(idx > 0) { const t = draftColumns[idx]; draftColumns[idx] = draftColumns[idx-1]; draftColumns[idx-1] = t; renderConfigLists(); } };
    const dnBtn = document.createElement('button'); dnBtn.className = 'config-del'; dnBtn.innerHTML = '&#8595;'; dnBtn.title = "Move Down";
    dnBtn.onclick = () => { if(idx < draftColumns.length-1) { const t = draftColumns[idx]; draftColumns[idx] = draftColumns[idx+1]; draftColumns[idx+1] = t; renderConfigLists(); } };
    const del = document.createElement('button'); del.className = 'config-del'; del.innerHTML = '&times;'; del.title = "Delete";
    del.onclick = () => { draftColumns.splice(idx, 1); renderConfigLists(); };
    actionBlock.appendChild(upBtn); actionBlock.appendChild(dnBtn); actionBlock.appendChild(del);
    row.appendChild(input); row.appendChild(swatchRow); row.appendChild(actionBlock); trackWrap.appendChild(row);
  });
}
function addCategoryDraft() {
  const input = document.getElementById('cfg-new-cat'); const val = input.value.trim(); if (!val) return;
  draftCategories.push({ id: genId('cat'), label: val, color: TRACKING_SWATCHES[draftCategories.length % TRACKING_SWATCHES.length] }); input.value = ''; renderConfigLists();
}
function addColumnDraft() {
  const input = document.getElementById('cfg-new-track'); const val = input.value.trim(); if (!val) return;
  draftColumns.push({ id: genId('col'), label: val, color: TRACKING_SWATCHES[draftColumns.length % TRACKING_SWATCHES.length], is_intake: false }); input.value = ''; renderConfigLists();
}
async function saveConfig() {
  const title = document.getElementById('cfg-title').value.trim() || 'Document board';
  const ok = await post({ action: 'configure', board_title: title, columns: [columns.find(c => c.is_intake), ...draftColumns], categories: draftCategories });
  if (ok) { closeOverlay('overlay'); await loadData(); }
}
loadData();
</script>
</body>
</html>
"""

class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args): pass
    def _send(self, code, content_type, body):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.end_headers()
        self.wfile.write(body.encode("utf-8") if isinstance(body, str) else body)

    def do_GET(self):
        if self.path in ["/", "/index.html"]:
            self._send(200, "text/html; charset=utf-8", PAGE.replace("__TRACKING_SWATCHES__", json.dumps(TRACKING_SWATCHES)))
        elif self.path == "/api/data":
            self._send(200, "application/json", json.dumps(load_data()))
        elif self.path == "/api/export":
            data = load_data()
            buf = io.StringIO()
            writer = csv.writer(buf)
            writer.writerow(["time", "action", "card", "detail"])
            for h in data["history"]: writer.writerow([h.get("time", ""), h.get("action", ""), h.get("card", ""), h.get("detail", "")])
            self.send_response(200)
            self.send_header("Content-Type", "text/csv")
            self.send_header("Content-Disposition", 'attachment; filename="document-board-log.csv"')
            self.end_headers()
            self.wfile.write(buf.getvalue().encode("utf-8"))
        elif self.path == "/api/backup":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Disposition", 'attachment; filename="document-board-backup.json"')
            self.end_headers()
            self.wfile.write(json.dumps(load_data(), indent=2).encode("utf-8"))
        else: self._send(404, "text/plain", "Not found")

    def do_POST(self):
        if self.path in ["/api/data", "/api/restore"]:
            try: body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            except: return self._send(400, "application/json", json.dumps({"error": "Malformed payload"}))
            data = load_data()

            if self.path == "/api/data":
                if body.get("version") is not None and body.get("version") != data.get("version", 1):
                    return self._send(409, "application/json", json.dumps({"error": "Syncing layouts."}))

                action = body.get("action")
                card_text = body.get("card", "")

                if action == "create":
                    data["cards"].append({"id": "c-" + uuid.uuid4().hex[:8], "text": card_text, "column_id": body.get("column_id"), "category_id": body.get("category_id"), "created_at": body.get("created_at", now_str())})
                    log_event(data, "created", card_text, f"Assigned to {body.get('column_id')}")
                elif action == "update_cards":
                    for ic in body.get("cards", []):
                        existing = next((cx for cx in data["cards"] if cx["id"] == ic["id"]), None)
                        ic["created_at"] = existing["created_at"] if existing and "created_at" in existing else now_str()
                    data["cards"] = body.get("cards", [])
                    log_event(data, "updated", "Cards batch processed")
                elif action == "delete":
                    data["cards"] = [c for c in data["cards"] if c["text"] != card_text]
                    log_event(data, "deleted", card_text)
                elif action == "configure":
                    data["board_title"] = body.get("board_title", data["board_title"])
                    data["columns"] = body.get("columns", [])
                    data["categories"] = body.get("categories", [])
                    log_event(data, "configured", "Layout and categories updated")
                elif action == "update_notes":
                    data["notes"] = body.get("notes", [])

                data["version"] = data.get("version", 1) + 1
                save_data(data)
                self._send(200, "application/json", json.dumps({"ok": True, "new_version": data["version"]}))
            elif self.path == "/api/restore":
                incoming = migrate_data(body)
                incoming["version"] = data.get("version", 1) + 1
                save_data(incoming)
                self._send(200, "application/json", json.dumps({"ok": True}))

def main():
    parser = argparse.ArgumentParser(description="Document Board Server - Adaptable for Online Hosting")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"), help="Host IP to bind the server to (use '0.0.0.0' for remote hosting)")
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", PORT)), help="Port number to listen on")
    parser.add_argument("--no-browser", action="store_true", default=os.environ.get("NO_BROWSER", "false").lower() == "true", help="Do not automatically open a web browser")
    args = parser.parse_args()

    if not os.path.exists(DATA_FILE):
        save_data(json.loads(json.dumps(DEFAULT_DATA)))

    print(f"Starting document board on http://{args.host}:{args.port}...")

    try:
        server = HTTPServer((args.host, args.port), Handler)
    except OSError as e:
        print(f"Error starting server: {e}", file=sys.stderr)
        sys.exit(1)

    # Automatically launch browser if binding to localhost/127.0.0.1 and --no-browser isn't set
    if not args.no_browser and args.host in ("127.0.0.1", "localhost"):
        threading.Timer(0.6, lambda: webbrowser.open(f"http://{args.host}:{args.port}/")).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
        sys.exit(0)

if __name__ == "__main__":
    main()
