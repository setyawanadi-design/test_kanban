# Document Board: Modular & Scalable Kanban Board

Welcome to the newly refactored, modern, and production-ready **Document Board**!

We completely migrated the application from a raw, single-file proof-of-concept into a decoupled, clean, and highly secure web app. This new architecture ensures your team can easily add features, avoid merge conflicts, protect data consistency, and deploy to any hosting platform in seconds.

---

## 🛠️ Refactored Architecture

1. **Decoupled Frontend (`static/`)**:
   The massive HTML string has been ripped out and organized into standards-based assets:
   - `static/index.html`: Clean HTML structure.
   - `static/style.css`: Dedicated, highly performant CSS variables and layout classes.
   - `static/script.js`: Clean JavaScript file utilizing IDE linting and autocompletion.
2. **Robust Persistence Layer (`board.db` via SQLite)**:
   Say goodbye to file-corruption race conditions! We replaced JSON flat-file storage with a local SQLite database, managed transactional CRUD APIs safely, and enabled proper concurrent reading/writing.
3. **Modern Backend Framework (FastAPI + Uvicorn)**:
   Built using **FastAPI**, providing superior routing, asynchronous request processing, automatic error handling, and high throughput.
4. **Strict Input Validation & Data Sanitization**:
   We added robust **Pydantic Models** that strictly validate and sanitize incoming payloads before writing anything to the database—safeguarding against malformed JSON or injection attacks.

---

## 📂 Project Structure

```text
├── board.py            # Main FastAPI server script (handles routing and server launch)
├── database.py         # SQLite Database schema, initialization, and transactional CRUD logic
├── board.db            # Local SQLite database (auto-generated on first run)
├── .gitignore          # Keeps build caches and local db files out of git history
├── README.md           # This comprehensive guide
└── static/             # Static frontend files directory
    ├── index.html      # Board HTML structure
    ├── style.css       # Board custom styles
    └── script.js       # Core board interaction script
```

---

## 🚀 How to Run Locally

### 1. Install Dependencies
You only need `fastapi` and `uvicorn` (which includes standard libraries like SQLite):
```bash
pip install fastapi uvicorn
```

### 2. Start the Server
Run the FastAPI application from your root directory:
```bash
python board.py
```

### 💡 Host, Port, and Headless Configuration Options
In `board.py`, we replaced hardcoded local bindings with robust arguments and environment variables:
- **`--host`** (or `HOST` environment variable): Set to `0.0.0.0` for public/network bindings.
- **`--port`** (or `PORT` environment variable): Define custom ports (defaults to `8825`).
- **`--no-browser`** (or `NO_BROWSER=true` environment variable): Prevents the script from attempting to spawn a local web browser on headless cloud servers.

Example:
```bash
python board.py --host 0.0.0.0 --port 8080 --no-browser
```

---

## 🌐 Free Online Deployment Guide (NO CREDIT CARD REQUIRED)

If you want to share your board securely with colleagues, use one of the following payment-free methods:

### Option A: GitHub Codespaces (Fastest Port Forwarding)
If your repository is stored on GitHub, you can securely access and run it inside the cloud for free:
1. Open your repository on GitHub.
2. Click the green **Code** button, select the **Codespaces** tab, and click **Create codespace**.
3. In the Codespace terminal, install dependencies and run:
   ```bash
   python board.py --host 0.0.0.0 --port 8825 --no-browser
   ```
4. Find the **Ports** tab in the bottom panel.
5. Right-click on port `8825` -> **Port Visibility** -> Select **Public**.
6. Copy the provided HTTPS link (e.g., `https://username-codespace-xyz-8825.app.github.dev`) and share it with your colleague!

### Option B: PythonAnywhere (Easiest Persistent Hosting)
PythonAnywhere offers a perpetual free beginner tier with zero setup cost:
1. Sign up on [PythonAnywhere](https://www.pythonanywhere.com/).
2. Under the **Files** tab, upload `board.py`, `database.py`, and the `static/` folder.
3. Go to the **Web** tab:
   - Click **Add a new web app**.
   - Choose **Manual Configuration** and select your Python version.
   - Point your WSGI configuration file directly to run `board.py` using ASGI or standard execution.

### Option C: Hugging Face Spaces (Docker-Native Hosting)
Deploy your containerized board directly onto Hugging Face for free:
1. Create a free account on [Hugging Face](https://huggingface.co/).
2. Go to **Spaces** -> **Create New Space**.
3. Choose **Docker** as the SDK (select the **Blank** template) and set your space to Public or Private.
4. Upload `board.py`, `database.py`, `static/`, and add a `Dockerfile` with:
   ```dockerfile
   FROM python:3.10-slim
   WORKDIR /app
   COPY . .
   RUN pip install fastapi uvicorn
   EXPOSE 7860
   CMD ["python", "board.py", "--host", "0.0.0.0", "--port", "7860", "--no-browser"]
   ```
5. Hugging Face will automatically build and host your board permanently!
