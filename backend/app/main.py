"""
AR-Based Real-Time Infrastructure Damage Assessment System – API server.

Run:  uvicorn app.main:app --host 0.0.0.0 --port 8000
"""
import json
import os
import uuid
from contextlib import asynccontextmanager
from typing import Optional

import cv2
import numpy as np
from fastapi import Depends, FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import detector
from .auth import (COOKIE_NAME, create_session, current_user, delete_session, ensure_demo_user,
                   hash_password, public_user, verify_password)
from .db import DATA_DIR, MEDIA_DIR, connect, init_db, row
from .reports import build_report

FRONTEND_DIR = os.environ.get(
    "FRONTEND_DIR",
    os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "frontend"),
)
INFRA_TYPES = ["Bridge", "Building", "Road", "Tunnel", "Railway", "Dam", "Utility Facility", "Other"]
MAX_UPLOAD = 15 * 1024 * 1024

@asynccontextmanager
async def lifespan(_app):
    init_db()
    ensure_demo_user()
    detector.get_engine()  # warm up
    yield


app = FastAPI(title="AR Infrastructure Damage Assessment API", version="1.0.0", lifespan=lifespan)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
async def _read_image(file: UploadFile) -> np.ndarray:
    data = await file.read()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "Image too large (max 15 MB)")
    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        raise HTTPException(400, "Could not read image – upload a JPEG or PNG")
    return img


def _own_inspection(con, inspection_id: int, user: dict) -> dict:
    ins = row(con.execute("SELECT * FROM inspections WHERE id = ?", (inspection_id,)).fetchone())
    if not ins or ins["user_id"] != user["id"]:
        raise HTTPException(404, "Inspection not found")
    return ins


def _finding_out(f: dict) -> dict:
    f = dict(f)
    f["detections"] = json.loads(f.pop("detections_json"))
    f["image_url"] = f"/{f['image_path']}"
    f["annotated_url"] = f"/{f['annotated_path']}"
    return f


def _refresh_condition(con, inspection_id: int):
    dets = []
    for (dj,) in con.execute("SELECT detections_json FROM findings WHERE inspection_id = ?", (inspection_id,)):
        dets += json.loads(dj)
    has_findings = con.execute("SELECT COUNT(*) FROM findings WHERE inspection_id = ?", (inspection_id,)).fetchone()[0]
    cond = detector.overall_condition(dets) if has_findings else None
    con.execute("UPDATE inspections SET condition = ? WHERE id = ?", (cond, inspection_id))


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
class LoginIn(BaseModel):
    username: str
    password: str


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=40)
    full_name: str = Field(min_length=2, max_length=80)
    password: str = Field(min_length=6, max_length=128)
    role: str = Field(default="Inspector", max_length=40)


def _login_response(user: dict) -> JSONResponse:
    token = create_session(user["id"])
    resp = JSONResponse({"user": public_user(user), "token": token})
    resp.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", max_age=60 * 60 * 24 * 14)
    return resp


@app.post("/api/auth/login")
def login(body: LoginIn):
    with connect() as con:
        u = row(con.execute("SELECT * FROM users WHERE username = ?", (body.username.strip().lower(),)).fetchone())
    if not u or not verify_password(body.password, u["password_hash"]):
        raise HTTPException(401, "Incorrect username or password")
    return _login_response(u)


@app.post("/api/auth/register")
def register(body: RegisterIn):
    username = body.username.strip().lower()
    with connect() as con:
        if con.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
            raise HTTPException(409, "That username is already taken")
        cur = con.execute(
            "INSERT INTO users (username, full_name, role, password_hash) VALUES (?, ?, ?, ?)",
            (username, body.full_name.strip(), body.role.strip() or "Inspector", hash_password(body.password)),
        )
        u = row(con.execute("SELECT * FROM users WHERE id = ?", (cur.lastrowid,)).fetchone())
    return _login_response(u)


@app.get("/api/auth/me")
def me(user: dict = Depends(current_user)):
    return public_user(user)


@app.post("/api/auth/logout")
def logout(response: Response, user: dict = Depends(current_user)):
    delete_session(user["_token"])
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


# --------------------------------------------------------------------------- #
# Detection (live AR mode – nothing stored)
# --------------------------------------------------------------------------- #
@app.post("/api/detect")
async def detect(image: UploadFile = File(...), fast: bool = Form(True), user: dict = Depends(current_user)):
    img = await _read_image(image)
    return detector.analyze(img, fast=fast)


@app.get("/api/meta")
def meta():
    eng = detector.get_engine()
    return {"engine": eng.name, "damage_types": detector.DAMAGE_TYPES, "infrastructure_types": INFRA_TYPES}


# --------------------------------------------------------------------------- #
# Inspections
# --------------------------------------------------------------------------- #
class InspectionIn(BaseModel):
    infrastructure_type: str
    asset_name: str = Field(min_length=1, max_length=120)
    location: Optional[str] = Field(default=None, max_length=200)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    description: Optional[str] = Field(default=None, max_length=2000)


class InspectionPatch(BaseModel):
    notes: Optional[str] = Field(default=None, max_length=4000)
    status: Optional[str] = None


@app.post("/api/inspections")
def create_inspection(body: InspectionIn, user: dict = Depends(current_user)):
    if body.infrastructure_type not in INFRA_TYPES:
        raise HTTPException(400, f"infrastructure_type must be one of {INFRA_TYPES}")
    with connect() as con:
        cur = con.execute(
            "INSERT INTO inspections (user_id, infrastructure_type, asset_name, location, latitude, longitude, description)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user["id"], body.infrastructure_type, body.asset_name.strip(), body.location, body.latitude,
             body.longitude, body.description),
        )
        return row(con.execute("SELECT * FROM inspections WHERE id = ?", (cur.lastrowid,)).fetchone())


@app.get("/api/inspections")
def list_inspections(q: Optional[str] = None, infrastructure_type: Optional[str] = None,
                     user: dict = Depends(current_user)):
    sql = """SELECT i.*, COUNT(f.id) AS capture_count,
                    (SELECT annotated_path FROM findings WHERE inspection_id = i.id ORDER BY id DESC LIMIT 1) AS thumb
             FROM inspections i LEFT JOIN findings f ON f.inspection_id = i.id
             WHERE i.user_id = ?"""
    args = [user["id"]]
    if q:
        sql += " AND (i.asset_name LIKE ? OR i.location LIKE ?)"
        args += [f"%{q}%", f"%{q}%"]
    if infrastructure_type:
        sql += " AND i.infrastructure_type = ?"
        args.append(infrastructure_type)
    sql += " GROUP BY i.id ORDER BY i.id DESC"
    with connect() as con:
        items = [row(r) for r in con.execute(sql, args)]
        for it in items:
            dets = []
            for (dj,) in con.execute("SELECT detections_json FROM findings WHERE inspection_id = ?", (it["id"],)):
                dets += json.loads(dj)
            it["defect_count"] = len(dets)
            it["thumb_url"] = f"/{it['thumb']}" if it.get("thumb") else None
    return items


@app.get("/api/inspections/{inspection_id}")
def get_inspection(inspection_id: int, user: dict = Depends(current_user)):
    with connect() as con:
        ins = _own_inspection(con, inspection_id, user)
        ins["findings"] = [_finding_out(row(r)) for r in con.execute(
            "SELECT * FROM findings WHERE inspection_id = ? ORDER BY id", (inspection_id,))]
    ins["recommendation"] = detector.recommendation(ins["condition"]) if ins["condition"] else None
    return ins


@app.patch("/api/inspections/{inspection_id}")
def update_inspection(inspection_id: int, body: InspectionPatch, user: dict = Depends(current_user)):
    with connect() as con:
        _own_inspection(con, inspection_id, user)
        if body.notes is not None:
            con.execute("UPDATE inspections SET notes = ? WHERE id = ?", (body.notes, inspection_id))
        if body.status == "Completed":
            con.execute("UPDATE inspections SET status = 'Completed', completed_at = datetime('now') WHERE id = ?",
                        (inspection_id,))
        elif body.status == "In Progress":
            con.execute("UPDATE inspections SET status = 'In Progress', completed_at = NULL WHERE id = ?",
                        (inspection_id,))
    return get_inspection(inspection_id, user)


@app.delete("/api/inspections/{inspection_id}")
def delete_inspection(inspection_id: int, user: dict = Depends(current_user)):
    with connect() as con:
        _own_inspection(con, inspection_id, user)
        paths = [p for r in con.execute("SELECT image_path, annotated_path FROM findings WHERE inspection_id = ?",
                                         (inspection_id,)) for p in r]
        con.execute("DELETE FROM inspections WHERE id = ?", (inspection_id,))
    for p in paths:
        try:
            os.remove(os.path.join(DATA_DIR, p))
        except OSError:
            pass
    return {"ok": True}


# --------------------------------------------------------------------------- #
# Findings (Capture -> Analyze -> Record)
# --------------------------------------------------------------------------- #
@app.post("/api/analyze")
async def analyze_capture(image: UploadFile = File(...), user: dict = Depends(current_user)):
    """Full-quality analysis of a captured frame (not stored until the inspector saves it)."""
    img = await _read_image(image)
    return detector.analyze(img, fast=False)


@app.post("/api/inspections/{inspection_id}/findings")
async def add_finding(inspection_id: int, image: UploadFile = File(...), notes: str = Form(""),
                      detections: Optional[str] = Form(None),
                      processing_ms: Optional[float] = Form(None), user: dict = Depends(current_user)):
    img = await _read_image(image)
    with connect() as con:
        _own_inspection(con, inspection_id, user)
    if detections:
        # the client already analysed this frame (and the inspector may have removed false positives)
        try:
            dets = json.loads(detections)
            assert isinstance(dets, list)
        except Exception:
            raise HTTPException(400, "detections must be a JSON list")
        result = {"detections": dets, "condition": detector.overall_condition(dets), "engine": detector.get_engine().name,
                  "processing_ms": processing_ms}
    else:
        result = detector.analyze(img)

    folder = os.path.join(MEDIA_DIR, str(inspection_id))
    os.makedirs(folder, exist_ok=True)
    stem = uuid.uuid4().hex[:12]
    h, w = img.shape[:2]
    if max(h, w) > 1920:
        s = 1920 / max(h, w)
        img = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
    cv2.imwrite(os.path.join(folder, f"{stem}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 88])
    cv2.imwrite(os.path.join(folder, f"{stem}_ar.jpg"), detector.draw_annotations(img, result["detections"]),
                [cv2.IMWRITE_JPEG_QUALITY, 88])
    rel = f"media/{inspection_id}/{stem}"
    with connect() as con:
        cur = con.execute(
            "INSERT INTO findings (inspection_id, image_path, annotated_path, detections_json, condition, engine,"
            " processing_ms, notes) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (inspection_id, f"{rel}.jpg", f"{rel}_ar.jpg", json.dumps(result["detections"]), result["condition"],
             result.get("engine"), result.get("processing_ms"), notes.strip() or None),
        )
        _refresh_condition(con, inspection_id)
        f = row(con.execute("SELECT * FROM findings WHERE id = ?", (cur.lastrowid,)).fetchone())
    return _finding_out(f)


@app.delete("/api/inspections/{inspection_id}/findings/{finding_id}")
def delete_finding(inspection_id: int, finding_id: int, user: dict = Depends(current_user)):
    with connect() as con:
        _own_inspection(con, inspection_id, user)
        f = row(con.execute("SELECT * FROM findings WHERE id = ? AND inspection_id = ?",
                            (finding_id, inspection_id)).fetchone())
        if not f:
            raise HTTPException(404, "Finding not found")
        con.execute("DELETE FROM findings WHERE id = ?", (finding_id,))
        _refresh_condition(con, inspection_id)
    for p in (f["image_path"], f["annotated_path"]):
        try:
            os.remove(os.path.join(DATA_DIR, p))
        except OSError:
            pass
    return {"ok": True}


@app.get("/api/inspections/{inspection_id}/report.pdf")
def report(inspection_id: int, user: dict = Depends(current_user)):
    with connect() as con:
        ins = _own_inspection(con, inspection_id, user)
        findings = [row(r) for r in con.execute(
            "SELECT * FROM findings WHERE inspection_id = ? ORDER BY id", (inspection_id,))]
    pdf = build_report(ins, findings, user)
    name = f"Inspection_Report_INS-{inspection_id:05d}.pdf"
    return Response(pdf, media_type="application/pdf", headers={"Content-Disposition": f'inline; filename="{name}"'})


# --------------------------------------------------------------------------- #
# Dashboard
# --------------------------------------------------------------------------- #
@app.get("/api/stats")
def stats(user: dict = Depends(current_user)):
    with connect() as con:
        total = con.execute("SELECT COUNT(*) FROM inspections WHERE user_id = ?", (user["id"],)).fetchone()[0]
        active = con.execute("SELECT COUNT(*) FROM inspections WHERE user_id = ? AND status = 'In Progress'",
                             (user["id"],)).fetchone()[0]
        dets = []
        for (dj,) in con.execute("SELECT f.detections_json FROM findings f JOIN inspections i ON i.id = f.inspection_id"
                                 " WHERE i.user_id = ?", (user["id"],)):
            dets += json.loads(dj)
    by_type = {k: sum(1 for d in dets if d["type"] == k) for k in detector.DAMAGE_TYPES}
    return {
        "inspections": total,
        "in_progress": active,
        "defects": len(dets),
        "high_severity": sum(1 for d in dets if d["severity"] == "High"),
        "by_type": by_type,
    }


# --------------------------------------------------------------------------- #
# Media + frontend
# --------------------------------------------------------------------------- #
@app.get("/media/{path:path}")
def media(path: str, user: dict = Depends(current_user)):
    full = os.path.realpath(os.path.join(DATA_DIR, "media", path))
    if not full.startswith(os.path.realpath(MEDIA_DIR) + os.sep) or not os.path.isfile(full):
        raise HTTPException(404, "Not found")
    inspection_id = path.split("/", 1)[0]
    with connect() as con:
        if not inspection_id.isdigit():
            raise HTTPException(404, "Not found")
        _own_inspection(con, int(inspection_id), user)
    return FileResponse(full)


if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
