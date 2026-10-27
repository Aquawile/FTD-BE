// A read that fails for a moment (the server was busy, a request was dropped) is tried again before the
// user ever sees an error. Only GET requests are retried: a write is never repeated behind the user's back.
const RETRYABLE_STATUS = new Set([500, 502, 503, 504]);
const DELAYS_MS = [400, 1200];

export async function fetchRetry(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
  const method = (init?.method ?? "GET").toUpperCase();
  if (method !== "GET") return fetch(input, init);
  for (let attempt = 0; ; attempt++) {
    const last = attempt >= DELAYS_MS.length;
    try {
      const res = await fetch(input, init);
      if (last || !RETRYABLE_STATUS.has(res.status)) return res;
    } catch (err) {
      if (last || init?.signal?.aborted) throw err;
    }
    await new Promise(resolve => setTimeout(resolve, DELAYS_MS[attempt]));
    if (init?.signal?.aborted) throw new DOMException("Aborted", "AbortError");
  }
}
