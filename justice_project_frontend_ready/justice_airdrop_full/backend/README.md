# JUSTICE Backend

This is the minimal backend for the Justice Airdrop frontend demo.

Requirements
- Python 3.10+
- Install dependencies: `pip install -r requirements.txt`

Run locally (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn backend.main:app --reload --port 8000
```

Endpoints added by the repair script
- `GET /api/logo` -> returns JSON {"logo_url": "/static/logo/<file>"}
- `GET /api/video` -> returns JSON {"video_url": "/static/video/<file>"}

Notes
- Static folders `logo/` and `video/` are mounted at `/static/logo` and `/static/video` respectively.
- This server creates a local SQLite DB file `justice.db` when first run.
- For production, lock down CORS and admin endpoints.
