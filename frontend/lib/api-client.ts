/**
 * Thin fetch wrapper around the FastAPI backend.
 *
 * Every call returns a Result -- callers branch on `ok` instead of using
 * try/catch, so a failed request can never throw unexpectedly across a
 * Server Action or Server Component boundary. Response bodies are
 * validated against a Zod schema before being trusted.
 */

import type { z } from "zod";

export type Result<T> = { ok: true; data: T } | { ok: false; error: string; status?: number };

function requireEnv(name: string, value: string | undefined): string {
  if (!value) {
    throw new Error(`${name} environment variable is not set`);
  }
  return value;
}

export async function apiFetch<T>(path: string, schema: z.ZodType<T>, init: RequestInit = {}): Promise<Result<T>> {
  let baseUrl: string;
  let userId: string;
  try {
    baseUrl = requireEnv("BACKEND_URL", process.env.BACKEND_URL);
    // TEMP: stands in for real auth until session/JWT auth is designed.
    // Must match api.py's get_current_user_id stub.
    userId = requireEnv("STUB_USER_ID", process.env.STUB_USER_ID);
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : "server is misconfigured" };
  }

  let response: Response;
  try {
    response = await fetch(`${baseUrl}${path}`, {
      ...init,
      headers: { "X-User-Id": userId, ...init.headers },
    });
  } catch {
    return { ok: false, error: "could not reach the server -- check your connection and try again" };
  }

  let body: unknown;
  try {
    body = await response.json();
  } catch {
    return { ok: false, error: "the server returned an unreadable response", status: response.status };
  }

  if (!response.ok) {
    const detail =
      typeof body === "object" && body !== null && "detail" in body && typeof (body as Record<string, unknown>).detail === "string"
        ? ((body as Record<string, unknown>).detail as string)
        : "something went wrong";
    return { ok: false, error: detail, status: response.status };
  }

  const parsed = schema.safeParse(body);
  if (!parsed.success) {
    return { ok: false, error: "the server response didn't match what we expected", status: response.status };
  }
  return { ok: true, data: parsed.data };
}
