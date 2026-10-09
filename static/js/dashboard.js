/**
 * HoneyTrap Dashboard — Client-side JavaScript
 * Handles Socket.IO events, Leaflet map, live feed, table filtering, and exports.
 */

// ─────────────────────────────────────────────
//  Socket.IO Connection
// ─────────────────────────────────────────────
const socket = io({ transports: ["websocket", "polling"] });

let paused = false;
let currentFilter = "all";
let allEvents = [];
let mapMarkers = [];

// ─────────────────────────────────────────────
//  Leaflet Map Setup
// ─────────────────────────────────────────────
const map = L.map("map", {
  center: [20, 0],
  zoom: 2,
  zoomControl: true,
  attributionControl: false,
  minZoom: 1,
  maxZoom: 12,
});

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19,
}).addTo(map);

// Custom marker colours per service
const serviceColors = {
  SSH:    "#00f5ff",
  FTP:    "#a855f7",
  Telnet: "#f59e0b",
  HTTP:   "#22c55e",
};

function createMarkerIcon(service) {
  const color = serviceColors[service] || "#ffffff";
  return L.divIcon({
    className: "",
    html: `<div style="
      width:12px;height:12px;border-radius:50%;
      background:${color};
      box-shadow:0 0 10px ${color}, 0 0 20px ${color}60;
      border:2px solid rgba(255,255,255,0.3);
      animation:markerPop 0.4s cubic-bezier(0.16,1,0.3,1);
    "></div>`,
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });
}

// Inject marker animation keyframes
const style = document.createElement("style");
style.textContent = `
  @keyframes markerPop {
    from { transform: scale(0); opacity: 0; }
    to   { transform: scale(1); opacity: 1; }
  }
`;
document.head.appendChild(style);

let uniqueOrigins = new Set();

function addMapMarker(event) {
  const lat = parseFloat(event.geo && event.geo.lat);
  const lon = parseFloat(event.geo && event.geo.lon);
  // Only skip true localhost/private with no coordinates
  const isLocalhost = (event.ip === "127.0.0.1" || event.ip === "::1");
  if (isLocalhost && !lat && !lon) return;
  const key = event.ip;
  if (uniqueOrigins.has(key)) return;
  uniqueOrigins.add(key);

  const marker = L.marker([lat || 0.1, lon || 0.1], { icon: createMarkerIcon(event.service) })
    .addTo(map)
    .bindPopup(`
      <div style="font-family:JetBrains Mono,monospace;font-size:0.72rem;line-height:1.6;color:#e2e8f0">
        <b style="color:${serviceColors[event.service]}">${event.service}</b><br/>
        IP: ${escHtml(event.ip)}<br/>
        ${event.geo.city}, ${event.geo.country}<br/>
        ${event.geo.org}
      </div>
    `, { className: "custom-popup" });

  mapMarkers.push(marker);
  document.getElementById("map-count").textContent = `${uniqueOrigins.size} origin${uniqueOrigins.size !== 1 ? "s" : ""}`;
}

// ─────────────────────────────────────────────
//  Live Feed
// ─────────────────────────────────────────────
const feedEl = document.getElementById("feed");

function fmtTime(iso) {
  const d = new Date(iso);
  return d.toLocaleTimeString("en-US", { hour12: false });
}

function addFeedItem(event) {
  if (paused) return;

  const item = document.createElement("div");
  item.className = "feed-item";
  const cred = event.username
    ? `<span style="color:#f59e0b">${escHtml(event.username)}</span>:<span style="color:#ef4444">${escHtml(event.password)}</span>`
    : escHtml(event.payload || "").substring(0, 60);

  const sevCls   = (event.severity || "medium").toLowerCase();
  const sevLabel = event.severity || "MEDIUM";
  const tactic   = event.tactic   ? ` · <span class="feed-tactic">${escHtml(event.tactic)}</span>` : "";
  const campaign = event.campaign ? ` · <span class="feed-campaign">${escHtml(event.campaign)}</span>` : "";

  item.innerHTML = `
    <div class="feed-dot ${event.service}"></div>
    <div class="feed-content">
      <div class="feed-primary">
        <span style="color:${serviceColors[event.service] || '#fff'}">${event.service}</span>
        &nbsp;·&nbsp;
        <span style="color:#00f5ff">${escHtml(event.ip)}</span>
        ${event.geo.city !== "Unknown" ? `· ${escHtml(event.geo.city)}, ${escHtml(event.geo.country)}` : ""}
        <span class="feed-sev sev-${sevCls}">${sevLabel}</span>
        ${tactic}${campaign}
      </div>
      <div class="feed-secondary">${cred}</div>
    </div>
    <div class="feed-time">${fmtTime(event.timestamp)}</div>
  `;

  feedEl.prepend(item);
  while (feedEl.children.length > 60) feedEl.removeChild(feedEl.lastChild);
}

// ─────────────────────────────────────────────
//  Attack Log Table
// ─────────────────────────────────────────────
const tbody = document.getElementById("log-tbody");
const emptyState = document.getElementById("empty-state");

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function renderTable() {
  const filtered = currentFilter === "all"
    ? allEvents
    : allEvents.filter(e => e.service === currentFilter);

  if (filtered.length === 0) {
    tbody.innerHTML = "";
    emptyState.classList.add("visible");
    return;
  }
  emptyState.classList.remove("visible");

  const rows = filtered.slice().reverse().map(e => {
    const badge    = `<span class="badge badge-${e.service.toLowerCase()}">${escHtml(e.service)}</span>`;
    const sevCls   = (e.severity || "MEDIUM").toLowerCase();
    const sevBadge = `<span class="badge-sev sev-${sevCls}">${escHtml(e.severity || "MEDIUM")}</span>`;
    const loc      = e.geo.city !== "Unknown" ? `${escHtml(e.geo.city)}, ${escHtml(e.geo.country)}` : escHtml(e.geo.country);
    const payload  = (e.payload || e.extra || "").substring(0, 55);
    const campaign = e.campaign ? `<span class="campaign-tag">${escHtml(e.campaign)}</span>` : "";
    const tactic   = e.tactic   ? `<span class="tactic-tag">${escHtml(e.tactic)}</span>` : "";
    const tech     = e.technique ? `<span class="technique-tag" title="${escHtml(e.technique)}">${escHtml(e.technique)}</span>` : "";
    return `<tr data-service="${escHtml(e.service)}" data-severity="${sevCls}">
      <td>${e.id}</td>
      <td class="mono">${new Date(e.timestamp).toLocaleString("en-US",{hour12:false})}</td>
      <td>${badge} ${sevBadge}</td>
      <td class="ip-cell">${escHtml(e.ip)}</td>
      <td>${loc}</td>
      <td class="user-cell">${escHtml(e.username || "—")}</td>
      <td class="pass-cell">${escHtml(e.password || "—")}</td>
      <td class="mono" title="${escHtml(e.payload || e.extra || "")}">${escHtml(payload) || "—"}</td>
      <td>${tactic}</td>
      <td>${tech}</td>
      <td>${campaign}</td>
    </tr>`;
  });
  tbody.innerHTML = rows.join("");
}

// ─────────────────────────────────────────────
//  Stats
// ─────────────────────────────────────────────
function updateStats(stats) {
  animateCount("stat-total",  stats.total  || 0);
  animateCount("stat-ssh",    stats.ssh    || 0);
  animateCount("stat-ftp",    stats.ftp    || 0);
  animateCount("stat-telnet", stats.telnet || 0);
  animateCount("stat-http",   stats.http   || 0);
}

function animateCount(id, target) {
  const el = document.getElementById(id);
  const start = parseInt(el.textContent) || 0;
  if (start === target) return;
  const diff = target - start;
  const steps = 20;
  let step = 0;
  const timer = setInterval(() => {
    step++;
    el.textContent = Math.round(start + (diff * step / steps));
    if (step >= steps) { el.textContent = target; clearInterval(timer); }
  }, 20);
}

// ─────────────────────────────────────────────
//  Socket Events
// ─────────────────────────────────────────────
socket.on("connect", () => {
  console.log("Connected to HoneyTrap");
  document.getElementById("status-text").textContent = "LIVE MONITORING";
  showToast("Connected to HoneyTrap server");
});

socket.on("disconnect", () => {
  console.warn("❌ Disconnected");
  document.getElementById("status-text").textContent = "DISCONNECTED";
  document.querySelector(".pulse-ring").style.background = "#ef4444";
  showToast("⚠️ Connection lost – retrying…");
});

socket.on("reconnect", () => {
  document.getElementById("status-text").textContent = "LIVE MONITORING";
  document.querySelector(".pulse-ring").style.background = "";
  showToast("✅ Reconnected!");
});

socket.on("new_event", (event) => {
  allEvents.push(event);
  addFeedItem(event);
  addMapMarker(event);
  renderTable();
});

socket.on("stats_update", (stats) => {
  updateStats(stats);
});

// ─────────────────────────────────────────────
//  Initial Load (Fetch Existing Events)
// ─────────────────────────────────────────────
let _initialLoaded = false;

async function loadInitialData() {
  if (_initialLoaded) return;
  _initialLoaded = true;
  try {
    const [evRes, stRes] = await Promise.all([
      fetch("/api/events"),
      fetch("/api/stats"),
    ]);
    if (!evRes.ok || !stRes.ok) throw new Error("API returned error");
    const events = await evRes.json();
    const stats  = await stRes.json();

    // Store oldest-first internally
    allEvents = events.slice().reverse();

    // Populate feed with last 60 events (newest first), bypass pause
    const feedSlice = allEvents.slice(-60).reverse();
    feedSlice.forEach(e => addFeedItem(e, true));

    // Add map markers for all events
    allEvents.forEach(e => addMapMarker(e));

    updateStats(stats);
    renderTable();

    showToast(`Loaded ${allEvents.length} attack events`);
    if (allEvents.length === 0) emptyState.classList.add("visible");
  } catch (err) {
    console.error("Failed to load initial data:", err);
    showToast("Failed to load events - check server connection");
    _initialLoaded = false; // allow retry
  }
}

loadInitialData();

// ─────────────────────────────────────────────
//  Filter Buttons
// ─────────────────────────────────────────────
document.querySelectorAll(".filter-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".filter-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");
    currentFilter = btn.dataset.filter;
    renderTable();
  });
});

// ─────────────────────────────────────────────
//  Pause Toggle
// ─────────────────────────────────────────────
document.getElementById("toggle-pause").addEventListener("change", (e) => {
  paused = e.target.checked;
});

// ─────────────────────────────────────────────
//  Clear Logs
// ─────────────────────────────────────────────
document.getElementById("btn-clear").addEventListener("click", async () => {
  if (!confirm("Clear all attack logs?")) return;
  await fetch("/api/clear", { method: "POST" });
  allEvents = [];
  _initialLoaded = false;
  uniqueOrigins.clear();
  mapMarkers.forEach(m => map.removeLayer(m));
  mapMarkers = [];
  feedEl.innerHTML = "";
  renderTable();
  document.getElementById("map-count").textContent = "0 origins";
  showToast("Logs cleared");
});

// ─────────────────────────────────────────────
//  Export JSON
// ─────────────────────────────────────────────
document.getElementById("btn-export").addEventListener("click", () => {
  const blob = new Blob([JSON.stringify(allEvents, null, 2)], { type: "application/json" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href     = url;
  a.download = `honeypot_export_${new Date().toISOString().slice(0,19).replace(/[:T]/g,"-")}.json`;
  a.click();
  URL.revokeObjectURL(url);
  showToast("⬇ Exported attack log");
});

// ─────────────────────────────────────────────
//  Toast Helper
// ─────────────────────────────────────────────
let toastTimer;
function showToast(msg) {
  const toast = document.getElementById("toast");
  toast.textContent = msg;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 3500);
}
