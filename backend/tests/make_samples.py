"""Generate synthetic infrastructure surfaces for testing / demos (no internet needed)."""
import os
import sys

import cv2
import numpy as np

rng = np.random.default_rng(7)


def concrete(w=1200, h=900, base=160):
    noise = rng.normal(0, 14, (h // 4, w // 4)).astype(np.float32)
    noise = cv2.resize(noise, (w, h), interpolation=cv2.INTER_CUBIC)
    fine = rng.normal(0, 7, (h, w)).astype(np.float32)
    g = np.clip(base + noise + fine, 0, 255).astype(np.uint8)
    img = cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)
    img = (img * np.array([0.98, 1.0, 1.02])).clip(0, 255).astype(np.uint8)
    # aggregate speckles
    for _ in range(900):
        x, y = rng.integers(0, w), rng.integers(0, h)
        c = int(rng.integers(110, 200))
        cv2.circle(img, (int(x), int(y)), int(rng.integers(1, 3)), (c, c, c), -1)
    return img


def add_crack(img, start, steps=60, step=14, width=4, angle=0.4):
    x, y = start
    a = angle
    pts = []
    for i in range(steps):
        a += rng.normal(0, 0.25)
        x += step * np.cos(a)
        y += step * np.sin(a)
        pts.append((int(x), int(y)))
    for i in range(1, len(pts)):
        wv = max(1, int(width * (1 - i / len(pts) * 0.6) + rng.normal(0, 0.6)))
        cv2.line(img, pts[i - 1], pts[i], (45, 45, 48), wv, cv2.LINE_AA)
        # branch
        if i % 22 == 0:
            bx, by = pts[i]
            ba = a + rng.choice([-1, 1]) * 0.9
            for _ in range(10):
                nx, ny = int(bx + 10 * np.cos(ba)), int(by + 10 * np.sin(ba))
                cv2.line(img, (bx, by), (nx, ny), (55, 55, 58), max(1, wv - 1), cv2.LINE_AA)
                bx, by = nx, ny
                ba += rng.normal(0, 0.3)
    return img


def add_rust(img, centre, r=150):
    h, w = img.shape[:2]
    mask = np.zeros((h, w), np.float32)
    for _ in range(25):
        cx = int(centre[0] + rng.normal(0, r / 2))
        cy = int(centre[1] + rng.normal(0, r / 2))
        cv2.circle(mask, (cx, cy), int(rng.integers(r // 4, r // 2)), 1.0, -1)
    mask = cv2.GaussianBlur(mask, (31, 31), 0)[..., None]
    tex = rng.normal(0, 25, (h, w, 1)).astype(np.float32)
    rust = np.concatenate([30 + tex * 0.3, 70 + tex * 0.6, 150 + tex], axis=2)  # BGR brown-orange
    out = img.astype(np.float32) * (1 - mask) + rust * mask
    return out.clip(0, 255).astype(np.uint8)


def add_spall(img, centre, r=140):
    h, w = img.shape[:2]
    pts = []
    for t in np.linspace(0, 2 * np.pi, 24, endpoint=False):
        rr = r * (0.7 + 0.5 * rng.random())
        pts.append((int(centre[0] + rr * np.cos(t)), int(centre[1] + rr * np.sin(t))))
    mask = np.zeros((h, w), np.uint8)
    cv2.fillPoly(mask, [np.array(pts)], 255)
    rough = rng.normal(0, 40, (h, w)).astype(np.float32)
    rough = cv2.GaussianBlur(rough, (3, 3), 0)
    dark = img.astype(np.float32) * 0.5 + rough[..., None]
    for _ in range(120):  # exposed aggregate
        x = int(centre[0] + rng.normal(0, r / 2)); y = int(centre[1] + rng.normal(0, r / 2))
        c = float(rng.integers(30, 150))
        cv2.circle(dark, (x, y), int(rng.integers(3, 9)), (c, c, c), -1)
    m = (mask > 0)[..., None]
    return np.where(m, dark, img.astype(np.float32)).clip(0, 255).astype(np.uint8)


def add_bent_beam(img, sag=70):
    h, w = img.shape[:2]
    out = img.copy()
    xs = np.arange(80, w - 80)
    mid = (xs[0] + xs[-1]) / 2
    half = (xs[-1] - xs[0]) / 2
    top = 250 + sag * (1 - ((xs - mid) / half) ** 2)
    for x, t in zip(xs, top):
        out[int(t):int(t) + 90, x] = (70, 72, 78)
    return out


def main(dest):
    os.makedirs(dest, exist_ok=True)
    c = concrete()
    cv2.imwrite(os.path.join(dest, "clean_concrete.jpg"), c)
    cv2.imwrite(os.path.join(dest, "crack.jpg"), add_crack(concrete(), (120, 200), angle=0.45))
    cv2.imwrite(os.path.join(dest, "corrosion.jpg"), add_rust(concrete(base=135), (600, 450), r=170))
    cv2.imwrite(os.path.join(dest, "spalling.jpg"), add_spall(concrete(), (620, 470)))
    cv2.imwrite(os.path.join(dest, "deformation.jpg"), add_bent_beam(concrete(base=175)))
    mixed = add_crack(concrete(), (80, 120), steps=45, angle=0.3)
    mixed = add_rust(mixed, (950, 650), r=110)
    mixed = add_spall(mixed, (330, 650), r=110)
    cv2.imwrite(os.path.join(dest, "mixed.jpg"), mixed)
    print("samples written to", dest)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "samples"))
