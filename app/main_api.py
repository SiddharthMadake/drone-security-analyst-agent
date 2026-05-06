from pathlib import Path
import re

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.agent import SecurityQueryAgent
from src.database import SecurityDatabase
from src.settings import settings


app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.cache = None

db: SecurityDatabase | None = None


def get_db() -> SecurityDatabase:
    global db
    if db is None:
        db = SecurityDatabase(settings.database.db_path)
    return db


@app.on_event("startup")
def startup() -> None:
    global db
    db = SecurityDatabase(settings.database.db_path)


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(
        request,
        "dashboard_pro.html",
        {"request": request},
    )


@app.get("/api/stats")
def stats():
    return get_db().get_statistics()


@app.get("/api/alerts")
def alerts():
    return get_db().get_alerts(limit=20)


@app.get("/api/frames")
def frames():
    return get_db().get_recent_frames(limit=20)


@app.get("/api/frames/object/{object_class}")
def frames_by_object(object_class: str):
    return get_db().query_frames_by_object(object_class, limit=50)


@app.get("/api/search")
def search(q: str):
    q = q.strip()
    if not q:
        return []
    terms = re.findall(r"\w+", q)
    if not terms:
        return []
    fts_query = " OR ".join(f'"{term}"' for term in terms)
    try:
        return get_db().fulltext_search(fts_query)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid search query") from exc


@app.get("/api/agent/ask")
def ask_agent(q: str):
    return SecurityQueryAgent(get_db()).answer(q)


@app.get("/api/summary")
def summary():
    return SecurityQueryAgent(get_db()).summary()
