/* AR-Based Real-Time Infrastructure Damage Assessment System – mobile web client
 * Screens follow the wireframe in Figure 4.4:
 *   Welcome/Login -> Dashboard -> Start Inspection -> AR Camera (Capture / Analyze / Exit)
 *   -> Damage Detection Result -> Inspection Record -> Inspection History
 */
(() => {
  "use strict";

  const COLORS = { crack: "#eb3c3c", corrosion: "#ff8c00", deformation: "#aa50c8", surface_damage: "#e6c800" };
  const LABELS = { crack: "Crack", corrosion: "Corrosion", deformation: "Deformation", surface_damage: "Surface Damage" };
  const INFRA = ["Bridge", "Building", "Road", "Tunnel", "Railway", "Dam", "Utility Facility", "Other"];

  const ICON = {
    back: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 18l-6-6 6-6"/></svg>',
    logout: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5-5-5M21 12H9"/></svg>',
    scan: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7V5a2 2 0 0 1 2-2h2M17 3h2a2 2 0 0 1 2 2v2M21 17v2a2 2 0 0 1-2 2h-2M7 21H5a2 2 0 0 1-2-2v-2"/><path d="M7 14l3-4 2 2 3-5 2 7"/></svg>',
    history: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 3-6.7L3 8"/><path d="M3 3v5h5M12 7v5l3 3"/></svg>',
    capture: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg>',
    upload: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><path d="M21 15l-5-5L5 21"/></svg>',
    exit: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6L6 18M6 6l12 12"/></svg>',
    retake: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M1 4v6h6M23 20v-6h-6"/><path d="M20.5 9A9 9 0 0 0 5.6 5.6L1 10m22 4l-4.6 4.4A9 9 0 0 1 3.5 15"/></svg>',
    pdf: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M12 18v-6M9 15l3 3 3-3"/></svg>',
    pin: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13S3 17 3 10a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>',
    Bridge: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M2 17h20M4 17V9M20 17V9M2 9c4 0 6 4 10 4s6-4 10-4M8 17v-5M16 17v-5M12 17v-4"/></svg>',
    Building: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><rect x="5" y="3" width="14" height="18" rx="1"/><path d="M9 7h2M13 7h2M9 11h2M13 11h2M9 15h2M13 15h2M10 21v-3h4v3"/></svg>',
    Road: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M8 3L4 21M16 3l4 18M12 4v3M12 11v3M12 18v3"/></svg>',
    Tunnel: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M2 21h20M4 21V12a8 8 0 0 1 16 0v9M9 21v-6a3 3 0 0 1 6 0v6"/></svg>',
    Railway: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M8 3L5 21M16 3l3 18M6 7h12M5.5 12h13M5 17h14"/></svg>',
    Dam: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 6h6l3 14H3zM12 9c2 0 2 1.5 4.5 1.5S19 9 21 9M13 13c2 0 2 1.5 4 1.5s2.5-1.5 4-1.5M14 17c2 0 2 1.5 3.5 1.5S20 17 21 17"/></svg>',
    "Utility Facility": '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M13 2L4 14h7l-1 8 9-12h-7z"/></svg>',
    Other: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M8 12h.01M12 12h.01M16 12h.01"/></svg>',
  };

  const app = document.getElementById("app");
  const state = { user: null, meta: null, pending: null, cleanup: null };

  // ------------------------------------------------------------------ utils
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const $ = (sel, root = document) => root.querySelector(sel);
  const condClass = (c) => (!c ? "cond-none" : c.startsWith("Good (") ? "cond-Good-minor" : `cond-${c.split(" ")[0]}`);
  const fmtDate = (s) => {
    if (!s) return "";
    const d = new Date(s.replace(" ", "T") + "Z");
    return d.toLocaleString(undefined, { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
  };

  function toast(msg, ms = 2400) {
    const t = document.getElementById("toast");
    t.textContent = msg;
    t.classList.add("show");
    clearTimeout(toast._t);
    toast._t = setTimeout(() => t.classList.remove("show"), ms);
  }

  async function api(path, opts = {}) {
    const res = await fetch(path, { credentials: "same-origin", ...opts });
    if (res.status === 401 && !path.startsWith("/api/auth/login")) {
      state.user = null;
      location.hash = "#/login";
      throw new Error("Please log in");
    }
    const ct = res.headers.get("content-type") || "";
    const data = ct.includes("json") ? await res.json() : await res.text();
    if (!res.ok) {
      const detail = data && data.detail;
      throw new Error(Array.isArray(detail) ? detail.map((d) => d.msg).join(", ") : detail || `Request failed (${res.status})`);
    }
    return data;
  }
  const postJSON = (path, body, method = "POST") =>
    api(path, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

  function metricText(m = {}) {
    const parts = [];
    if (m.length_pct_of_view != null) parts.push(`length ≈ ${m.length_pct_of_view}% of view`);
    if (m.mean_width_px != null) parts.push(`width ≈ ${m.mean_width_px}px (max ${m.max_width_px}px)`);
    if (m.area_pct_of_view != null) parts.push(`area ${m.area_pct_of_view}% of view`);
    if (m.relative_depth != null) parts.push(`relative depth ${m.relative_depth}`);
    if (m.deflection_ratio != null) parts.push(`deflection ${(m.deflection_ratio * 100).toFixed(1)}% of span`);
    if (m.model_class) parts.push(`class: ${m.model_class}`);
    return parts.join(" · ");
  }

  // Draw AR overlay for normalised detections onto ctx; map(nx, ny) -> [x, y] in canvas pixels
  function drawDetections(ctx, dets, map, scale = 1, alpha = 1, numbered = true) {
    ctx.save();
    ctx.globalAlpha = alpha;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    dets.forEach((d, i) => {
      const col = COLORS[d.type] || "#ffffff";
      const pts = (d.polygon || []).map(([x, y]) => map(x, y));
      const open = d.metrics && d.metrics.open_path;
      if (pts.length >= 2) {
        ctx.beginPath();
        pts.forEach(([x, y], k) => (k ? ctx.lineTo(x, y) : ctx.moveTo(x, y)));
        if (!open && pts.length >= 3) {
          ctx.closePath();
          ctx.fillStyle = col + "40";
          ctx.fill();
        }
        ctx.strokeStyle = col;
        ctx.lineWidth = (open ? 5 : 3) * scale;
        ctx.shadowColor = col;
        ctx.shadowBlur = 8 * scale;
        ctx.stroke();
        ctx.shadowBlur = 0;
      }
      // corner brackets around the bounding box
      const [bx, by, bw, bh] = d.bbox;
      const [x0, y0] = map(bx, by);
      const [x1, y1] = map(bx + bw, by + bh);
      const c = Math.min(18 * scale, (x1 - x0) / 3, (y1 - y0) / 3);
      ctx.strokeStyle = col;
      ctx.lineWidth = 2.5 * scale;
      ctx.beginPath();
      [[x0, y0, 1, 1], [x1, y0, -1, 1], [x0, y1, 1, -1], [x1, y1, -1, -1]].forEach(([x, y, sx, sy]) => {
        ctx.moveTo(x + sx * c, y); ctx.lineTo(x, y); ctx.lineTo(x, y + sy * c);
      });
      ctx.stroke();
      // label tag
      const label = `${numbered ? i + 1 + ". " : ""}${d.label || LABELS[d.type] || d.type}  ${Math.round(d.confidence * 100)}%  ${d.severity}`;
      ctx.font = `600 ${13 * scale}px system-ui, sans-serif`;
      const tw = ctx.measureText(label).width + 14 * scale;
      const th = 22 * scale;
      let ty = y0 - th - 4 * scale;
      if (ty < 2) ty = y1 + 4 * scale;
      const tx = Math.max(2, Math.min(x0, ctx.canvas.width - tw - 2));
      ctx.fillStyle = col;
      roundRect(ctx, tx, ty, tw, th, 6 * scale);
      ctx.fill();
      ctx.fillStyle = d.type === "surface_damage" ? "#1a1500" : "#fff";
      ctx.fillText(label, tx + 7 * scale, ty + 15.5 * scale);
    });
    ctx.restore();
  }
  function roundRect(ctx, x, y, w, h, r) {
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.arcTo(x + w, y, x + w, y + h, r);
    ctx.arcTo(x + w, y + h, x, y + h, r);
    ctx.arcTo(x, y + h, x, y, r);
    ctx.arcTo(x, y, x + w, y, r);
    ctx.closePath();
  }

  // ------------------------------------------------------------------ router
  const routes = [
    [/^#\/login$/, viewLogin, false],
    [/^#\/register$/, viewRegister, false],
    [/^#\/dashboard$/, viewDashboard, true],
    [/^#\/start$/, viewStart, true],
    [/^#\/camera\/(\d+)$/, viewCamera, true],
    [/^#\/result\/(\d+)$/, viewResult, true],
    [/^#\/inspection\/(\d+)$/, viewInspection, true],
    [/^#\/history$/, viewHistory, true],
  ];

  async function router() {
    if (state.cleanup) { try { state.cleanup(); } catch (_) {} state.cleanup = null; }
    const hash = location.hash || "#/dashboard";
    if (!state.user) {
      try { state.user = await api("/api/auth/me"); } catch (_) { state.user = null; }
    }
    if (!state.meta) { try { state.meta = await api("/api/meta"); } catch (_) {} }
    for (const [re, view, needsAuth] of routes) {
      const m = hash.match(re);
      if (m) {
        if (needsAuth && !state.user) { location.hash = "#/login"; return; }
        if (!needsAuth && state.user) { location.hash = "#/dashboard"; return; }
        window.scrollTo(0, 0);
        try { await view(...m.slice(1)); } catch (e) { console.error(e); toast(e.message); }
        return;
      }
    }
    location.hash = state.user ? "#/dashboard" : "#/login";
  }
  window.addEventListener("hashchange", router);

  const topbar = (title, back = "#/dashboard", right = "") =>
    `<div class="topbar"><a class="icon-btn" href="${back}" aria-label="Back">${ICON.back}</a><h1>${esc(title)}</h1>${right}</div>`;

  // ------------------------------------------------------------------ login / register
  function viewLogin() {
    app.innerHTML = `<div class="page">
      <div class="brand"><img src="icon.svg" alt="" /><h1>AR-Based Real-Time Infrastructure<br/>Damage Assessment</h1>
      <p>Detect, visualise and record structural damage in the field</p></div>
      <form class="card" id="f">
        <h2>Inspector login</h2>
        <label for="u">Username</label><input id="u" autocomplete="username" autocapitalize="none" required />
        <label for="p">Password</label><input id="p" type="password" autocomplete="current-password" required />
        <div class="err" id="err"></div>
        <button class="btn btn-primary mt" type="submit">Login</button>
        <p class="center small muted mt">New inspector? <button type="button" class="link-btn" id="reg">Create an account</button></p>
        <p class="center small muted">Demo account: <b>inspector</b> / <b>inspect123</b></p>
      </form></div>`;
    $("#reg").onclick = () => (location.hash = "#/register");
    $("#f").onsubmit = async (e) => {
      e.preventDefault();
      $("#err").textContent = "";
      try {
        const r = await postJSON("/api/auth/login", { username: $("#u").value, password: $("#p").value });
        state.user = r.user;
        location.hash = "#/dashboard";
      } catch (err) { $("#err").textContent = err.message; }
    };
  }

  function viewRegister() {
    app.innerHTML = `<div class="page">${topbar("Create account", "#/login")}
      <form class="card" id="f">
        <label for="n">Full name</label><input id="n" required minlength="2" />
        <label for="r">Role</label>
        <select id="r"><option>Inspector</option><option>Engineer</option><option>Maintenance Officer</option><option>Supervisor</option></select>
        <label for="u">Username</label><input id="u" autocapitalize="none" required minlength="3" />
        <label for="p">Password (min. 6 characters)</label><input id="p" type="password" required minlength="6" autocomplete="new-password" />
        <div class="err" id="err"></div>
        <button class="btn btn-primary mt" type="submit">Create account</button>
      </form></div>`;
    $("#f").onsubmit = async (e) => {
      e.preventDefault();
      $("#err").textContent = "";
      try {
        const r = await postJSON("/api/auth/register", {
          full_name: $("#n").value, role: $("#r").value, username: $("#u").value, password: $("#p").value,
        });
        state.user = r.user;
        location.hash = "#/dashboard";
      } catch (err) { $("#err").textContent = err.message; }
    };
  }

  // ------------------------------------------------------------------ dashboard
  function inspectionItem(it) {
    const thumb = it.thumb_url ? `<img class="thumb" src="${esc(it.thumb_url)}" alt="" loading="lazy" />`
      : `<div class="thumb">${ICON[it.infrastructure_type] || ICON.Other}</div>`;
    return `<div class="list-item" data-id="${it.id}">${thumb}
      <div class="meta"><b>${esc(it.asset_name)}</b>
        <div class="sub">${esc(it.infrastructure_type)}${it.location ? " · " + esc(it.location) : ""}</div>
        <div class="sub">${fmtDate(it.created_at)} · ${it.capture_count} capture${it.capture_count === 1 ? "" : "s"} · ${it.defect_count} defect${it.defect_count === 1 ? "" : "s"}</div>
      </div>
      <div style="display:flex;flex-direction:column;gap:6px;align-items:flex-end">
        <span class="pill ${condClass(it.condition)}">${esc(it.condition || "No captures")}</span>
        <span class="pill status-pill">${esc(it.status)}</span></div></div>`;
  }
  function bindItems(root) {
    root.querySelectorAll(".list-item[data-id]").forEach((el) => (el.onclick = () => (location.hash = `#/inspection/${el.dataset.id}`)));
  }

  async function viewDashboard() {
    const [s, items] = await Promise.all([api("/api/stats"), api("/api/inspections")]);
    const max = Math.max(1, ...Object.values(s.by_type));
    const first = (state.user.full_name || "").split(" ")[0];
    app.innerHTML = `<div class="page">
      <div class="topbar" style="margin-bottom:6px"><div style="flex:1"></div>
        <button class="icon-btn" id="logout" aria-label="Log out">${ICON.logout}</button></div>
      <div class="hello"><h1>Hello, ${esc(first)}</h1><p>${esc(state.user.role)} · ${state.meta ? "Detection engine: " + esc(state.meta.engine.toUpperCase()) : ""}</p></div>
      <div class="big-actions">
        <button class="big-action primary" id="start">${ICON.scan}<b>Start Inspection</b><span>Live AR damage detection</span></button>
        <button class="big-action" id="hist">${ICON.history}<b>Inspection History</b><span>${s.inspections} saved inspection${s.inspections === 1 ? "" : "s"}</span></button>
      </div>
      <div class="stats">
        <div class="stat"><b>${s.inspections}</b><span>Inspections</span></div>
        <div class="stat"><b>${s.defects}</b><span>Defects found</span></div>
        <div class="stat"><b style="color:var(--high)">${s.high_severity}</b><span>High severity</span></div>
      </div>
      <div class="card"><h2>Defects by type</h2><div class="bars">
        ${Object.entries(LABELS).map(([k, l]) => `<div class="bar"><span>${l}</span>
          <div class="track"><div class="fill" style="width:${(s.by_type[k] / max) * 100}%;background:${COLORS[k]}"></div></div>
          <b>${s.by_type[k]}</b></div>`).join("")}
      </div></div>
      <div class="card"><h2>Recent inspections</h2><div id="recent">
        ${items.length ? items.slice(0, 3).map(inspectionItem).join("") : `<div class="empty">No inspections yet. Tap <b>Start Inspection</b> to begin.</div>`}
      </div></div></div>`;
    $("#start").onclick = () => (location.hash = "#/start");
    $("#hist").onclick = () => (location.hash = "#/history");
    $("#logout").onclick = async () => {
      try { await api("/api/auth/logout", { method: "POST" }); } catch (_) {}
      state.user = null;
      location.hash = "#/login";
    };
    bindItems($("#recent"));
  }

  // ------------------------------------------------------------------ start inspection
  function viewStart() {
    let type = "Bridge";
    let coords = null;
    app.innerHTML = `<div class="page">${topbar("Start Inspection")}
      <form class="card" id="f">
        <h2>Infrastructure type</h2>
        <div class="type-grid" id="types">${INFRA.map((t) => `<button type="button" class="chip ${t === type ? "on" : ""}" data-t="${t}">${ICON[t]}${t === "Utility Facility" ? "Utility" : t}</button>`).join("")}</div>
        <h2 style="margin-top:20px">Inspection details</h2>
        <label for="a">Asset name / ID *</label><input id="a" required placeholder="e.g. Kwame Nkrumah Interchange – Pier 3" />
        <label for="l">Location</label>
        <div class="inline"><input id="l" placeholder="e.g. Accra, Greater Accra" /><button type="button" class="btn btn-secondary" id="gps" title="Use GPS">${ICON.pin}</button></div>
        <div class="small muted" id="gpsinfo" style="margin-top:6px"></div>
        <label for="d">Description / scope</label><textarea id="d" placeholder="Element being inspected, reason for inspection, weather…"></textarea>
        <div class="err" id="err"></div>
        <button class="btn btn-primary mt" type="submit">${ICON.scan} Begin Inspection</button>
      </form></div>`;
    $("#types").onclick = (e) => {
      const b = e.target.closest(".chip");
      if (!b) return;
      type = b.dataset.t;
      $("#types").querySelectorAll(".chip").forEach((c) => c.classList.toggle("on", c === b));
    };
    $("#gps").onclick = () => {
      if (!navigator.geolocation) return ($("#gpsinfo").textContent = "GPS not available on this device.");
      $("#gpsinfo").textContent = "Getting location…";
      navigator.geolocation.getCurrentPosition(
        (p) => {
          coords = { latitude: p.coords.latitude, longitude: p.coords.longitude };
          $("#gpsinfo").textContent = `GPS: ${coords.latitude.toFixed(5)}, ${coords.longitude.toFixed(5)} (±${Math.round(p.coords.accuracy)} m)`;
          if (!$("#l").value) $("#l").value = `${coords.latitude.toFixed(5)}, ${coords.longitude.toFixed(5)}`;
        },
        (err) => ($("#gpsinfo").textContent = "Could not get location: " + err.message + (isSecureContext ? "" : " (GPS needs HTTPS)")),
        { enableHighAccuracy: true, timeout: 10000 }
      );
    };
    $("#f").onsubmit = async (e) => {
      e.preventDefault();
      try {
        const ins = await postJSON("/api/inspections", {
          infrastructure_type: type, asset_name: $("#a").value, location: $("#l").value || null,
          description: $("#d").value || null, ...(coords || {}),
        });
        location.hash = `#/camera/${ins.id}`;
      } catch (err) { $("#err").textContent = err.message; }
    };
  }

  // ------------------------------------------------------------------ AR camera / inspection view
  async function viewCamera(id) {
    const ins = await api(`/api/inspections/${id}`);
    app.innerHTML = `<div class="camera" id="cam">
      <video id="v" playsinline muted autoplay></video>
      <img class="still hidden" id="still" alt="" />
      <canvas class="overlay" id="ov"></canvas>
      <div class="reticle" id="ret"><i></i><i></i><i></i><i></i></div>
      <div class="cam-top">
        <a class="icon-btn" href="#/inspection/${id}" aria-label="Back" style="background:#0009;border-color:#fff3">${ICON.back}</a>
        <div class="title"><b>${esc(ins.asset_name)}</b><span>${esc(ins.infrastructure_type)} · ${ins.findings.length} saved capture${ins.findings.length === 1 ? "" : "s"}</span></div>
        <button class="toggle on" id="live"><span class="dot"></span>LIVE AR</button>
      </div>
      <div class="hud" id="hud"><span id="h-status">Starting camera…</span></div>
      <div class="legend">${Object.entries(LABELS).map(([k, l]) => `<span><i style="background:${COLORS[k]}"></i>${l}</span>`).join("")}</div>
      <div class="cam-bottom">
        <button class="cam-btn" id="b-left">${ICON.upload}<span>Upload</span></button>
        <button class="shutter" id="b-main" aria-label="Capture">CAPTURE</button>
        <button class="cam-btn" id="b-exit">${ICON.exit}<span>Exit</span></button>
      </div>
      <input type="file" accept="image/*" id="file" class="hidden" />
      <div class="scanning hidden" id="scan"><div><span class="spinner"></span><b>Analyzing infrastructure…</b></div></div>
    </div>`;

    const video = $("#v"), still = $("#still"), ov = $("#ov"), ctx = ov.getContext("2d");
    let stream = null, live = true, busy = false, frozen = null, liveDets = [], lastAt = 0, alive = true;
    let frames = 0, fpsT = performance.now(), fps = 0, latency = 0;
    const grab = document.createElement("canvas");

    function sizeCanvas() {
      const dpr = window.devicePixelRatio || 1;
      ov.width = ov.clientWidth * dpr;
      ov.height = ov.clientHeight * dpr;
    }
    sizeCanvas();
    window.addEventListener("resize", sizeCanvas);

    // map normalised image coords to screen, honouring object-fit: cover
    function coverMap(srcW, srcH) {
      const W = ov.width, H = ov.height;
      const s = Math.max(W / srcW, H / srcH);
      const ox = (W - srcW * s) / 2, oy = (H - srcH * s) / 2;
      return (x, y) => [x * srcW * s + ox, y * srcH * s + oy];
    }

    function setHud() {
      if (frozen) {
        $("#hud").innerHTML = `<span>Frame captured – tap ANALYZE</span>`;
        return;
      }
      const counts = {};
      liveDets.forEach((d) => (counts[d.type] = (counts[d.type] || 0) + 1));
      $("#hud").innerHTML = live
        ? `<span>${fps.toFixed(1)} FPS</span><span>${Math.round(latency)} ms</span><span>${liveDets.length ? liveDets.length + " defect" + (liveDets.length > 1 ? "s" : "") + " in view" : "Scanning… no damage in view"}</span>` +
          Object.entries(counts).map(([k, n]) => `<span style="color:${COLORS[k]}">${n}× ${LABELS[k] || k}</span>`).join("")
        : `<span>Live detection paused</span>`;
    }

    function render() {
      if (!alive) return;
      ctx.clearRect(0, 0, ov.width, ov.height);
      if (!frozen && live && liveDets.length && video.videoWidth) {
        const age = performance.now() - lastAt;
        const alpha = Math.max(0, 1 - Math.max(0, age - 900) / 900);
        if (alpha > 0) drawDetections(ctx, liveDets, coverMap(video.videoWidth, video.videoHeight), window.devicePixelRatio || 1, alpha);
      }
      requestAnimationFrame(render);
    }

    async function liveLoop() {
      while (alive) {
        if (live && !frozen && !busy && video.readyState >= 2 && video.videoWidth) {
          busy = true;
          const w = 640, h = Math.round((video.videoHeight / video.videoWidth) * w);
          grab.width = w; grab.height = h;
          grab.getContext("2d").drawImage(video, 0, 0, w, h);
          const blob = await new Promise((r) => grab.toBlob(r, "image/jpeg", 0.72));
          const t0 = performance.now();
          try {
            const fd = new FormData();
            fd.append("image", blob, "frame.jpg");
            fd.append("fast", "true");
            const r = await api("/api/detect", { method: "POST", body: fd });
            latency = performance.now() - t0;
            liveDets = r.detections;
            lastAt = performance.now();
            frames++;
            const now = performance.now();
            if (now - fpsT > 1000) { fps = (frames * 1000) / (now - fpsT); frames = 0; fpsT = now; }
            setHud();
          } catch (e) { $("#hud").innerHTML = `<span>Connection problem: ${esc(e.message)}</span>`; }
          busy = false;
        }
        await new Promise((r) => setTimeout(r, 60));
      }
    }

    function setMode() {
      const main = $("#b-main"), left = $("#b-left");
      if (frozen) {
        main.textContent = "ANALYZE"; main.classList.add("analyze");
        left.innerHTML = `${ICON.retake}<span>Retake</span>`;
        still.src = frozen.url; still.classList.remove("hidden");
        $("#ret").classList.add("hidden");
      } else {
        main.textContent = "CAPTURE"; main.classList.remove("analyze");
        left.innerHTML = `${ICON.upload}<span>Upload</span>`;
        still.classList.add("hidden");
        $("#ret").classList.toggle("hidden", !stream);
      }
      setHud();
    }

    async function freezeBlob(blob) {
      if (frozen) URL.revokeObjectURL(frozen.url);
      frozen = { blob, url: URL.createObjectURL(blob) };
      setMode();
    }

    async function capture() {
      if (!stream || !video.videoWidth) return $("#file").click();
      const c = document.createElement("canvas");
      c.width = video.videoWidth; c.height = video.videoHeight;
      c.getContext("2d").drawImage(video, 0, 0);
      const blob = await new Promise((r) => c.toBlob(r, "image/jpeg", 0.92));
      freezeBlob(blob);
    }

    async function analyze() {
      $("#scan").classList.remove("hidden");
      try {
        const fd = new FormData();
        fd.append("image", frozen.blob, "capture.jpg");
        const result = await api("/api/analyze", { method: "POST", body: fd });
        state.pending = { inspectionId: Number(id), blob: frozen.blob, url: frozen.url, result };
        frozen = null; // keep the object URL alive for the result screen
        location.hash = `#/result/${id}`;
      } catch (e) {
        toast(e.message);
      } finally {
        const s = $("#scan"); if (s) s.classList.add("hidden");
      }
    }

    $("#b-main").onclick = () => (frozen ? analyze() : capture());
    $("#b-left").onclick = () => {
      if (frozen) { URL.revokeObjectURL(frozen.url); frozen = null; setMode(); }
      else $("#file").click();
    };
    $("#b-exit").onclick = () => (location.hash = `#/inspection/${id}`);
    $("#file").onchange = (e) => { const f = e.target.files[0]; if (f) freezeBlob(f); e.target.value = ""; };
    $("#live").onclick = () => {
      live = !live;
      $("#live").classList.toggle("on", live);
      liveDets = [];
      setHud();
    };

    state.cleanup = () => {
      alive = false;
      window.removeEventListener("resize", sizeCanvas);
      if (stream) stream.getTracks().forEach((t) => t.stop());
    };

    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) throw new Error(isSecureContext ? "Camera API not supported" : "insecure");
      stream = await navigator.mediaDevices.getUserMedia({
        audio: false, video: { facingMode: { ideal: "environment" }, width: { ideal: 1920 }, height: { ideal: 1080 } },
      });
      if (!alive) { stream.getTracks().forEach((t) => t.stop()); return; }
      video.srcObject = stream;
      await video.play().catch(() => {});
      setMode();
      liveLoop();
    } catch (e) {
      live = false;
      $("#live").classList.add("hidden");
      $("#ret").classList.add("hidden");
      const why = e.message === "insecure"
        ? "The live camera needs a secure (HTTPS) connection. Start the server with HTTPS (see README), or use <b>Upload</b> to take a photo with your camera app."
        : `Camera unavailable (${esc(e.message || e.name)}). Use <b>Upload</b> to take or choose a photo instead.`;
      $("#hud").innerHTML = "";
      const msg = document.createElement("div");
      msg.className = "cam-msg";
      msg.innerHTML = `<div class="card"><h2>Live camera</h2><p class="small">${why}</p>
        <button class="btn btn-primary mt" id="pick">${ICON.capture} Take / choose photo</button></div>`;
      $("#cam").insertBefore(msg, $(".cam-top"));
      $("#pick").onclick = () => $("#file").click();
      const obs = new MutationObserver(() => msg.classList.toggle("hidden", !!frozen));
      obs.observe(still, { attributes: true, attributeFilter: ["class"] });
    }
    render();
  }

  // ------------------------------------------------------------------ damage detection result
  function viewResult(id) {
    const p = state.pending;
    if (!p || p.inspectionId !== Number(id)) { location.hash = `#/camera/${id}`; return; }
    const dets = p.result.detections.map((d) => ({ ...d, keep: true }));
    app.innerHTML = `<div class="page">${topbar("Damage Detection Result", `#/camera/${id}`)}
      <div class="result-img"><img id="img" src="${p.url}" alt="Captured infrastructure" /><canvas id="cv"></canvas></div>
      <div class="card mt" id="condCard"></div>
      <div class="card"><h2>Detected damage <span class="muted" style="text-transform:none;letter-spacing:0">– untick false detections</span></h2><div id="dets"></div></div>
      <div class="card"><h2>Inspection notes</h2>
        <textarea id="notes" placeholder="Element, location on structure, measurements, observations…"></textarea>
        <button class="btn btn-primary mt" id="save">Save Assessment</button>
        <div class="btn-row"><button class="btn btn-secondary" id="retake">${ICON.retake} Retake</button>
        <a class="btn btn-secondary" href="#/inspection/${id}">Record</a></div>
      </div>
      <p class="small muted center">Engine: ${esc(p.result.engine)} · processed in ${Math.round(p.result.processing_ms)} ms</p></div>`;

    const img = $("#img"), cv = $("#cv");
    function draw() {
      if (!img.naturalWidth) return;
      const dpr = window.devicePixelRatio || 1;
      cv.width = img.clientWidth * dpr; cv.height = img.clientHeight * dpr;
      const c = cv.getContext("2d");
      c.clearRect(0, 0, cv.width, cv.height);
      const kept = dets.filter((d) => d.keep);
      drawDetections(c, kept, (x, y) => [x * cv.width, y * cv.height], dpr * Math.max(0.7, Math.min(1.2, img.clientWidth / 520)));
    }
    function condition(list) {
      if (!list.length) return "Good";
      const rank = { Low: 1, Medium: 2, High: 3 };
      const worst = Math.max(...list.map((d) => rank[d.severity] || 1));
      const highs = list.filter((d) => d.severity === "High").length;
      if (worst === 3) return highs >= 2 ? "Critical" : "Poor";
      if (worst === 2) return "Fair";
      return list.length >= 4 ? "Fair" : "Good (minor defects)";
    }
    const recs = {
      "Good": "No visible defects detected. Continue routine inspection schedule.",
      "Good (minor defects)": "Minor defects present. Monitor at next scheduled inspection.",
      "Fair": "Defects require monitoring. Schedule maintenance and re-inspect within 6 months.",
      "Poor": "Significant damage detected. Refer to a structural engineer and plan repairs promptly.",
      "Critical": "Severe damage detected. Restrict use if necessary and arrange urgent engineering assessment.",
    };
    function renderList() {
      const kept = dets.filter((d) => d.keep);
      const cond = condition(kept);
      $("#condCard").innerHTML = `<h2>Assessment</h2><div class="cond-card"><span class="big">${kept.length}</span>
        <span class="muted" style="flex:1">defect${kept.length === 1 ? "" : "s"} detected</span>
        <span class="pill ${condClass(cond)}" style="font-size:.85rem">${esc(cond)}</span></div>
        <p class="small muted" style="margin:10px 0 0">${esc(recs[cond])}</p>`;
      let n = 0;
      $("#dets").innerHTML = dets.length ? dets.map((d, i) => {
        if (d.keep) n++;
        return `<div class="det ${d.keep ? "" : "removed"}">
          <span class="swatch" style="background:${COLORS[d.type] || "#fff"}"></span>
          <div class="body"><div class="row1"><b>${d.keep ? n + ". " : ""}${esc(d.label || LABELS[d.type] || d.type)}</b>
            <span class="pill sev-${esc(d.severity)}">${esc(d.severity)}</span>
            <span class="small muted">${Math.round(d.confidence * 100)}% confidence</span></div>
            <div class="metrics">${esc(metricText(d.metrics))}</div></div>
          <label class="keep"><input type="checkbox" data-i="${i}" ${d.keep ? "checked" : ""}/>Keep</label></div>`;
      }).join("") : `<div class="empty">No visible damage detected in this frame.</div>`;
      $("#dets").querySelectorAll("input[type=checkbox]").forEach((cb) => (cb.onchange = () => {
        dets[cb.dataset.i].keep = cb.checked; renderList(); draw();
      }));
    }
    img.onload = draw;
    window.addEventListener("resize", draw);
    state.cleanup = () => window.removeEventListener("resize", draw);
    renderList();
    if (img.complete) draw();

    $("#retake").onclick = () => { URL.revokeObjectURL(p.url); state.pending = null; location.hash = `#/camera/${id}`; };
    $("#save").onclick = async () => {
      const btn = $("#save");
      btn.disabled = true; btn.textContent = "Saving…";
      try {
        const fd = new FormData();
        fd.append("image", p.blob, "capture.jpg");
        fd.append("notes", $("#notes").value);
        fd.append("processing_ms", String(p.result.processing_ms));
        fd.append("detections", JSON.stringify(dets.filter((d) => d.keep).map(({ keep, ...d }) => d)));
        await api(`/api/inspections/${id}/findings`, { method: "POST", body: fd });
        URL.revokeObjectURL(p.url);
        state.pending = null;
        toast("Assessment saved to inspection record");
        location.hash = `#/camera/${id}`;
      } catch (e) {
        toast(e.message);
        btn.disabled = false; btn.textContent = "Save Assessment";
      }
    };
  }

  // ------------------------------------------------------------------ inspection record
  async function viewInspection(id) {
    const ins = await api(`/api/inspections/${id}`);
    const all = ins.findings.flatMap((f) => f.detections);
    const counts = Object.keys(LABELS).map((k) => [k, all.filter((d) => d.type === k).length]).filter(([, n]) => n);
    const done = ins.status === "Completed";
    app.innerHTML = `<div class="page">${topbar("Inspection Record", "#/history")}
      <div class="card">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:10px">
          <div><div class="small muted">INS-${String(ins.id).padStart(5, "0")}</div><h2 style="font-size:1.15rem;text-transform:none;letter-spacing:0;color:var(--text);margin:4px 0 0">${esc(ins.asset_name)}</h2></div>
          <span class="pill ${condClass(ins.condition)}" style="font-size:.85rem">${esc(ins.condition || "No captures")}</span></div>
        ${ins.recommendation ? `<p class="small muted">${esc(ins.recommendation)}</p>` : ""}
        <dl class="kv mt">
          <dt>Type</dt><dd>${esc(ins.infrastructure_type)}</dd>
          <dt>Location</dt><dd>${esc(ins.location || "–")}</dd>
          ${ins.latitude != null ? `<dt>GPS</dt><dd>${ins.latitude.toFixed(5)}, ${ins.longitude.toFixed(5)}</dd>` : ""}
          <dt>Started</dt><dd>${fmtDate(ins.created_at)}</dd>
          <dt>Status</dt><dd>${esc(ins.status)}${ins.completed_at ? " · " + fmtDate(ins.completed_at) : ""}</dd>
          <dt>Damage found</dt><dd>${counts.length ? counts.map(([k, n]) => `<span style="color:${COLORS[k]}">${n}× ${LABELS[k]}</span>`).join(", ") : "None recorded"}</dd>
          ${ins.description ? `<dt>Scope</dt><dd>${esc(ins.description)}</dd>` : ""}
        </dl>
      </div>
      <div class="btn-row">
        ${done ? `<button class="btn btn-secondary" id="reopen">Reopen</button>` : `<a class="btn btn-primary" href="#/camera/${id}">${ICON.scan} Continue</a>`}
        <a class="btn btn-secondary" href="/api/inspections/${id}/report.pdf" target="_blank" rel="noopener">${ICON.pdf} Report</a>
      </div>
      <div class="card mt"><h2>Overall inspection notes</h2>
        <textarea id="notes" placeholder="Summary, recommended actions…">${esc(ins.notes || "")}</textarea>
        <div class="btn-row"><button class="btn btn-secondary" id="saveNotes">Save notes</button>
        ${done ? `<button class="btn btn-secondary" disabled>Completed</button>` : `<button class="btn btn-primary" id="complete">Complete</button>`}</div>
      </div>
      <div class="card"><h2>Captures (${ins.findings.length})</h2>
        ${ins.findings.length ? ins.findings.map((f, i) => `<div class="capture">
          <img src="${esc(f.annotated_url)}" alt="Capture ${i + 1}" loading="lazy" />
          <div class="cap-head"><b>Capture ${i + 1}</b><span class="pill ${condClass(f.condition)}">${esc(f.condition)}</span></div>
          <div class="small muted">${fmtDate(f.created_at)} · ${f.detections.length ? f.detections.map((d) => `${esc(d.label)} (${esc(d.severity)})`).join(", ") : "no damage"}</div>
          ${f.notes ? `<div class="small" style="margin-top:4px">${esc(f.notes)}</div>` : ""}
          <button class="link-btn small" style="color:var(--high);margin-top:6px" data-del="${f.id}">Delete capture</button></div>`).join("")
          : `<div class="empty">No captures yet. Tap <b>Continue</b> to open the AR camera.</div>`}
      </div>
      <button class="btn btn-danger mt" id="delete">Delete inspection</button></div>`;

    const saveNotes = () => postJSON(`/api/inspections/${id}`, { notes: $("#notes").value }, "PATCH");
    $("#saveNotes").onclick = async () => { await saveNotes(); toast("Notes saved"); };
    if ($("#complete")) $("#complete").onclick = async () => {
      await postJSON(`/api/inspections/${id}`, { notes: $("#notes").value, status: "Completed" }, "PATCH");
      toast("Inspection completed");
      viewInspection(id);
    };
    if ($("#reopen")) $("#reopen").onclick = async () => {
      await postJSON(`/api/inspections/${id}`, { status: "In Progress" }, "PATCH");
      viewInspection(id);
    };
    app.querySelectorAll("[data-del]").forEach((b) => (b.onclick = async () => {
      if (!confirm("Delete this capture?")) return;
      await api(`/api/inspections/${id}/findings/${b.dataset.del}`, { method: "DELETE" });
      viewInspection(id);
    }));
    $("#delete").onclick = async () => {
      if (!confirm("Delete this inspection and all its captures?")) return;
      await api(`/api/inspections/${id}`, { method: "DELETE" });
      toast("Inspection deleted");
      location.hash = "#/history";
    };
  }

  // ------------------------------------------------------------------ history
  async function viewHistory() {
    let filter = "", q = "";
    app.innerHTML = `<div class="page">${topbar("Inspection History")}
      <input id="q" type="search" placeholder="Search asset or location…" />
      <div class="chips mt" id="chips"><button class="chip on" data-t="">All</button>${INFRA.map((t) => `<button class="chip" data-t="${t}">${t}</button>`).join("")}</div>
      <div id="list" class="mt"></div></div>`;
    async function load() {
      const params = new URLSearchParams();
      if (q) params.set("q", q);
      if (filter) params.set("infrastructure_type", filter);
      const items = await api(`/api/inspections?${params}`);
      $("#list").innerHTML = items.length ? items.map(inspectionItem).join("") : `<div class="empty">No inspections found.</div>`;
      bindItems($("#list"));
    }
    let t;
    $("#q").oninput = (e) => { clearTimeout(t); t = setTimeout(() => { q = e.target.value.trim(); load(); }, 250); };
    $("#chips").onclick = (e) => {
      const b = e.target.closest(".chip");
      if (!b) return;
      filter = b.dataset.t;
      $("#chips").querySelectorAll(".chip").forEach((c) => c.classList.toggle("on", c === b));
      load();
    };
    await load();
  }

  router();
})();
