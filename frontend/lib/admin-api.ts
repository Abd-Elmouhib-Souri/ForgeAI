// Admin console client (Sprint 7.1).
//
// The console talks to the SEPARATE admin API (port 8002 by default, private network),
// never to the public API. Admin tokens are short-lived (15 min) and have no
// silent refresh: an expired session goes back to the login page.

export const ADMIN_API_URL =
  process.env.NEXT_PUBLIC_ADMIN_API_URL || "http://localhost:8002";

const TOKEN_KEY = "admin_access_token";
const CONFIRMATION_HEADER = "X-Admin-Confirmation";

export function getAdminToken() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setAdminToken(token: string) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function removeAdminToken() {
  localStorage.removeItem(TOKEN_KEY);
}

// Backend errors are either a string or {reason, message}.
export class AdminApiError extends Error {
  status: number;
  reason?: string;

  constructor(status: number, detail: unknown, fallback: string) {
    const structured =
      typeof detail === "object" && detail !== null
        ? (detail as { reason?: string; message?: string })
        : undefined;
    super(
      typeof detail === "string"
        ? detail
        : structured?.message || fallback,
    );
    this.status = status;
    this.reason = structured?.reason;
  }
}

async function readJson(response: Response) {
  if (response.status === 204) return null;
  try {
    return await response.json();
  } catch {
    return null;
  }
}

// Unauthenticated / pre-session calls (login, 2FA enrollment): no redirect.
export async function adminRequest(
  path: string,
  { method = "POST", body, token }: { method?: string; body?: unknown; token?: string } = {},
) {
  const response = await fetch(`${ADMIN_API_URL}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await readJson(response);
  return { status: response.status, ok: response.ok, data };
}

// Asks the admin for the current code of the authenticator app.
// Temporary browser prompt: replaced by the console's dialog in Sprint 7.3.
function askConfirmationCode(message?: string): string | null {
  if (typeof window === "undefined") return null;
  const code = window.prompt(
    message || "Action sensible : saisissez le code à 6 chiffres de votre application d'authentification.",
  );
  return code ? code.trim() : null;
}

type AdminFetchOptions = RequestInit & {
  // Sensitive action (role, status, deletion, admin creation): the backend
  // requires a fresh 2FA code and answers 428 without it.
  confirm?: boolean;
};

export async function adminFetch(path: string, options: AdminFetchOptions = {}) {
  const { confirm, ...init } = options;
  const token = getAdminToken();

  let code: string | null = null;
  if (confirm) {
    code = askConfirmationCode();
    if (!code) throw new AdminApiError(428, "Action annulée.", "Action annulée.");
  }

  const response = await fetch(`${ADMIN_API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(code ? { [CONFIRMATION_HEADER]: code } : {}),
      ...(init.headers || {}),
    },
  });

  // Session missing, expired or not an admin: back to the login page.
  if (response.status === 401 || response.status === 403) {
    removeAdminToken();
    if (typeof window !== "undefined") {
      window.location.href = "/admin/login";
    }
    throw new AdminApiError(response.status, null, "Session admin expirée ou accès interdit.");
  }

  const data = await readJson(response);

  // 428 = confirmation code missing or wrong: the session stays open.
  if (response.status === 428) {
    throw new AdminApiError(428, data?.detail, "Code de confirmation invalide.");
  }

  if (!response.ok) {
    throw new AdminApiError(response.status, data?.detail, "Erreur admin.");
  }

  return data;
}
