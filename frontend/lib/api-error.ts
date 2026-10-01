export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (
    typeof error === "object" &&
    error !== null &&
    "response" in error
  ) {
    const response = (error as { response?: unknown }).response;

    if (
      typeof response === "object" &&
      response !== null &&
      "data" in response
    ) {
      const data = (response as { data?: unknown }).data;

      if (
        typeof data === "object" &&
        data !== null &&
        "detail" in data
      ) {
        const detail = (data as { detail?: unknown }).detail;

        if (typeof detail === "string" && detail.trim().length > 0) {
          return detail;
        }
      }
    }

    // A validation error (422, detail = list) or a server error: axios's
    // English technical message must never reach the page.
    return fallback; // HTTP error without a readable detail
  }

  if (error instanceof Error && error.message.trim().length > 0) {
    return error.message;
  }

  return fallback;
}
