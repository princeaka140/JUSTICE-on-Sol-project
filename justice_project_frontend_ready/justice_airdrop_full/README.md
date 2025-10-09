# JUSTICE Airdrop WebApp (Full Stack)

This project contains:
- Backend: aiogram Telegram bot + FastAPI endpoints (backend/main.py)
- Frontend: Static WebApp (frontend/) designed for embedding as a Telegram Web App (Hugging Face Space)

Features implemented:
- Join verification
- Dashboard endpoints for user data, logo, video, notifications
- Task submission and withdrawal flows (submissions stored in DB and posted to review channel)
- Admin group commands (run in ADMIN_GROUP_ID):
  - /add <amount> <@username|user_id>
  - /ban <@username|user_id>
  - /unban <@username|user_id>
  - /openwithdraw
  - /closewithdraw
  - /task "Title" <reward>
  - /stats
  - /updatetrade <text>
  - /approveall, /rejectall, /approve <target>, /reject <target>
  - /updatelogo <image_url>
  - /uploadvideo <video_url>
  - /broadcast <message>
- Frontend uses BACKEND_URL environment variable to call the API.
- For simplicity, logo and video are set as public URLs via admin commands.

## Quickstart (local)
1. Create venv and install:
   ```bash
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
2. Copy `.env.example` -> `.env` and fill in values.
3. Run:
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port 8000
   ```
4. Open `frontend/index.html` in browser (or serve it on Hugging Face Spaces). When deploying frontend on Hugging Face, set BACKEND_URL to your deployed backend URL.

Notes:
- This is a starter full stack app. For production, consider securing endpoints, using webhooks, serving static files properly, and storing uploaded media.
