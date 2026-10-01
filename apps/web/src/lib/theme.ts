export const themeStorageKey = "ai-atlas-theme";
export const themeChangeEvent = "ai-atlas-theme-change";
export const systemThemeQuery = "(prefers-color-scheme: light)";

export type ThemePreference = "dark" | "light" | "system";
export type ResolvedTheme = Exclude<ThemePreference, "system">;

export const themeBootstrapScript = `(() => {
  const root = document.documentElement;
  let preference = "dark";

  try {
    const stored = window.localStorage.getItem("${themeStorageKey}");
    if (stored === "light" || stored === "system") preference = stored;
  } catch {}

  const resolved = preference === "light" ||
    (preference === "system" && window.matchMedia?.("${systemThemeQuery}").matches)
    ? "light"
    : "dark";

  root.dataset.theme = resolved;
  root.style.colorScheme = resolved;
})();`;
