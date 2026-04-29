/**
 * Forge3D – Shared App Shell (sidebar + topbar)
 * Included by every authenticated page.
 */

const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
const API_BASE = window.FORGE3D_API_BASE || (isLocal ? "http://localhost:5000/api" : "/api");

// ── Auth guard ────────────────────────────────────────────────────────────────
export function requireAuth() {
  if (!localStorage.getItem("forge3d_token")) {
    // window.location.href = "login.html";
    return { email: "guest@studio.com" }; // Return mock user to prevent redirect
  }
  try {
    return JSON.parse(localStorage.getItem("forge3d_user") || "null");
  } catch { return null; }
}

export function logout() {
  localStorage.removeItem("forge3d_token");
  localStorage.removeItem("forge3d_user");
  window.location.href = "login.html";
}

// ── Sidebar nav items ─────────────────────────────────────────────────────────
const NAV_ITEMS = [
  { href: "dashboard.html",  icon: "dashboard",    label: "Dashboard"    },
  { href: "assets.html",     icon: "inventory_2",  label: "Asset Library"},
  { href: "projects.html",   icon: "folder_copy",  label: "Projects"     },
  { href: "activity.html",   icon: "history",      label: "Activity"     },
  { href: "settings.html",   icon: "settings",     label: "Settings"     },
];

// ── Render sidebar ────────────────────────────────────────────────────────────
export function renderSidebar(activeHref) {
  const user = requireAuth();
  if (!user) return;

  const navHtml = NAV_ITEMS.map(({ href, icon, label }) => {
    const isActive = location.pathname.endsWith(href) || location.href.endsWith(href);
    const active = isActive
      ? "bg-zinc-800 text-blue-500 border-r-2 border-blue-500"
      : "text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50";
    return `
      <a class="flex items-center gap-3 px-3 py-2 ${active} font-inter text-sm font-medium tracking-tight transition-colors duration-150" href="${href}">
        <span class="material-symbols-outlined">${icon}</span>
        <span>${label}</span>
      </a>`;
  }).join("");

  document.getElementById("sidebar").innerHTML = `
    <div class="p-6 flex items-center gap-3">
      <span class="material-symbols-outlined text-blue-500">deployed_code</span>
      <span class="font-inter text-lg font-bold tracking-widest uppercase text-zinc-100">Forge3D</span>
    </div>
    <nav class="flex-1 flex flex-col px-3 space-y-1">${navHtml}</nav>
    <div class="p-4 border-t border-zinc-800">
      <div class="flex items-center gap-3 px-2 py-2">
        <div class="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center border border-zinc-700">
          <span class="material-symbols-outlined text-xs">person</span>
        </div>
        <div class="flex flex-col flex-1 min-w-0">
          <span class="font-label-md text-on-surface truncate">${user.email}</span>
          <span class="font-label-sm text-zinc-500">Pro Plan</span>
        </div>
        <button id="logout-btn" title="Log out" class="text-zinc-500 hover:text-red-400 transition-colors">
          <span class="material-symbols-outlined text-sm">logout</span>
        </button>
      </div>
    </div>`;

  document.getElementById("logout-btn").addEventListener("click", logout);
}

// ── Render top bar ────────────────────────────────────────────────────────────
export function renderTopbar(title) {
  const user = requireAuth();
  if (!user) return;
  document.getElementById("topbar").innerHTML = `
    <div class="flex items-center gap-4">
      <span class="material-symbols-outlined text-zinc-400 cursor-pointer hover:text-white">search</span>
      <h1 class="font-inter text-lg font-semibold text-blue-500">${title}</h1>
    </div>
    <div class="flex items-center gap-4">
      <span class="material-symbols-outlined text-zinc-400 hover:text-white cursor-pointer">notifications</span>
      <div class="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center border border-zinc-700">
        <span class="material-symbols-outlined text-xs text-zinc-400">person</span>
      </div>
    </div>`;
}

// ── Toast notifications ───────────────────────────────────────────────────────
export function showToast(message, type = "success") {
  const colors = {
    success: "bg-green-900/80 border-green-700 text-green-300",
    error:   "bg-red-900/80 border-red-700 text-red-300",
    info:    "bg-zinc-800 border-zinc-700 text-zinc-300",
  };
  const icon = { success: "check_circle", error: "error", info: "info" }[type];

  const el = document.createElement("div");
  el.className = `fixed bottom-8 left-1/2 -translate-x-1/2 z-[9999] px-4 py-3 border flex items-center gap-2 font-body-sm text-body-sm shadow-xl transition-all ${colors[type]}`;
  el.innerHTML = `<span class="material-symbols-outlined text-sm">${icon}</span><span>${message}</span>`;
  document.body.appendChild(el);
  setTimeout(() => { el.style.opacity = "0"; setTimeout(() => el.remove(), 300); }, 3000);
}

// ── Authenticated fetch wrapper ───────────────────────────────────────────────
export async function authFetch(path, options = {}) {
  const token = localStorage.getItem("forge3d_token");
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (res.status === 401) { 
    // logout(); throw new Error("Unauthenticated"); 
    console.warn("Unauthenticated request"); 
  }
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || `HTTP ${res.status}`);
  return data;
}
