from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from .routers import auth, tasks, wallet, referrals, notify, admin, account
from .database import init_db
from .config import settings
import os

ROOT = os.path.dirname(os.path.dirname(__file__))
LOGO_PATH = os.path.join(ROOT, 'logo')
VIDEO_PATH = os.path.join(ROOT, 'video')
UPLOADS_PATH = os.path.join(ROOT, 'uploads')

app = FastAPI(title="JUSTICE Backend")

# initialize DB
init_db()

# add permissive CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# mount static folders so frontend can fetch logos and videos
if os.path.isdir(LOGO_PATH):
    app.mount('/static/logo', StaticFiles(directory=LOGO_PATH), name='logo')

if os.path.isdir(VIDEO_PATH):
    app.mount('/static/video', StaticFiles(directory=VIDEO_PATH), name='video')

# mount uploads if present (for submitted screenshots)
if os.path.isdir(UPLOADS_PATH):
    app.mount('/static/uploads', StaticFiles(directory=UPLOADS_PATH), name='uploads')


# include routers (services)
app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(wallet.router, prefix="/wallet", tags=["wallet"])
app.include_router(referrals.router, prefix="/referrals", tags=["referrals"])
app.include_router(notify.router, prefix="/notify", tags=["notify"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(account.router, tags=["account"])


@app.get('/api/logo')
def api_logo():
    # return the first logo file found or a default
    try:
        files = [f for f in os.listdir(LOGO_PATH) if f.lower().endswith(('.png','.jpg','.jpeg','svg'))]
        if not files:
            return {"logo_url": None}
        return {"logo_url": f"/static/logo/{files[0]}"}
    except Exception:
        return {"logo_url": None}


@app.get('/api/video')
def api_video():
    try:
        files = [f for f in os.listdir(VIDEO_PATH) if f.lower().endswith(('.mp4','.webm'))]
        if not files:
            return {"video_url": None}
        return {"video_url": f"/static/video/{files[0]}"}
    except Exception:
        return {"video_url": None}

@app.get("/")
def root():
    return {"message": "JUSTICE backend running", "backend_url": str(settings.BACKEND_URL)}
