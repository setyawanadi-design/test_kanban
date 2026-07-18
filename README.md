# Document Board: How to Run Online & Share with Colleagues

Your Kanban board is designed to run as a lightweight Python server. Out-of-the-box, it only listens to your local computer (`127.0.0.1`). If you want to share it with your colleagues, you have three primary ways to host it online depending on your needs.

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

## Option 2: Persistent Cloud Hosting (Deploying to a PaaS)
**Best for:** Having a permanent link (e.g., `https://my-board.render.com`) that is online 24/7.

Platforms like **Render**, **Railway**, and **Fly.io** can host your Python script directly from a GitHub repository.

### Example: Deploying to Render (Free Tier)
1. Push this folder to your GitHub account (as a private or public repository).
2. Go to [Render](https://render.com/) and sign up / log in.
3. Click **New +** -> **Web Service**.
4. Connect your GitHub repository.
5. Configure the following settings:
   - **Environment:** `Python`
   - **Build Command:** *(Leave blank or set to a dummy step like `echo "No build needed"` since we use built-in Python standard libraries!)*
   - **Start Command:**
     ```bash
     python board.py --host 0.0.0.0 --port $PORT --no-browser
     ```
6. Click **Deploy Web Service**.
7. Once deployed, Render will provide a persistent URL (e.g., `https://document-board-xyz.onrender.com`) that you can share!

---

## Option 3: Dedicated Virtual Private Server (VPS)
**Best for:** Absolute control on your own server (AWS EC2, DigitalOcean Droplet, Linode, etc.).

If you have a Linux virtual machine, you can run it directly using a terminal multiplexer (like `tmux`) or turn it into a system service.

### Step-by-Step setup:
1. SSH into your VPS.
2. Clone or copy `board.py` onto the server.
3. To run it persistently in the background, you can use a tool like `nohup` or `tmux`:
   ```bash
   nohup python3 board.py --host 0.0.0.0 --port 8825 --no-browser > board.log 2>&1 &
   ```
   - *Note: Binding to `0.0.0.0` tells the server to listen on all public network interfaces.*
4. Ensure your cloud provider's firewall (Security Groups / UFW) allows inbound TCP traffic on port `8825`.
5. Access your board by visiting:
   ```text
   http://<YOUR_VPS_PUBLIC_IP>:8825
   ```
