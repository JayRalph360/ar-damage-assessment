# AR-Based Real-Time Infrastructure Damage Assessment System

Capstone implementation for **Jerry Neequaye Kotey (ADS23A00008Y)**, ASDASS, Accra Institute of Technology.

A mobile web application that uses the phone camera to detect infrastructure damage in real time
(**crack, corrosion, deformation, surface damage**), draws the results as an **AR overlay** on the live view,
and records each assessment in an inspection record with a downloadable **PDF report**.

Default login: **inspector / inspect123** (or create a new account from the login screen).

---

## 1. Run it (5 minutes)

You need **Python 3.10+** on a laptop. The phone and laptop must be on the **same Wi-Fi** (or use the phone's hotspot).

**Windows:** double-click `start_windows.bat`
**Mac / Linux:** `./start_mac_linux.sh`

The first run creates a virtual environment and installs the packages (needs internet once). Then it prints:

```
Laptop:  https://localhost:8443
Phone:   https://192.168.x.x:8443   (same Wi-Fi; accept the certificate warning)
```

On the phone, open the **Phone** address in Chrome. You will see a certificate warning because the certificate is
self-signed. Tap **Advanced, then Proceed**. Log in, tap **Start Inspection**, and allow camera access.

> Why HTTPS? Browsers only allow live camera access on secure (HTTPS) pages. If you run `python run.py --http`,
> the app still works, but you must use the **Upload** button, which opens the phone's camera app.

**Windows firewall:** when Windows asks, tick **Private networks** and click **Allow**. Otherwise the phone
cannot connect. If you missed the pop-up, allow port 8443 in Windows Defender Firewall.

**"Smart App Control blocked a file that may be unsafe"** (Windows 11): Windows blocks unsigned scripts that
came from a download. Do **not** turn Smart App Control off, because it cannot be turned back on without resetting
the PC. Type the commands yourself instead:

1. Open the unzipped `ar-damage-assessment` folder in File Explorer, click the address bar, type `cmd` and press Enter.
2. Run these one at a time. The first two are needed only once:
   ```
   python -m venv .venv
   .venv\Scripts\python -m pip install -r backend\requirements.txt
   .venv\Scripts\python run.py
   ```
   Next time, only the last line is needed.

* **"python is not recognized":** install Python from python.org and tick **"Add python.exe to PATH"** on the
  first installer screen. Then open a new Command Prompt.
* **"An Application Control policy has blocked this file":** Smart App Control blocked one of the installed
  packages. Copy the full error message so it can be dealt with.

### Using it on the laptop
Open **https://localhost:8443** in Chrome or Edge on the laptop running the server. The webcam works for live AR,
and **Upload** lets you analyse photos saved on the laptop. For a demo, it works well to use the phone for live
AR and the laptop for uploads and reports.

---

## 1b. Removing the "Not secure" / certificate warning

By default the app makes its **own** HTTPS certificate, so browsers do not recognise it and show a warning. The
app works fine if you click **Advanced, then Proceed**, but to remove the warning pick one option:

| Option | Devices | Internet needed? | Effort |
|---|---|---|---|
| A. Plain localhost | This laptop only | No | None |
| B. Cloudflare Tunnel | Any device, anywhere | Yes | 2 min |
| C. mkcert trusted certificate | Laptop + phones on the same Wi-Fi | No | 10 min, best for a defense or demo |

### A. Laptop only: no certificate needed
```
.venv\Scripts\python run.py --http
```
Open **http://localhost:8000**. Browsers treat `localhost` as secure, so there is no warning and the webcam
works. This does not work for a phone, because a phone connects with the laptop's IP address, not `localhost`.

### B. Cloudflare Tunnel: a real certificate, works on any phone
1. Install once:  `winget install --id Cloudflare.cloudflared`
   (Mac: `brew install cloudflared`, Linux: see developers.cloudflare.com)
2. Start the app:  `.venv\Scripts\python run.py --http`
3. In a **second** Command Prompt:  `cloudflared tunnel --url http://localhost:8000`
4. Open the printed `https://<random-words>.trycloudflare.com` link on any phone or computer.

Notes: the link changes every time you start the tunnel. Both devices need internet, and live detection is
slower because frames travel over the internet. Anyone with the link can reach the login page, so press Ctrl+C
in the tunnel window when you are finished.

### C. mkcert: a trusted local certificate, works offline
`run.py` automatically uses `backend\data\certs\trusted-cert.pem` and `trusted-key.pem` if they exist.

1. Install mkcert and create your local certificate authority (once per laptop):
   ```
   winget install FiloSottile.mkcert
   mkcert -install
   ```
   (Mac: `brew install mkcert`.) Close the Command Prompt and open a new one afterwards so `mkcert` is found.
2. Find the laptop's IP address: run `.venv\Scripts\python run.py`, read the **Phone:** line, then stop it with Ctrl+C.
3. From inside the `ar-damage-assessment` folder, create the certificate. Replace `192.168.1.5` with your IP:
   ```
   mkcert -cert-file backend\data\certs\trusted-cert.pem -key-file backend\data\certs\trusted-key.pem localhost 127.0.0.1 192.168.1.5
   ```
4. Make the **phone** trust it (once per phone):
   * Run `mkcert -CAROOT` to see the folder containing **`rootCA.pem`**.
   * Send `rootCA.pem` to the phone (USB, email, WhatsApp). **Never share `rootCA-key.pem`.**
   * Android: **Settings → Security → More security settings → Encryption & credentials → Install a certificate
     → CA certificate**, then choose the file. Menu names differ between phones; searching Settings for
     "certificate" finds it.
   * iPhone: open the file, install the profile in **Settings → Profile Downloaded**, then enable it in
     **Settings → General → About → Certificate Trust Settings**.
5. Start normally with `.venv\Scripts\python run.py`. It prints "Using trusted certificate (mkcert)". Open
   `https://<IP>:8443` on the laptop or phone, with no warning.

**If the laptop's IP changes** (for example, on a different Wi-Fi network at the venue), repeat step 3 with the
new IP. The phone does not need step 4 again. To go back to the self-signed certificate, delete the two
`trusted-*.pem` files.

**Optional:** in Chrome on the phone, tap **⋮ then Add to Home screen** so it launches like an installed app.

### Manual install (if you don't want the scripts)
```
python -m venv .venv
.venv\Scripts\activate           (Windows)   |   source .venv/bin/activate   (Mac/Linux)
pip install -r backend/requirements.txt
python run.py
```

### Run the tests
```
cd backend
python -m pytest -q          # 9 tests: detection engine (unit) + full API workflow (integration)
python tests/make_samples.py # regenerates the synthetic test images in tests/samples/
```

---

## 2. Using the app (follows Figure 4.4, the wireframe)

| Screen | What it does |
|---|---|
| **Welcome / Login** | User authentication, plus a "Create an account" option |
| **Dashboard** | Start Inspection, Inspection History, totals, defects-by-type chart, recent inspections |
| **Start Inspection** | Pick infrastructure type, enter asset name, location (GPS button) and scope, then Begin Inspection |
| **AR Camera / Inspection View** | Live camera with **real-time AR damage overlay** (outlines, labels, severity), FPS and latency HUD. Buttons: **Capture** (freeze the frame), then **Analyze**, plus **Upload** and **Exit** |
| **Damage Detection Result** | Full-quality analysis of the captured frame: AR overlay, damage type, severity, confidence, measurements, condition rating and recommendation. The inspector can **untick false detections**, add notes, then **Save Assessment** |
| **Inspection Record** | Asset details, overall condition, every saved capture, overall notes, **Complete**, **Report (PDF)** |
| **Inspection History** | Search and filter all saved inspections by infrastructure type |

Tip for the demo: print or display the images in `backend/tests/samples/` on a screen, then point the phone at them.
For real-world testing, cracked walls, rusty railings or gates, and broken pavement work well.

---

## 3. Architecture (matches Section 3.4.1 and Figure 4.2)

```
Phone browser (AR Client Application)          Laptop / server
┌───────────────────────────────┐   HTTPS   ┌──────────────────────────────────────┐
│ frontend/  (HTML, CSS, JS)    │ ────────▶ │ backend/app/main.py   FastAPI REST   │
│ • camera capture (getUserMedia)│ frames   │ backend/app/detector.py              │
│ • AR overlay on canvas         │ ◀──────── │   Damage Detection & Analysis Engine │
│ • inspection workflow screens  │ results  │ backend/app/db.py  SQLite + images   │
└───────────────────────────────┘           │ backend/app/reports.py  PDF reports  │
                                            └──────────────────────────────────────┘
```

* **AR Client Application:** `frontend/`. The camera feed is sampled about 8 times per second and sent to the
  detection engine (`/api/detect`). Results come back as normalised polygons and are drawn over the live video,
  aligned to the camera view.
* **Damage Detection and Analysis Engine:** `backend/app/detector.py` (Python + OpenCV + NumPy)
  * *Pre-processing:* resizing, bilateral (edge-preserving) denoising, CLAHE contrast enhancement
  * *Crack:* morphological black-hat filter, adaptive statistical threshold, hysteresis linking, then shape
    filtering (elongation, length). Severity comes from crack width and length.
  * *Corrosion:* HSV colour segmentation of rust hues, morphological cleanup, area and texture scoring
  * *Surface damage (spalling / potholes / deterioration):* local texture (standard deviation) combined with darkness analysis
  * *Deformation:* edge extraction and line-vs-curve fitting to measure deflection of straight members
  * *Classification output:* type, confidence, severity (Low/Medium/High), measurements, and a condition
    rating (Good / Fair / Poor / Critical) with a maintenance recommendation
* **Backend Data Management Layer:** `backend/app/db.py`. SQLite tables `users`, `sessions`, `inspections`,
  `findings`, plus saved original and AR-annotated images in `backend/data/media/`.

### API (interactive docs at `/docs` while the server runs)
`POST /api/auth/login|register|logout`, `GET /api/auth/me`,
`POST /api/detect` (live), `POST /api/analyze` (captured frame),
`POST/GET /api/inspections`, `GET/PATCH/DELETE /api/inspections/{id}`,
`POST /api/inspections/{id}/findings`, `GET /api/inspections/{id}/report.pdf`, `GET /api/stats`

---

## 4. Upgrading to a deep-learning model (optional, from Table 3.2: YOLO)

The engine automatically switches to a YOLO model if these two files exist:

```
backend/models/damage.onnx    # YOLOv8 exported:  yolo export model=best.pt format=onnx opset=12
backend/models/classes.txt    # one class name per line, in training order
```

Class names such as `crack`, `rust`, `corrosion`, `spalling`, `pothole`, `exposed rebar`, and `deformation` are mapped
to the four system damage types automatically. A model can be trained for free in Google Colab on a public
crack/corrosion dataset (for example, from Roboflow Universe). No code changes are needed; OpenCV's DNN module loads it.
This path has not been tested with a real model yet. Test it before relying on it in a demo.

---

## 5. Project structure

```
ar-damage-assessment/
├── run.py                    # starts the server (HTTPS with self-signed certificate, or --http)
├── start_windows.bat / start_mac_linux.sh
├── backend/
│   ├── app/  main.py  detector.py  db.py  auth.py  reports.py
│   ├── models/               # optional YOLO ONNX model goes here
│   ├── tests/ test_system.py  make_samples.py  samples/
│   └── requirements.txt
├── frontend/  index.html  app.js  styles.css  manifest.json  icon.svg
└── docs/screenshots/         # UI screenshots for Chapter 4.5.1
```

## 6. Known limitations (for Chapter 4.6 / 5)

* The OpenCV engine uses classical computer vision, not a trained neural network. It works best on fairly plain
  concrete, steel or asphalt surfaces in good light. Strong shadows, joints, stains or brown and orange objects
  (bricks, paint) can cause false detections. The inspector can untick those before saving.
* Measurements are given in pixels or as a percentage of the camera view. Real-world units would need a reference
  scale or the phone's depth or AR measurement APIs.
* Overlays are drawn in screen space on the live camera feed (camera-based AR, Section 4.4.1). They are not anchored
  in 3-D world space, as an ARCore / Unity AR Foundation build would be.
* Live detection needs the phone to reach the laptop over the network. Latency is about 50–150 ms on local Wi-Fi.
