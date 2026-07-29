const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function getAdminToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("admin_access_token");
}

export function setAdminToken(token: string) {
  localStorage.setItem("admin_access_token", token);
}

export function removeAdminToken() {
  localStorage.removeItem("admin_access_token");
}

export async function adminFetch(path: string, options: RequestInit = {}) {
  const token = getAdminToken();

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });

  if (response.status === 401 || response.status === 403) {
    removeAdminToken();

    if (typeof window !== "undefined") {
      window.location.href = "/admin/login";
    }

    throw new Error("Session admin expirée ou accès interdit.");
  }

  if (response.status === 204) {
    return null;
  }

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || "Erreur admin.");
  }

  return data;
}