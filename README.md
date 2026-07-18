# Document Board: How to Run Online & Share with Colleagues

Your Kanban board is designed to run as a lightweight Python server. Out-of-the-box, it only listens to your local computer (`127.0.0.1`). If you want to share it with your colleagues, you have multiple ways to host it online depending on your needs.

We have updated the code in `board.py` to allow flexible hosting (accepting Custom Ports, Host IP binding, and a headless/no-browser option).

---

## Preparation: Understand the Dynamic Variables
In `board.py`, we replaced the hardcoded localhost bindings with arguments and environment variables:
- **`--host`** (or `HOST` env variable): Set this to `0.0.0.0` when running online so that it accepts incoming requests from other computers.
- **`--port`** (or `PORT` env variable): Set this to whatever port your cloud environment expects (e.g. `80`, `8080`, or `$PORT`).
- **`--no-browser`** (or `NO_BROWSER=true` env variable): Keeps the script from trying to open a local web browser on your headless remote server.

---

## Option 1: Quick & Temporary Sharing (Using Tunnels)
**Best for:** Showing your current local tasks to a colleague *right now* without configuring any cloud accounts.

If you already have the board running on your machine, you can use a secure tunnel tool to generate a temporary public URL that redirects directly to your local port.

### Method A: Localtunnel (Free & No Signup)
1. Ensure your local board is running:
   ```bash
   python3 board.py
   ```
2. In a new terminal tab/window, run:
   ```bash
   npx localtunnel --port 8825
   ```
3. Copy the URL generated (e.g., `https://short-bears-jump.loca.lt`) and share it with your colleague!

### Method B: Ngrok (Extremely Popular)
1. Install [ngrok](https://ngrok.com/) and create a free account.
2. Run your board:
   ```bash
   python3 board.py
   ```
3. Expose the port:
   ```bash
   ngrok http 8825
   ```
4. Copy the secure `https://...ngrok-free.app` link and send it to your colleague.

---

## Option 2: Free Persistent Cloud Hosting (NO CREDIT CARD REQUIRED)
**Best for:** Having a permanent link that is online 24/7, without entering any credit card details.

Since popular platforms like Render may require a credit card during signup, here are excellent free alternatives that do not require any payment details.

### Method A: PythonAnywhere (Easiest for Pure Python)
PythonAnywhere is custom-made for Python developers and offers a completely free plan with no credit card details.

1. Sign up for a free Beginner account on [PythonAnywhere](https://www.pythonanywhere.com/).
2. Once logged in, go to the **Files** tab and upload your `board.py` script.
3. Open a **Bash Console** from your dashboard.
4. (Optional) Run a quick test:
   ```bash
   python3 board.py --port 8825 --no-browser
   ```
5. To configure it as an official permanent web app, go to the **Web** tab in your dashboard:
   - Click **Add a new web app**.
   - Under framework choice, select **Manual Configuration** and choose your Python version.
   - Point the WSGI configuration or run script directly to your `board.py`.

### Method B: GitHub Codespaces (Built-in Port Forwarding)
If your code is on GitHub, you can spin up a fully cloud-hosted environment for free and easily share ports.

1. Go to your GitHub repository and click the green **Code** button.
2. Select the **Codespaces** tab and click **Create codespace on main**.
3. Once the environment loads, run the board inside the terminal:
   ```bash
   python3 board.py --host 0.0.0.0 --port 8825 --no-browser
   ```
4. Locate the **Ports** tab at the bottom panel next to Terminal.
5. You will see port `8825`. Right-click its **Port Visibility** and change it from *Private* to *Public*.
6. Copy the **Local Address** URL provided (e.g., `https://username-codespace-xyz-8825.app.github.dev`) and share it with your colleague!

### Method C: Hugging Face Spaces (Docker Sandbox)
Hugging Face offers 100% free cloud servers where you can host custom Python apps via Docker, with zero payment info required.

1. Sign up on [Hugging Face](https://huggingface.co/).
2. Click **Spaces** -> **Create New Space**.
3. Name your Space, and select **Docker** as the SDK (instead of Streamlit or Gradio). Choose the **Blank** template.
4. Set the space visibility to **Public** or **Private**, and click create.
5. Upload your `board.py` file, along with a simple file named `Dockerfile` containing:
   ```dockerfile
   FROM python:3.10-slim
   WORKDIR /app
   COPY . .
   EXPOSE 7860
   CMD ["python", "board.py", "--host", "0.0.0.0", "--port", "7860", "--no-browser"]
   ```
   *(Note: Hugging Face runs default apps on port `7860`, so we route to that port).*
6. Hugging Face will build the container automatically and host your Kanban board forever at a secure `huggingface.co/spaces/...` link.

---

## Option 3: Traditional Cloud Hosting (PaaS)
If you do have a credit card and want a service with automatic scaling:

### Deploying to Render
1. Push this folder to your GitHub account (as a private or public repository).
2. Go to [Render](https://render.com/) and sign up.
3. Click **New +** -> **Web Service**.
4. Connect your GitHub repository.
5. Configure the following settings:
   - **Environment:** `Python`
   - **Start Command:**
     ```bash
     python board.py --host 0.0.0.0 --port $PORT --no-browser
     ```
6. Click **Deploy Web Service** to generate your persistent URL.

---

## Option 4: Dedicated Virtual Private Server (VPS)
**Best for:** Absolute control on your own server (AWS EC2, DigitalOcean Droplet, Linode, etc.).

If you have a Linux virtual machine, you can run it directly using a terminal multiplexer (like `tmux`) or turn it into a system service.

### Step-by-Step setup:
1. SSH into your VPS.
2. Clone or copy `board.py` onto the server.
3. To run it persistently in the background:
   ```bash
   nohup python3 board.py --host 0.0.0.0 --port 8825 --no-browser > board.log 2>&1 &
   ```
4. Ensure your cloud provider's firewall (Security Groups / UFW) allows inbound TCP traffic on port `8825`.
5. Access your board by visiting `http://<YOUR_VPS_PUBLIC_IP>:8825`.
