"use client";

import { createContext, useContext } from "react";

export type Locale = "en" | "vi";

type LocaleContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
};

export const LocaleContext = createContext<LocaleContextValue | null>(null);

export function useLocale(): LocaleContextValue {
  const context = useContext(LocaleContext);
  if (context === null) {
    throw new Error("useLocale must be used inside AppShell");
  }
  return context;
}
