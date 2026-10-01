// Thin API client. All requests go to the backend; the browser never touches
// files. Responses are validated with Zod before use.
import {
  ConfigResponse,
  Session,
  SessionSummary,
  SettingsResponse,
  TestConnectionResult,
  type IntentProfile,
  type SearchMode,
} from "./types";
import { z } from "zod";

const BASE = "/api";

async function request<T>(path: string, schema: z.ZodType<T>, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = `Request failed (${res.status})`;
    try {
      const body = await res.json();
      if (typeof body?.detail === "string") detail = body.detail;
      else if (body?.detail?.message) detail = `${body.detail.message}: ${(body.detail.errors || []).join("; ")}`;
      else if (body?.detail) detail = JSON.stringify(body.detail);
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  const data = await res.json();
  return schema.parse(data);
}

export const api = {
  health: () =>
    request(
      "/health",
      z.object({ ok: z.boolean(), sdkAvailable: z.boolean(), sdkImportError: z.string().nullable() }),
    ),

  listSessions: () => request("/sessions", z.array(SessionSummary)),

  getSession: (id: string) => request(`/sessions/${id}`, Session),

  createSession: (session: unknown) =>
    request("/sessions", Session, { method: "POST", body: JSON.stringify(session) }),

  updateSession: (id: string, session: unknown) =>
    request(`/sessions/${id}`, Session, { method: "PUT", body: JSON.stringify(session) }),

  deleteSession: (id: string) =>
    request(`/sessions/${id}`, z.object({ deleted: z.boolean() }), { method: "DELETE" }),

  duplicateSession: (id: string) =>
    request(`/sessions/${id}/duplicate`, Session, { method: "POST" }),

  generate: (mode: SearchMode, profile: IntentProfile) =>
    request("/generate", Session, { method: "POST", body: JSON.stringify({ mode, profile }) }),

  predict: (id: string) => request(`/sessions/${id}/predict`, Session, { method: "POST" }),

  getSettings: () => request("/settings", SettingsResponse),

  updateSettings: (payload: {
    TYPESAFE_BASE_URL: string;
    TYPESAFE_DEFAULT_MODEL: string;
    TYPESAFE_API_KEY?: string;
  }) => request("/settings", SettingsResponse, { method: "PUT", body: JSON.stringify(payload) }),

  resetSettings: () => request("/settings/reset", SettingsResponse, { method: "POST" }),

  testConnection: () => request("/settings/test", TestConnectionResult, { method: "POST" }),

  getConfig: (mode: SearchMode) => request(`/configs/${mode}`, ConfigResponse),

  updateConfig: (mode: SearchMode, config: unknown) =>
    request(`/configs/${mode}`, ConfigResponse, { method: "PUT", body: JSON.stringify({ config }) }),

  resetConfig: (mode: SearchMode) =>
    request(`/configs/${mode}/reset`, ConfigResponse, { method: "POST" }),

  validateConfig: (mode: SearchMode, config: unknown) =>
    request(
      `/configs/${mode}/validate`,
      z.object({ valid: z.boolean(), errors: z.array(z.string()) }),
      { method: "POST", body: JSON.stringify({ config }) },
    ),
};
