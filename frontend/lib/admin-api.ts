// Admin console client (Sprint 7.1, console dialog in 7.3).
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

// Expiry of the current admin token (ms since epoch), read from its "exp"
// claim. Display only: the admin API stays the authority (it answers 401).
export function getAdminTokenExpiry(): number | null {
  const token = getAdminToken();
  if (!token) return null;
  try {
    const payload = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const claims = JSON.parse(atob(payload.padEnd(Math.ceil(payload.length / 4) * 4, "=")));
    return typeof claims.exp === "number" ? claims.exp * 1000 : null;
  } catch {
    return null;
  }
}

// End the admin session on this browser (no refresh token to revoke).
export function adminLogout() {
  removeAdminToken();
  if (typeof window !== "undefined") {
    window.location.replace("/admin/login");
  }
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

// Sprint 7.3: the 2FA code of a sensitive action is asked by the console's
// own dialog (ConfirmDialog registers itself here), never by window.prompt.
export type ConfirmationRequest = {
  message: string; // what is about to happen, in plain French
  error?: string; // the previous code was refused: say why
};

type ConfirmationHandler = (request: ConfirmationRequest) => Promise<string | null>;

let confirmationHandler: ConfirmationHandler | null = null;

export function setConfirmationHandler(handler: ConfirmationHandler | null) {
  confirmationHandler = handler;
}

const DEFAULT_CONFIRMATION =
  "Action sensible : saisissez le code à 6 chiffres de votre application d'authentification.";
const MAX_CONFIRMATION_ATTEMPTS = 3;

// The admin closed the dialog: not an error, the page simply does nothing.
export function isAdminActionCancelled(err: unknown) {
  return err instanceof AdminApiError && err.reason === "cancelled";
}

type AdminFetchOptions = RequestInit & {
  // Sensitive action (role, status, deletion, admin creation): the backend
  // requires a fresh 2FA code and answers 428 without it. A string is the
  // description shown in the dialog.
  confirm?: boolean | string;
};

export async function adminFetch(path: string, options: AdminFetchOptions = {}) {
  const { confirm, ...init } = options;
  const token = getAdminToken();
  const message = typeof confirm === "string" ? confirm : DEFAULT_CONFIRMATION;

  let response: Response | null = null;
  let refusal: string | undefined;

  // One request without a code, or up to 3 codes when a confirmation is required.
  for (let attempt = 0; attempt < (confirm ? MAX_CONFIRMATION_ATTEMPTS : 1); attempt += 1) {
    let code: string | null = null;
    if (confirm) {
      if (!confirmationHandler) {
        throw new AdminApiError(428, "Confirmation indisponible : rechargez la page.", "Confirmation indisponible.");
      }
      code = await confirmationHandler({ message, error: refusal });
      if (!code) {
        throw new AdminApiError(428, { reason: "cancelled", message: "Action annulée." }, "Action annulée.");
      }
    }

    response = await fetch(`${ADMIN_API_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(code ? { [CONFIRMATION_HEADER]: code } : {}),
        ...(init.headers || {}),
      },
    });

    if (response.status !== 428) break;
    const refused = await readJson(response);
    const reason = refused?.detail?.reason;
    if (reason !== "confirmation_invalid" && reason !== "confirmation_required") {
      throw new AdminApiError(428, refused?.detail, "Confirmation refusée.");
    }
    // Wrong or expired code: ask again, with the backend's reason.
    refusal = refused?.detail?.message || "Code de confirmation invalide ou expiré.";
    if (attempt === MAX_CONFIRMATION_ATTEMPTS - 1) {
      throw new AdminApiError(428, refused?.detail, "Code de confirmation invalide.");
    }
  }

  if (!response) throw new AdminApiError(0, null, "Aucune réponse de l'API admin.");

  // Session missing, expired or not an admin: back to the login page.
  if (response.status === 401 || response.status === 403) {
    removeAdminToken();
    if (typeof window !== "undefined") {
      window.location.href = "/admin/login";
    }
    throw new AdminApiError(response.status, null, "Session admin expirée ou accès interdit.");
  }

  const data = await readJson(response);

  if (!response.ok) {
    throw new AdminApiError(response.status, data?.detail, "Erreur admin.");
  }

  return data;
}

// Authenticated file download (CSV of the audit log...): the token travels
// in the header, never in the URL (URLs end up in logs and history).
export async function adminDownload(path: string, fallbackName: string) {
  const token = getAdminToken();
  const response = await fetch(`${ADMIN_API_URL}${path}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (response.status === 401 || response.status === 403) {
    removeAdminToken();
    if (typeof window !== "undefined") {
      window.location.href = "/admin/login";
    }
    throw new AdminApiError(response.status, null, "Session admin expirée ou accès interdit.");
  }
  if (!response.ok) {
    const data = await readJson(response);
    throw new AdminApiError(response.status, data?.detail, "Téléchargement impossible.");
  }

  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = fallbackName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
