const BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const ACCESS_KEY = "omniflow.token";
const REFRESH_KEY = "omniflow.refresh";

let onUnauthorized = () => {};
let refreshing = null;

export const getToken = () => localStorage.getItem(ACCESS_KEY);
export const setSession = (data) => {
  localStorage.setItem(ACCESS_KEY, data.access_token);
  localStorage.setItem(REFRESH_KEY, data.refresh_token);
};
export const clearToken = () => {
  localStorage.removeItem(ACCESS_KEY);
  localStorage.removeItem(REFRESH_KEY);
};
export const setUnauthorizedHandler = (fn) => {
  onUnauthorized = fn;
};

function refreshSession() {
  const refresh = localStorage.getItem(REFRESH_KEY);
  if (!refresh) return Promise.resolve(false);
  refreshing ??= fetch(`${BASE}/api/v1/auth/refresh`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refresh_token: refresh }),
  })
    .then(async (response) => {
      if (!response.ok) return false;
      setSession(await response.json());
      return true;
    })
    .catch(() => false)
    .finally(() => {
      refreshing = null;
    });
  return refreshing;
}

async function send(path, method, body) {
  const headers = { "Content-Type": "application/json" };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  try {
    return await fetch(`${BASE}/api/v1${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new Error("Cannot reach the server. Check your connection and try again.");
  }
}

export async function api(path, { method = "GET", body } = {}) {
  const hadToken = Boolean(getToken());
  let response = await send(path, method, body);

  if (response.status === 401 && hadToken && !path.startsWith("/auth/")) {
    if (await refreshSession()) {
      response = await send(path, method, body);
    }
    if (response.status === 401) {
      clearToken();
      onUnauthorized();
    }
  }

  if (!response.ok) {
    let message = "Something went wrong";
    try {
      const data = await response.json();
      if (typeof data.detail === "string") message = data.detail;
      else if (Array.isArray(data.detail)) message = "Please check the details you entered";
    } catch {
      /* body was not JSON */
    }
    throw new Error(message);
  }

  return response.status === 204 ? null : response.json();
}

export const publicBase = BASE;
