// The access code, kept in this browser until sign-in exists (SPEC-013). A link may carry it in its fragment
// (#token=…), which is never sent to a server; it is moved into storage and removed from the address bar.

const KEY = "hishob.token";

export function readToken(): string {
  const params = new URLSearchParams(window.location.hash.slice(1));
  const fromLink = params.get("token");
  try {
    if (fromLink) {
      localStorage.setItem(KEY, fromLink);
      params.delete("token");
      const rest = params.toString().replace(/=(?=&|$)/g, "");
      history.replaceState(null, "", window.location.pathname + (rest ? `#${rest}` : ""));
    }
    return localStorage.getItem(KEY) ?? "";
  } catch {
    return fromLink ?? "";
  }
}

export function saveToken(token: string): void {
  try {
    localStorage.setItem(KEY, token);
  } catch {
    /* storage may be blocked */
  }
}

export function forgetToken(): void {
  try {
    localStorage.removeItem(KEY);
  } catch {
    /* ignore */
  }
}

/** The tier a code claims, from its first part. For showing the right tabs only: the server decides what it allows. */
export function tierOf(token: string): string {
  return token.split(".")[0] ?? "";
}
