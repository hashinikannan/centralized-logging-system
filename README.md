# Centralized Logging System 🚀
> A lightweight, beginner-friendly log aggregation and error investigation platform for distributed services built with **Python**, **Flask**, and **Vanilla Web Technologies**.

The complete project code and documentation are inside [`centralized-logging-system/`](centralized-logging-system).

---

## 🚀 1-Click Free Cloud Deployment (Render / Railway)

This repository includes pre-configured **`Procfile`**, **`render.yaml`**, **`Dockerfile`**, and **`wsgi.py`** for instant deployment.

### Option A: Deploy on Render (Free & Recommended)
1. Go to [dashboard.render.com](https://dashboard.render.com/) and sign in with GitHub.
2. Click **New +** > **Web Service**.
3. Choose **Build and deploy from a Git repository** and select:
   `https://github.com/hashinikannan/centralized-logging-system`
4. Render will auto-detect the configuration, or set:
   - **Environment:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn wsgi:app`
5. Click **Create Web Service**. Your live public URL (`https://centralized-logging-system-xxxx.onrender.com`) will be active in ~1-2 minutes!

### Option B: Deploy on Railway
1. Go to [railway.com](https://railway.com/) and sign in with GitHub.
2. Click **New Project** > **Deploy from GitHub repo**.
3. Select `hashinikannan/centralized-logging-system`.
4. Railway will auto-detect the `Procfile` and deploy your app with a public domain.

---

## 💻 Local Quick Start

To launch the application locally:
```powershell
py run.py
```

Or change directory into the project folder:
```powershell
cd centralized-logging-system
py app.py
```

Then open your browser at:
```text
http://127.0.0.1:5000/
```

### Run Automated Tests:
```powershell
py -m pytest -v centralized-logging-system/tests
```

For the complete architectural guide, API reference, presentation pitch, and 5-minute live demo script, see:
- [centralized-logging-system/README.md](centralized-logging-system/README.md)
