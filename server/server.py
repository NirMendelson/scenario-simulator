from pathlib import Path
import json
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI()

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "final.json"
DIST = ROOT / "ui" / "dist"


@app.get("/api/tree")
def get_tree():
    if not DATA.exists():
        raise HTTPException(404, "data/final.json not found")
    with DATA.open("r", encoding="utf-8") as f:
        return JSONResponse(json.load(f))

if DIST.exists():
    app.mount("/", StaticFiles(directory=str(DIST), html=True), name="static")


@app.get("/")
def index():
    idx = DIST / "index.html"
    if idx.exists():
        return FileResponse(str(idx))
    return {"msg": "Build UI first: cd ui && npm i && npm run build"}
