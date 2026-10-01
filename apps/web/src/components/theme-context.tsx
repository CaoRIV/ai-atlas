"use client";

import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useSyncExternalStore,
} from "react";

import {
  type ResolvedTheme,
  systemThemeQuery,
  themeChangeEvent,
  type ThemePreference,
  themeStorageKey,
} from "../lib/theme";

type ThemeContextValue = {
  resolvedTheme: ResolvedTheme;
  setTheme: (theme: ThemePreference) => void;
  theme: ThemePreference;
};

const ThemeContext = createContext<ThemeContextValue | null>(null);
let fallbackTheme: ThemePreference = "dark";

function readStoredTheme(): ThemePreference {
  try {
    const storedTheme = window.localStorage.getItem(themeStorageKey);
    if (storedTheme === "light" || storedTheme === "system") {
      return storedTheme;
    }
    return "dark";
  } catch {
    return fallbackTheme;
  }
}

function resolveTheme(theme: ThemePreference): ResolvedTheme {
  if (theme === "system") {
    return window.matchMedia(systemThemeQuery).matches ? "light" : "dark";
  }
  return theme;
}

function applyTheme(theme: ThemePreference): ResolvedTheme {
  const resolvedTheme = resolveTheme(theme);
  document.documentElement.dataset.theme = resolvedTheme;
  document.documentElement.style.colorScheme = resolvedTheme;
  return resolvedTheme;
}

function getThemeSnapshot(): string {
  const theme = readStoredTheme();
  return `${theme}:${resolveTheme(theme)}`;
}

function subscribeToThemeChange(onStoreChange: () => void): () => void {
  const mediaQuery = window.matchMedia(systemThemeQuery);
  const handleChange = () => {
    applyTheme(readStoredTheme());
    onStoreChange();
  };

  window.addEventListener("storage", handleChange);
  window.addEventListener(themeChangeEvent, handleChange);
  mediaQuery.addEventListener("change", handleChange);

  return () => {
    window.removeEventListener("storage", handleChange);
    window.removeEventListener(themeChangeEvent, handleChange);
    mediaQuery.removeEventListener("change", handleChange);
  };
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const snapshot = useSyncExternalStore(
    subscribeToThemeChange,
    getThemeSnapshot,
    () => "dark:dark",
  );
  const [theme, resolvedTheme] = snapshot.split(":") as [ThemePreference, ResolvedTheme];

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  const setTheme = useCallback((nextTheme: ThemePreference) => {
    fallbackTheme = nextTheme;
    try {
      window.localStorage.setItem(themeStorageKey, nextTheme);
    } catch {
      // The in-memory fallback keeps the control usable when storage is unavailable.
    }
    applyTheme(nextTheme);
    window.dispatchEvent(new Event(themeChangeEvent));
  }, []);

  const context = useMemo(
    () => ({ resolvedTheme, setTheme, theme }),
    [resolvedTheme, setTheme, theme],
  );

  return <ThemeContext.Provider value={context}>{children}</ThemeContext.Provider>;
}

export function useTheme(): ThemeContextValue {
  const context = useContext(ThemeContext);
  if (context === null) {
    throw new Error("useTheme must be used inside ThemeProvider");
  }
  return context;
}
