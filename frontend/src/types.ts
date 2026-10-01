// Shared runtime schemas (Zod) and inferred TypeScript types.
// These mirror the backend Pydantic models and validate API responses at the
// boundary before the UI trusts them.
import { z } from "zod";

export const SearchMode = z.enum(["traditional", "conversational"]);
export type SearchMode = z.infer<typeof SearchMode>;

export const Channel = z.enum(["Mobile", "Desktop", "Voice AI Assistant"]);
export type Channel = z.infer<typeof Channel>;

export const PredictionStatus = z.enum(["none", "success", "error"]);
export type PredictionStatus = z.infer<typeof PredictionStatus>;

export const FlightSearch = z.object({
  id: z.string(),
  origin: z.string(),
  destination: z.string(),
  departure_date: z.string().nullable().optional(),
  return_date: z.string().nullable().optional(),
  adults: z.number().int(),
  children: z.number().int(),
});
export type FlightSearch = z.infer<typeof FlightSearch>;

export const TraditionalInput = z.object({
  previous_searches: z.array(FlightSearch),
  current_search: FlightSearch,
});
export type TraditionalInput = z.infer<typeof TraditionalInput>;

export const ChatMessage = z.object({
  id: z.string(),
  text: z.string(),
});
export type ChatMessage = z.infer<typeof ChatMessage>;

export const ConversationalInput = z.object({
  previous_messages: z.array(ChatMessage),
  current_request: z.string(),
});
export type ConversationalInput = z.infer<typeof ConversationalInput>;

export const NormalizedResult = z.object({
  intent: z.enum(["High", "Medium", "Low"]).nullable(),
  probability: z.number().nullable(),
  probabilityAvailable: z.boolean(),
  explanation: z.string(),
  model: z.string(),
  predictedAt: z.string(),
  durationMs: z.number(),
});
export type NormalizedResult = z.infer<typeof NormalizedResult>;

export const PredictionRun = z.object({
  id: z.string(),
  createdAt: z.string(),
  status: z.enum(["success", "error"]),
  state: z.string(),
  sdkRequest: z.record(z.unknown()),
  rawResponse: z.record(z.unknown()),
  normalized: NormalizedResult.nullable().optional(),
  error: z.record(z.unknown()).nullable().optional(),
  durationMs: z.number(),
});
export type PredictionRun = z.infer<typeof PredictionRun>;

export const Session = z.object({
  id: z.string(),
  name: z.string().nullable().optional(),
  mode: SearchMode,
  createdAt: z.string(),
  updatedAt: z.string(),
  browsingDate: z.string().nullable().optional(),
  browsingLocalTime: z.string().nullable().optional(),
  timeZone: z.string().nullable().optional(),
  channel: Channel,
  traditional: TraditionalInput,
  conversational: ConversationalInput,
  predictionHistory: z.array(PredictionRun),
  lastPredictionStatus: PredictionStatus,
});
export type Session = z.infer<typeof Session>;

export const SessionSummary = z.object({
  id: z.string(),
  name: z.string().nullable().optional(),
  mode: SearchMode,
  createdAt: z.string(),
  updatedAt: z.string(),
  channel: Channel,
  lastPredictionStatus: PredictionStatus,
  predictionCount: z.number(),
});
export type SessionSummary = z.infer<typeof SessionSummary>;

export const SettingsResponse = z.object({
  TYPESAFE_BASE_URL: z.string(),
  TYPESAFE_DEFAULT_MODEL: z.string(),
  apiKeySet: z.boolean(),
});
export type SettingsResponse = z.infer<typeof SettingsResponse>;

export const ConfigResponse = z.object({
  mode: z.string(),
  config: z.record(z.unknown()),
  modifiedAt: z.string().nullable().optional(),
});
export type ConfigResponse = z.infer<typeof ConfigResponse>;

export const TestConnectionResult = z.object({
  endpointReachable: z.boolean(),
  modelAvailable: z.boolean(),
  sdkListModelsOk: z.boolean(),
  availableModels: z.array(z.string()),
  messages: z.array(z.string()),
  success: z.boolean(),
});
export type TestConnectionResult = z.infer<typeof TestConnectionResult>;

export type IntentProfile = "random" | "high" | "medium" | "low";
