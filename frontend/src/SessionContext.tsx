// Keeps the "currently selected session" available across navigation.
import { createContext, useContext, useState, type ReactNode } from "react";
import type { Session } from "./types";

interface SessionCtx {
  active: Session | null;
  setActive: (s: Session | null) => void;
}

const Ctx = createContext<SessionCtx | null>(null);

export function SessionProvider({ children }: { children: ReactNode }) {
  const [active, setActive] = useState<Session | null>(null);
  return <Ctx.Provider value={{ active, setActive }}>{children}</Ctx.Provider>;
}

export function useActiveSession(): SessionCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useActiveSession must be used within SessionProvider");
  return ctx;
}
