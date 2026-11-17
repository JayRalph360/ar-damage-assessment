"""
Damage Detection and Analysis Engine
====================================

Implements the "Damage Detection and Analysis Engine" component described in
Section 3.4.1 of the capstone.  It analyses an image of an infrastructure
surface and returns the visible defects it finds, each with:

    type        crack | corrosion | deformation | surface_damage
    confidence  0..1
    severity    Low | Medium | High
    bbox        [x, y, w, h]   normalised to 0..1 of the image size
    polygon     [[x, y], ...]  normalised outline used for the AR overlay
    metrics     measurements used to grade the defect

Two back-ends are supported:

1. OpenCV engine (default, no training required)
   Classical computer-vision pipeline: pre-processing (CLAHE, blur),
   morphological black-hat filtering for cracks, HSV colour segmentation for
   corrosion, local-texture analysis for spalling / surface deterioration and
   edge-curvature analysis for deformation.

2. YOLO engine (optional)
   If a YOLOv8 model exported to ONNX is placed at  models/damage.onnx  with its
   class names (one per line) in  models/classes.txt, it is loaded with OpenCV's
   DNN module and used for detection instead.  No extra Python packages needed.
"""
from __future__ import annotations

import math
import os
import time
from dataclasses import dataclass, field, asdict
from typing import List, Optional

import cv2
import numpy as np

DAMAGE_TYPES = {
    "crack": "Crack",
    "corrosion": "Corrosion",
    "deformation": "Deformation",
    "surface_damage": "Surface Damage",
}

# BGR colours used when drawing annotated images (frontend uses the same hues)
COLOURS = {
    "crack": (60, 60, 235),           # red
    "corrosion": (0, 140, 255),       # orange
    "deformation": (200, 80, 170),    # purple
    "surface_damage": (0, 200, 230),  # yellow
}

SEVERITY_RANK = {"Low": 1, "Medium": 2, "High": 3}

MODEL_DIR = os.environ.get(
    "MODEL_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
)


@dataclass
class Detection:
    type: str
    confidence: float
    severity: str
    bbox: List[float]
    polygon: List[List[float]] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)

    @property
    def label(self) -> str:
        return DAMAGE_TYPES.get(self.type, self.type.replace("_", " ").title())

    def to_dict(self) -> dict:
        d = asdict(self)
        d["label"] = self.label
        return d


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _resize_for_processing(img: np.ndarray, max_side: int) -> np.ndarray:
    h, w = img.shape[:2]
    scale = max_side / max(h, w)
    if scale < 1:
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    return img


def _norm_bbox(x, y, w, h, W, H) -> List[float]:
    return [round(x / W, 4), round(y / H, 4), round(w / W, 4), round(h / H, 4)]


def _norm_polygon(contour: np.ndarray, W: int, H: int, max_points: int = 60) -> List[List[float]]:
    peri = cv2.arcLength(contour, True)
    eps = max(1.0, 0.004 * peri)
    approx = cv2.approxPolyDP(contour, eps, True).reshape(-1, 2)
    while len(approx) > max_points:
        eps *= 1.5
        approx = cv2.approxPolyDP(contour, eps, True).reshape(-1, 2)
    return [[round(float(px) / W, 4), round(float(py) / H, 4)] for px, py in approx]


def _iou(a: List[float], b: List[float]) -> float:
    ax2, ay2 = a[0] + a[2], a[1] + a[3]
    bx2, by2 = b[0] + b[2], b[1] + b[3]
    ix = max(0.0, min(ax2, bx2) - max(a[0], b[0]))
    iy = max(0.0, min(ay2, by2) - max(a[1], b[1]))
    inter = ix * iy
    union = a[2] * a[3] + b[2] * b[3] - inter
    return inter / union if union > 0 else 0.0


def _overlap_of_smaller(a: List[float], b: List[float]) -> float:
    ax2, ay2 = a[0] + a[2], a[1] + a[3]
    bx2, by2 = b[0] + b[2], b[1] + b[3]
    ix = max(0.0, min(ax2, bx2) - max(a[0], b[0]))
    iy = max(0.0, min(ay2, by2) - max(a[1], b[1]))
    smaller = min(a[2] * a[3], b[2] * b[3])
    return (ix * iy) / smaller if smaller > 0 else 0.0


# --------------------------------------------------------------------------- #
# OpenCV engine
# --------------------------------------------------------------------------- #
class OpenCVDamageDetector:
    name = "opencv"

    def __init__(self, max_side: int = 960):
        self.max_side = max_side

    # ---- public --------------------------------------------------------- #
    def detect(self, img: np.ndarray, fast: bool = False) -> List[Detection]:
        img = _resize_for_processing(img, 640 if fast else self.max_side)
        H, W = img.shape[:2]
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        gray_eq = clahe.apply(cv2.GaussianBlur(gray, (3, 3), 0))

        corrosion, corr_mask = self._corrosion(img, W, H)
        cracks, crack_mask = self._cracks(gray, W, H, exclude=corr_mask)
        surface = self._surface_damage(gray, W, H, exclude=cv2.bitwise_or(crack_mask, corr_mask))
        deform = [] if fast else self._deformation(gray, W, H, exclude=cv2.bitwise_or(crack_mask, corr_mask))

        dets = corrosion + cracks + surface + deform
        return self._suppress(dets)

    # ---- cracks --------------------------------------------------------- #
    def _cracks(self, gray: np.ndarray, W: int, H: int, exclude: np.ndarray):
        diag = math.hypot(W, H)
        k = max(9, int(diag / 60) | 1)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
        # edge-preserving denoise removes surface grain but keeps thin dark cracks
        smooth = cv2.bilateralFilter(gray, 7, 40, 7)
        blackhat = cv2.morphologyEx(smooth, cv2.MORPH_BLACKHAT, kernel)

        # Adaptive threshold: crack pixels are statistical outliers of the black-hat response,
        # with a contrast floor so clean surfaces stay clean
        thr = max(float(blackhat.mean() + 4 * blackhat.std()), 30.0)
        # Hysteresis: strong crack pixels seed the mask, weaker pixels connected to them are kept,
        # so a crack that thins out towards its tip is still traced as one defect.
        strong = (blackhat > thr).astype(np.uint8)
        weak = (blackhat > max(thr * 0.55, 22.0)).astype(np.uint8)
        weak = cv2.morphologyEx(weak, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))
        n, labels = cv2.connectedComponents(weak, connectivity=8)
        seeded = np.unique(labels[(strong > 0) & (labels > 0)])
        mask = (np.isin(labels, seeded) & (labels > 0)).astype(np.uint8) * 255
        mask = cv2.bitwise_and(mask, cv2.bitwise_not(exclude))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2)))

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        out: List[Detection] = []
        keep_mask = np.zeros_like(mask)
        for c in contours:
            area = cv2.contourArea(c)
            if area < 0.00015 * W * H:
                continue
            (cx, cy), (rw, rh), _ = cv2.minAreaRect(c)
            length = max(rw, rh)
            if length < 0.08 * diag:
                continue
            # Skeleton-free width estimate: area spread over the length
            single = np.zeros_like(mask)
            cv2.drawContours(single, [c], -1, 255, -1)
            dist = cv2.distanceTransform(single, cv2.DIST_L2, 3)
            max_width = float(dist.max() * 2)
            path_len = max(length, cv2.arcLength(c, False) / 2)
            mean_width = area / path_len
            elongation = path_len / max(mean_width, 1.0)
            if elongation < 8:
                continue
            # contrast of the crack versus its surroundings
            contrast = float(cv2.mean(blackhat, mask=single)[0])
            if contrast < thr * 0.9:
                continue

            x, y, w, h = cv2.boundingRect(c)
            rel_w = mean_width / diag
            rel_len = path_len / diag
            if rel_w > 0.009 or rel_len > 0.55:
                severity = "High"
            elif rel_w > 0.004 or rel_len > 0.3:
                severity = "Medium"
            else:
                severity = "Low"
            conf = min(0.97, 0.45 + 0.25 * min(1.0, elongation / 30) + 0.27 * min(1.0, contrast / 90))
            out.append(Detection(
                type="crack",
                confidence=round(conf, 2),
                severity=severity,
                bbox=_norm_bbox(x, y, w, h, W, H),
                polygon=_norm_polygon(c, W, H),
                metrics={
                    "length_px": round(path_len, 1),
                    "mean_width_px": round(mean_width, 2),
                    "max_width_px": round(max_width, 2),
                    "length_pct_of_view": round(rel_len * 100, 1),
                },
            ))
            cv2.drawContours(keep_mask, [c], -1, 255, -1)
        keep_mask = cv2.dilate(keep_mask, np.ones((7, 7), np.uint8))
        return out, keep_mask

    # ---- corrosion ------------------------------------------------------ #
    def _corrosion(self, img: np.ndarray, W: int, H: int):
        hsv = cv2.cvtColor(cv2.GaussianBlur(img, (5, 5), 0), cv2.COLOR_BGR2HSV)
        # rust: orange / brown / reddish-brown hues with enough saturation
        m1 = cv2.inRange(hsv, (5, 90, 45), (24, 255, 235))
        m2 = cv2.inRange(hsv, (0, 120, 40), (5, 255, 170))
        m3 = cv2.inRange(hsv, (172, 120, 40), (180, 255, 170))
        mask = m1 | m2 | m3
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        out: List[Detection] = []
        keep = np.zeros(mask.shape, np.uint8)
        total = W * H
        for c in contours:
            area = cv2.contourArea(c)
            if area < 0.004 * total:
                continue
            single = np.zeros(mask.shape, np.uint8)
            cv2.drawContours(single, [c], -1, 255, -1)
            mean_h, mean_s, mean_v, _ = cv2.mean(hsv, mask=single)
            # rust is textured: very uniform orange areas (paint, signage) are less likely rust
            sat_std = float(np.std(hsv[..., 1][single > 0]))
            pct = area / total * 100
            severity = "High" if pct > 15 else "Medium" if pct > 4 else "Low"
            conf = 0.45 + 0.25 * min(1.0, mean_s / 200) + 0.2 * min(1.0, sat_std / 40) + 0.07 * min(1.0, pct / 10)
            x, y, w, h = cv2.boundingRect(c)
            out.append(Detection(
                type="corrosion",
                confidence=round(min(conf, 0.96), 2),
                severity=severity,
                bbox=_norm_bbox(x, y, w, h, W, H),
                polygon=_norm_polygon(c, W, H),
                metrics={"area_pct_of_view": round(pct, 2), "mean_saturation": round(mean_s, 1)},
            ))
            cv2.drawContours(keep, [c], -1, 255, -1)
        return out, keep

    # ---- spalling / surface deterioration / potholes -------------------- #
    def _surface_damage(self, gray: np.ndarray, W: int, H: int, exclude: np.ndarray):
        g = gray.astype(np.float32)
        k = max(15, int(min(W, H) / 25) | 1)
        mean = cv2.blur(g, (k, k))
        sq = cv2.blur(g * g, (k, k))
        local_std = np.sqrt(np.maximum(sq - mean * mean, 0))

        global_med = float(np.median(g))
        std_med = float(np.median(local_std))
        big = cv2.blur(g, (k * 3 | 1, k * 3 | 1))
        darker = (big < global_med - max(18.0, 0.12 * global_med))
        rough = local_std > max(std_med * 1.8, std_med + 9)
        mask = (darker & rough).astype(np.uint8) * 255
        mask = cv2.bitwise_and(mask, cv2.bitwise_not(exclude))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        out: List[Detection] = []
        total = W * H
        for c in contours:
            area = cv2.contourArea(c)
            if area < 0.012 * total or area > 0.7 * total:
                continue
            (_, _), (rw, rh), _ = cv2.minAreaRect(c)
            if max(rw, rh) / max(1.0, min(rw, rh)) > 5:  # elongated -> crack-like, not spalling
                continue
            single = np.zeros(mask.shape, np.uint8)
            cv2.drawContours(single, [c], -1, 255, -1)
            inside = float(cv2.mean(gray, mask=single)[0])
            depth = (global_med - inside) / max(global_med, 1)
            rough_v = float(cv2.mean(local_std, mask=single)[0])
            pct = area / total * 100
            severity = "High" if pct > 12 or depth > 0.45 else "Medium" if pct > 4 or depth > 0.25 else "Low"
            conf = 0.4 + 0.3 * min(1.0, depth / 0.4) + 0.2 * min(1.0, rough_v / (std_med * 3 + 1))
            x, y, w, h = cv2.boundingRect(c)
            out.append(Detection(
                type="surface_damage",
                confidence=round(min(conf, 0.93), 2),
                severity=severity,
                bbox=_norm_bbox(x, y, w, h, W, H),
                polygon=_norm_polygon(c, W, H),
                metrics={"area_pct_of_view": round(pct, 2), "relative_depth": round(depth, 2)},
            ))
        return out

    # ---- deformation (bending / sagging of straight members) ------------ #
    def _deformation(self, gray: np.ndarray, W: int, H: int, exclude: np.ndarray):
        diag = math.hypot(W, H)
        edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 140)
        edges = cv2.bitwise_and(edges, cv2.bitwise_not(cv2.dilate(exclude, np.ones((9, 9), np.uint8))))
        edges = cv2.dilate(edges, np.ones((3, 3), np.uint8))
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        out: List[Detection] = []
        for c in contours:
            pts = c.reshape(-1, 2).astype(np.float32)
            if len(pts) < 80:
                continue
            x, y, w, h = cv2.boundingRect(c)
            span = max(w, h)
            if span < 0.35 * diag:
                continue
            # orient along the dominant axis and fit a straight line + a parabola
            horiz = w >= h
            u = pts[:, 0] if horiz else pts[:, 1]
            v = pts[:, 1] if horiz else pts[:, 0]
            # An edge contour of a member traces both of its faces. Take the near face (min) and
            # far face (max) separately for each slice along the member, trimming the end caps.
            bins = np.linspace(u.min(), u.max(), 41)
            idx = np.digitize(u, bins)
            cu, near, far = [], [], []
            for b in range(3, len(bins) - 2):
                sel = v[idx == b]
                if len(sel):
                    cu.append((bins[b - 1] + bins[b]) / 2)
                    near.append(float(sel.min()))
                    far.append(float(sel.max()))
            if len(cu) < 20:
                continue
            cu = np.array(cu)
            thickness = (h if horiz else w)
            if thickness > 0.45 * span:
                continue
            best = None
            for face in (np.array(near), np.array(far)):
                line = np.polyfit(cu, face, 1)
                dev_line = np.abs(face - np.polyval(line, cu))
                para = np.polyfit(cu, face, 2)
                res_para = np.abs(face - np.polyval(para, cu))
                sag = float(dev_line.max())
                smooth = float(res_para.mean()) < max(2.5, 0.25 * float(dev_line.mean()))
                if smooth and (best is None or sag > best[0]):
                    best = (sag, face)
            if best is None:
                continue
            sag, cv_ = best
            sag_ratio = sag / span
            if not (0.025 <= sag_ratio <= 0.2):
                continue
            severity = "High" if sag_ratio > 0.08 else "Medium" if sag_ratio > 0.045 else "Low"
            conf = 0.45 + 0.35 * min(1.0, sag_ratio / 0.08)
            pad = int(0.02 * diag)
            x0, y0 = max(0, x - pad), max(0, y - pad)
            x1, y1 = min(W, x + w + pad), min(H, y + h + pad)
            poly_pts = np.stack([cu, cv_], 1) if horiz else np.stack([cv_, cu], 1)
            poly = [[round(float(px) / W, 4), round(float(py) / H, 4)] for px, py in poly_pts[::2]]
            out.append(Detection(
                type="deformation",
                confidence=round(min(conf, 0.9), 2),
                severity=severity,
                bbox=_norm_bbox(x0, y0, x1 - x0, y1 - y0, W, H),
                polygon=poly,
                metrics={"deflection_px": round(sag, 1), "deflection_ratio": round(sag_ratio, 3),
                         "member_span_px": int(span), "open_path": True},
            ))
        return out

    # ---- overlap handling ----------------------------------------------- #
    @staticmethod
    def _suppress(dets: List[Detection], max_dets: int = 25) -> List[Detection]:
        dets = sorted(dets, key=lambda d: d.confidence, reverse=True)
        kept: List[Detection] = []
        for d in dets:
            dup = False
            for k in kept:
                if k.type == d.type and (_iou(k.bbox, d.bbox) > 0.5 or _overlap_of_smaller(k.bbox, d.bbox) > 0.85):
                    dup = True
                    break
            if not dup:
                kept.append(d)
        return kept[:max_dets]


# --------------------------------------------------------------------------- #
# Optional YOLOv8 ONNX engine
# --------------------------------------------------------------------------- #
class YoloOnnxDamageDetector:
    """YOLOv8 detector exported with  `yolo export model=best.pt format=onnx opset=12`."""

    name = "yolo"

    # map dataset class names to the four system damage types
    ALIASES = {
        "crack": "crack", "cracks": "crack", "longitudinal crack": "crack", "transverse crack": "crack",
        "alligator crack": "crack", "d00": "crack", "d10": "crack", "d20": "crack",
        "corrosion": "corrosion", "rust": "corrosion", "exposed rebar": "corrosion", "exposed_rebar": "corrosion",
        "rebar": "corrosion", "efflorescence": "surface_damage",
        "spalling": "surface_damage", "pothole": "surface_damage", "potholes": "surface_damage", "d40": "surface_damage",
        "deformation": "deformation", "bending": "deformation", "dent": "deformation",
        "surface_damage": "surface_damage", "surface damage": "surface_damage",
    }

    def __init__(self, model_path: str, classes_path: str, input_size: int = 640, conf: float = 0.3):
        self.net = cv2.dnn.readNetFromONNX(model_path)
        with open(classes_path, encoding="utf-8") as f:
            self.classes = [ln.strip() for ln in f if ln.strip()]
        self.size = input_size
        self.conf = conf

    def detect(self, img: np.ndarray, fast: bool = False) -> List[Detection]:
        H, W = img.shape[:2]
        s = max(H, W)
        square = np.zeros((s, s, 3), np.uint8)
        square[:H, :W] = img
        blob = cv2.dnn.blobFromImage(square, 1 / 255.0, (self.size, self.size), swapRB=True)
        self.net.setInput(blob)
        out = self.net.forward()[0]           # (4 + nc, N)
        out = out.T if out.shape[0] < out.shape[1] else out
        boxes, scores, cls_ids = [], [], []
        factor = s / self.size
        for row in out:
            cls_scores = row[4:]
            cid = int(np.argmax(cls_scores))
            sc = float(cls_scores[cid])
            if sc < self.conf:
                continue
            cx, cy, bw, bh = row[:4] * factor
            boxes.append([int(cx - bw / 2), int(cy - bh / 2), int(bw), int(bh)])
            scores.append(sc)
            cls_ids.append(cid)
        idxs = cv2.dnn.NMSBoxes(boxes, scores, self.conf, 0.45)
        dets: List[Detection] = []
        for i in np.array(idxs).flatten() if len(idxs) else []:
            x, y, w, h = boxes[i]
            x, y = max(0, x), max(0, y)
            w, h = min(W - x, w), min(H - y, h)
            name = self.classes[cls_ids[i]] if cls_ids[i] < len(self.classes) else str(cls_ids[i])
            dtype = self.ALIASES.get(name.lower(), name.lower().replace(" ", "_"))
            pct = w * h / (W * H) * 100
            severity = "High" if pct > 15 else "Medium" if pct > 4 else "Low"
            bb = _norm_bbox(x, y, w, h, W, H)
            dets.append(Detection(
                type=dtype, confidence=round(scores[i], 2), severity=severity, bbox=bb,
                polygon=[[bb[0], bb[1]], [bb[0] + bb[2], bb[1]], [bb[0] + bb[2], bb[1] + bb[3]], [bb[0], bb[1] + bb[3]]],
                metrics={"area_pct_of_view": round(pct, 2), "model_class": name},
            ))
        return dets


# --------------------------------------------------------------------------- #
# Facade
# --------------------------------------------------------------------------- #
_engine = None


def get_engine():
    global _engine
    if _engine is None:
        onnx = os.path.join(MODEL_DIR, "damage.onnx")
        classes = os.path.join(MODEL_DIR, "classes.txt")
        if os.path.exists(onnx) and os.path.exists(classes):
            _engine = YoloOnnxDamageDetector(onnx, classes)
        else:
            _engine = OpenCVDamageDetector()
    return _engine


def overall_condition(dets: List[dict]) -> str:
    """Condition rating for a captured view / whole inspection."""
    if not dets:
        return "Good"
    worst = max(SEVERITY_RANK.get(d["severity"], 1) for d in dets)
    highs = sum(1 for d in dets if d["severity"] == "High")
    if worst == 3 and highs >= 2:
        return "Critical"
    if worst == 3:
        return "Poor"
    if worst == 2:
        return "Fair"
    return "Fair" if len(dets) >= 4 else "Good (minor defects)"


def recommendation(condition: str) -> str:
    return {
        "Good": "No visible defects detected. Continue routine inspection schedule.",
        "Good (minor defects)": "Minor defects present. Monitor at next scheduled inspection.",
        "Fair": "Defects require monitoring. Schedule maintenance and re-inspect within 6 months.",
        "Poor": "Significant damage detected. Refer to a structural engineer and plan repairs promptly.",
        "Critical": "Severe damage detected. Restrict use if necessary and arrange urgent engineering assessment.",
    }.get(condition, "")


def analyze(img: np.ndarray, fast: bool = False) -> dict:
    t0 = time.perf_counter()
    engine = get_engine()
    dets = [d.to_dict() for d in engine.detect(img, fast=fast)]
    cond = overall_condition(dets)
    counts = {}
    for d in dets:
        counts[d["type"]] = counts.get(d["type"], 0) + 1
    return {
        "engine": engine.name,
        "processing_ms": round((time.perf_counter() - t0) * 1000, 1),
        "image_size": [int(img.shape[1]), int(img.shape[0])],
        "detections": dets,
        "counts": counts,
        "condition": cond,
        "recommendation": recommendation(cond),
    }


def draw_annotations(img: np.ndarray, dets: List[dict]) -> np.ndarray:
    """Burn the AR overlay into a copy of the image (used for saved records and PDF reports)."""
    out = img.copy()
    H, W = out.shape[:2]
    overlay = out.copy()
    thick = max(2, int(max(W, H) / 400))
    font_scale = max(0.5, max(W, H) / 1400)
    for i, d in enumerate(dets, 1):
        col = COLOURS.get(d["type"], (255, 255, 255))
        pts = np.array([[p[0] * W, p[1] * H] for p in d.get("polygon") or []], np.int32)
        if len(pts) >= 3 and not d.get("metrics", {}).get("open_path"):
            cv2.fillPoly(overlay, [pts], col)
            cv2.polylines(out, [pts], True, col, thick, cv2.LINE_AA)
        elif len(pts) >= 2:
            cv2.polylines(out, [pts], False, col, thick * 2, cv2.LINE_AA)
        x, y, w, h = [int(v) for v in (d["bbox"][0] * W, d["bbox"][1] * H, d["bbox"][2] * W, d["bbox"][3] * H)]
        cv2.rectangle(out, (x, y), (x + w, y + h), col, max(1, thick // 2), cv2.LINE_AA)
        label = f"{i}. {d['label']} {int(d['confidence'] * 100)}% [{d['severity']}]"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)
        ty = y - 6 if y - th - 10 > 0 else y + h + th + 6
        cv2.rectangle(out, (x, ty - th - 6), (x + tw + 8, ty + 4), col, -1)
        cv2.putText(out, label, (x + 4, ty), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), 1, cv2.LINE_AA)
    return cv2.addWeighted(overlay, 0.25, out, 0.75, 0)
