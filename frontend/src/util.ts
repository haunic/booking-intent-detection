// Small shared helpers: IATA reference list, date math, display formatting.

export const AIRPORTS: { code: string; city: string }[] = [
  { code: "NCE", city: "Nice" },
  { code: "CDG", city: "Paris" },
  { code: "LHR", city: "London" },
  { code: "JFK", city: "New York" },
  { code: "BKK", city: "Bangkok" },
  { code: "DXB", city: "Dubai" },
  { code: "SIN", city: "Singapore" },
  { code: "LAX", city: "Los Angeles" },
  { code: "FCO", city: "Rome" },
  { code: "BCN", city: "Barcelona" },
  { code: "AMS", city: "Amsterdam" },
  { code: "MAD", city: "Madrid" },
  { code: "IST", city: "Istanbul" },
  { code: "HND", city: "Tokyo" },
  { code: "SYD", city: "Sydney" },
  { code: "GRU", city: "Sao Paulo" },
];

export const IATA_CODES = AIRPORTS.map((a) => a.code);

export function parseDate(value?: string | null): Date | null {
  if (!value) return null;
  const d = new Date(value.slice(0, 10) + "T00:00:00");
  return Number.isNaN(d.getTime()) ? null : d;
}

export function daysBetween(a: Date, b: Date): number {
  const ms = b.getTime() - a.getTime();
  return Math.round(ms / (1000 * 60 * 60 * 24));
}

export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

// IANA zones plus simple UTC offsets for the time-zone selector.
export const TIME_ZONES = [
  "UTC+00:00",
  "UTC+01:00",
  "UTC+02:00",
  "UTC+03:00",
  "UTC-05:00",
  "UTC-08:00",
  "UTC+05:30",
  "UTC+07:00",
  "UTC+09:00",
  "UTC+10:00",
];
