"""Unit + integration tests (Section 3.5.1). Run:  python -m pytest -q"""
import json
import os
import sys
import tempfile

import cv2
import pytest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.dirname(HERE))
os.environ["DATA_DIR"] = tempfile.mkdtemp(prefix="arinspect_test_")

from fastapi.testclient import TestClient  # noqa: E402

from app import detector  # noqa: E402
from app.main import app  # noqa: E402
from tests import make_samples  # noqa: E402

SAMPLES = os.path.join(HERE, "samples")


@pytest.fixture(scope="session", autouse=True)
def samples():
    if not os.path.exists(os.path.join(SAMPLES, "mixed.jpg")):
        make_samples.main(SAMPLES)


def types_in(name):
    r = detector.analyze(cv2.imread(os.path.join(SAMPLES, name)))
    return {d["type"] for d in r["detections"]}, r


# ---------------- detection engine (unit) ---------------- #
def test_clean_surface_has_no_false_positives():
    t, r = types_in("clean_concrete.jpg")
    assert t == set() and r["condition"] == "Good"


@pytest.mark.parametrize("name,expected", [
    ("crack.jpg", "crack"),
    ("corrosion.jpg", "corrosion"),
    ("spalling.jpg", "surface_damage"),
    ("deformation.jpg", "deformation"),
])
def test_detects_each_damage_type(name, expected):
    t, _ = types_in(name)
    assert expected in t


def test_mixed_scene_detects_multiple_types():
    t, r = types_in("mixed.jpg")
    assert {"crack", "corrosion", "surface_damage"} <= t
    for d in r["detections"]:
        assert d["severity"] in ("Low", "Medium", "High")
        assert 0 < d["confidence"] <= 1
        x, y, w, h = d["bbox"]
        assert 0 <= x <= 1 and 0 <= y <= 1 and 0 < w <= 1 and 0 < h <= 1


def test_live_mode_is_fast():
    img = cv2.imread(os.path.join(SAMPLES, "mixed.jpg"))
    r = detector.analyze(img, fast=True)
    assert r["processing_ms"] < 1000


# ---------------- API (integration) ---------------- #
@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_full_inspection_workflow(client):
    assert client.get("/api/stats").status_code == 401
    r = client.post("/api/auth/login", json={"username": "inspector", "password": "wrong"})
    assert r.status_code == 401
    r = client.post("/api/auth/login", json={"username": "inspector", "password": "inspect123"})
    assert r.status_code == 200

    r = client.post("/api/inspections", json={"infrastructure_type": "Bridge", "asset_name": "Test Bridge",
                                              "location": "Accra"})
    assert r.status_code == 200
    ins_id = r.json()["id"]

    with open(os.path.join(SAMPLES, "mixed.jpg"), "rb") as f:
        live = client.post("/api/detect", files={"image": ("f.jpg", f, "image/jpeg")})
    assert live.status_code == 200 and live.json()["detections"]

    with open(os.path.join(SAMPLES, "mixed.jpg"), "rb") as f:
        r = client.post(f"/api/inspections/{ins_id}/findings", files={"image": ("m.jpg", f, "image/jpeg")},
                        data={"notes": "Pier 2 east face"})
    assert r.status_code == 200
    finding = r.json()
    assert len(finding["detections"]) >= 3
    assert client.get(finding["annotated_url"]).status_code == 200

    # client-side reviewed detections (inspector removed one)
    with open(os.path.join(SAMPLES, "crack.jpg"), "rb") as f:
        r = client.post(f"/api/inspections/{ins_id}/findings", files={"image": ("c.jpg", f, "image/jpeg")},
                        data={"detections": json.dumps(live.json()["detections"][:1])})
    assert r.status_code == 200 and len(r.json()["detections"]) == 1

    r = client.patch(f"/api/inspections/{ins_id}", json={"notes": "Overall OK", "status": "Completed"})
    assert r.json()["status"] == "Completed" and r.json()["condition"]

    r = client.get(f"/api/inspections/{ins_id}/report.pdf")
    assert r.status_code == 200 and r.content[:4] == b"%PDF"

    items = client.get("/api/inspections").json()
    assert items[0]["id"] == ins_id and items[0]["capture_count"] == 2
    s = client.get("/api/stats").json()
    assert s["inspections"] >= 1 and s["defects"] >= 4

    # another user cannot see this inspection
    client.post("/api/auth/register", json={"username": "other", "full_name": "Other User", "password": "secret1"})
    assert client.get(f"/api/inspections/{ins_id}").status_code == 404
    assert client.get(finding["annotated_url"]).status_code == 404


def test_rejects_non_image(client):
    client.post("/api/auth/login", json={"username": "inspector", "password": "inspect123"})
    r = client.post("/api/detect", files={"image": ("x.txt", b"hello", "text/plain")})
    assert r.status_code == 400
