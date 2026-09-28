"use client";

import Link from "next/link";
import { type ReactNode, useCallback, useEffect, useMemo, useSyncExternalStore } from "react";

import { LocaleContext, type Locale } from "./locale-context";

const localeStorageKey = "ai-atlas-locale";
const localeChangeEvent = "ai-atlas-locale-change";

function readStoredLocale(): Locale {
  const storedLocale = window.localStorage.getItem(localeStorageKey);
  return storedLocale === "en" ? "en" : "vi";
}

function subscribeToLocaleChange(onStoreChange: () => void): () => void {
  window.addEventListener("storage", onStoreChange);
  window.addEventListener(localeChangeEvent, onStoreChange);
  return () => {
    window.removeEventListener("storage", onStoreChange);
    window.removeEventListener(localeChangeEvent, onStoreChange);
  };
}

const shellCopy = {
  vi: {
    skip: "Đi tới nội dung chính",
    locale: "Ngôn ngữ",
  },
  en: {
    skip: "Skip to main content",
    locale: "Language",
  },
} as const;

export function AppShell({ children }: { children: ReactNode }) {
  const locale = useSyncExternalStore<Locale>(
    subscribeToLocaleChange,
    readStoredLocale,
    (): Locale => "vi",
  );

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const setLocale = useCallback((nextLocale: Locale) => {
    window.localStorage.setItem(localeStorageKey, nextLocale);
    document.documentElement.lang = nextLocale;
    window.dispatchEvent(new Event(localeChangeEvent));
  }, []);

  const context = useMemo(
    () => ({
      locale,
      setLocale,
    }),
    [locale, setLocale],
  );
  const copy = shellCopy[locale];

  return (
    <LocaleContext.Provider value={context}>
      <a className="skip-link" href="#main-content">
        {copy.skip}
      </a>
      <div className="app-shell">
        <aside className="sidebar">
          <Link className="wordmark" href="/">
            AI Atlas
          </Link>
          <label className="locale-control">
            <span>{copy.locale}</span>
            <select
              aria-label={copy.locale}
              onChange={(event) => context.setLocale(event.target.value as Locale)}
              value={locale}
            >
              <option value="vi">Tiếng Việt</option>
              <option value="en">English</option>
            </select>
          </label>
        </aside>
        <main id="main-content">{children}</main>
      </div>
    </LocaleContext.Provider>
  );
}
