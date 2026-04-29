/**
 * Forge3D – Frontend API Client
 * All calls to the Flask backend go through this module.
 * Set FORGE3D_API_BASE in your environment or override below.
 */

const isLocal = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";
const API_BASE = window.FORGE3D_API_BASE || (isLocal ? "http://localhost:5000/api" : "/api");

// ── Token helpers ─────────────────────────────────────────────────────────────
export const Auth = {
  getToken: () => localStorage.getItem("forge3d_token"),
  setToken: (t) => localStorage.setItem("forge3d_token", t),
  removeToken: () => localStorage.removeItem("forge3d_token"),
  getUser: () => {
    try { return JSON.parse(localStorage.getItem("forge3d_user") || "null"); }
    catch { return null; }
  },
  setUser: (u) => localStorage.setItem("forge3d_user", JSON.stringify(u)),
  clear: () => { Auth.removeToken(); localStorage.removeItem("forge3d_user"); },
  isLoggedIn: () => !!Auth.getToken(),
};

// ── Core fetch wrapper ────────────────────────────────────────────────────────
async function apiFetch(path, options = {}) {
  const token = Auth.getToken();
  const headers = {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };

  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
  });

  // Auto-logout on 401
  if (res.status === 401) {
    Auth.clear();
    window.location.href = "/login.html";
    throw new Error("Session expired. Please log in again.");
  }

  const json = await res.json();

  if (!res.ok) {
    throw new Error(json.error || `HTTP ${res.status}`);
  }

  return json;
}

// ── Auth API ──────────────────────────────────────────────────────────────────
export const AuthAPI = {
  signup: (email, password) =>
    apiFetch("/signup", { method: "POST", body: JSON.stringify({ email, password }) }),

  login: (email, password) =>
    apiFetch("/login", { method: "POST", body: JSON.stringify({ email, password }) }),

  me: () => apiFetch("/me"),
};

// ── Projects API ──────────────────────────────────────────────────────────────
export const ProjectsAPI = {
  list: (limit = 50, offset = 0) =>
    apiFetch(`/projects?limit=${limit}&offset=${offset}`),

  create: (name) =>
    apiFetch("/projects", { method: "POST", body: JSON.stringify({ name }) }),

  delete: (id) =>
    apiFetch(`/projects/${id}`, { method: "DELETE" }),
};

// ── Assets API ────────────────────────────────────────────────────────────────
export const AssetsAPI = {
  listForProject: (projectId, limit = 100, offset = 0) =>
    apiFetch(`/projects/${projectId}/assets?limit=${limit}&offset=${offset}`),

  create: (projectId, fileUrl, filename) =>
    apiFetch("/assets", {
      method: "POST",
      body: JSON.stringify({ project_id: projectId, file_url: fileUrl, filename }),
    }),

  delete: (assetId) =>
    apiFetch(`/assets/${assetId}`, { method: "DELETE" }),
};

// ── Upload API ────────────────────────────────────────────────────────────────
export const UploadAPI = {
  /**
   * Full upload flow:
   *  1. Get signed URL from backend
   *  2. PUT the file to Supabase Storage
   *  3. Save metadata via /api/assets
   *
   * @param {File}   file       - File object from <input type="file">
   * @param {string} projectId  - Target project UUID
   * @param {function} onProgress - Optional callback(percent: number)
   */
  upload: async (file, projectId, onProgress) => {
    // Step 1: get signed URL
    const { upload_url, file_url } = await apiFetch("/upload-url", {
      method: "POST",
      body: JSON.stringify({
        filename: file.name,
        project_id: projectId,
        content_type: file.type || "application/octet-stream",
      }),
    });

    // Step 2: upload directly to Supabase Storage
    await new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open("PUT", upload_url);
      xhr.setRequestHeader("Content-Type", file.type || "application/octet-stream");
      if (onProgress) {
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable) onProgress(Math.round((e.loaded / e.total) * 100));
        };
      }
      xhr.onload  = () => (xhr.status < 300 ? resolve() : reject(new Error(`Upload failed: ${xhr.status}`)));
      xhr.onerror = () => reject(new Error("Network error during upload."));
      xhr.send(file);
    });

    // Step 3: save metadata
    const { asset } = await AssetsAPI.create(projectId, file_url, file.name);
    return asset;
  },
};
