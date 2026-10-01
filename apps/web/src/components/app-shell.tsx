"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { House, Menu, Monitor, Moon, Sun, X } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState,
  useSyncExternalStore,
} from "react";

import { LocaleContext, type Locale } from "./locale-context";
import { ThemeProvider, useTheme } from "./theme-context";

const localeStorageKey = "ai-atlas-locale";
const localeChangeEvent = "ai-atlas-locale-change";
let fallbackLocale: Locale = "vi";

function readStoredLocale(): Locale {
  try {
    return window.localStorage.getItem(localeStorageKey) === "en" ? "en" : "vi";
  } catch {
    return fallbackLocale;
  }
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
    closeMenu: "Đóng điều hướng",
    drawerDescription: "Điều hướng chính và tùy chọn hiển thị của AI Atlas.",
    drawerTitle: "Điều hướng",
    home: "Trang chủ",
    locale: "Ngôn ngữ",
    menu: "Mở điều hướng",
    navigation: "Điều hướng chính",
    navigationGroup: "Khám phá",
    preferences: "Tùy chọn hiển thị",
    sidebar: "Thanh bên ứng dụng",
    skip: "Đi tới nội dung chính",
    switchToDark: "Chuyển sang giao diện tối",
    switchToLight: "Chuyển sang giao diện sáng",
    theme: "Giao diện",
    themeDark: "Tối",
    themeLight: "Sáng",
    themeSystem: "Theo hệ thống",
  },
  en: {
    closeMenu: "Close navigation",
    drawerDescription: "AI Atlas primary navigation and display preferences.",
    drawerTitle: "Navigation",
    home: "Home",
    locale: "Language",
    menu: "Open navigation",
    navigation: "Primary navigation",
    navigationGroup: "Discover",
    preferences: "Display preferences",
    sidebar: "Application sidebar",
    skip: "Skip to main content",
    switchToDark: "Switch to dark theme",
    switchToLight: "Switch to light theme",
    theme: "Theme",
    themeDark: "Dark",
    themeLight: "Light",
    themeSystem: "System",
  },
} as const;

type ShellCopy = (typeof shellCopy)[Locale];

function Navigation({ copy, onNavigate }: { copy: ShellCopy; onNavigate?: () => void }) {
  const pathname = usePathname();
  const isHome = pathname === "/";

  return (
    <nav aria-label={copy.navigation} className="shell-navigation">
      <p className="navigation-group-label">{copy.navigationGroup}</p>
      <Link
        aria-current={isHome ? "page" : undefined}
        className="navigation-link"
        href="/"
        onClick={onNavigate}
      >
        <House aria-hidden="true" size={19} strokeWidth={1.75} />
        <span>{copy.home}</span>
      </Link>
    </nav>
  );
}

function ThemeGlyph({ resolvedTheme, system }: { resolvedTheme: "dark" | "light"; system?: boolean }) {
  if (system) {
    return <Monitor aria-hidden="true" size={18} strokeWidth={1.75} />;
  }
  return resolvedTheme === "dark" ? (
    <Moon aria-hidden="true" size={18} strokeWidth={1.75} />
  ) : (
    <Sun aria-hidden="true" size={18} strokeWidth={1.75} />
  );
}

function PreferenceControls({ copy, locale, setLocale }: {
  copy: ShellCopy;
  locale: Locale;
  setLocale: (locale: Locale) => void;
}) {
  const { resolvedTheme, setTheme, theme } = useTheme();

  return (
    <div aria-label={copy.preferences} className="preference-controls" role="group">
      <label className="preference-field">
        <span>{copy.theme}</span>
        <span className="select-control">
          <ThemeGlyph resolvedTheme={resolvedTheme} system={theme === "system"} />
          <select
            aria-label={copy.theme}
            onChange={(event) => setTheme(event.target.value as "dark" | "light" | "system")}
            value={theme}
          >
            <option value="dark">{copy.themeDark}</option>
            <option value="light">{copy.themeLight}</option>
            <option value="system">{copy.themeSystem}</option>
          </select>
        </span>
      </label>
      <label className="preference-field">
        <span>{copy.locale}</span>
        <span className="select-control select-control--language">
          <select
            aria-label={copy.locale}
            onChange={(event) => setLocale(event.target.value as Locale)}
            value={locale}
          >
            <option value="vi">Tiếng Việt</option>
            <option value="en">English</option>
          </select>
        </span>
      </label>
    </div>
  );
}

function ShellFrame({ children, locale, setLocale }: {
  children: ReactNode;
  locale: Locale;
  setLocale: (locale: Locale) => void;
}) {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const { resolvedTheme, setTheme } = useTheme();
  const copy = shellCopy[locale];
  const toggleLabel = resolvedTheme === "dark" ? copy.switchToLight : copy.switchToDark;

  return (
    <>
      <a className="skip-link" href="#main-content">
        {copy.skip}
      </a>
      <div className="app-shell">
        <aside aria-label={copy.sidebar} className="desktop-sidebar">
          <Link className="wordmark" href="/">
            AI Atlas
          </Link>
          <Navigation copy={copy} />
          <PreferenceControls copy={copy} locale={locale} setLocale={setLocale} />
        </aside>

        <header className="mobile-header">
          <Dialog.Root onOpenChange={setDrawerOpen} open={drawerOpen}>
            <Dialog.Trigger asChild>
              <button aria-label={copy.menu} className="icon-button" type="button">
                <Menu aria-hidden="true" size={20} strokeWidth={1.75} />
              </button>
            </Dialog.Trigger>
            <Dialog.Portal>
              <Dialog.Overlay className="drawer-overlay" />
              <Dialog.Content className="drawer-content">
                <div className="drawer-heading">
                  <Dialog.Title>{copy.drawerTitle}</Dialog.Title>
                  <Dialog.Close asChild>
                    <button aria-label={copy.closeMenu} className="icon-button" type="button">
                      <X aria-hidden="true" size={20} strokeWidth={1.75} />
                    </button>
                  </Dialog.Close>
                </div>
                <Dialog.Description className="visually-hidden">
                  {copy.drawerDescription}
                </Dialog.Description>
                <Navigation copy={copy} onNavigate={() => setDrawerOpen(false)} />
                <PreferenceControls copy={copy} locale={locale} setLocale={setLocale} />
              </Dialog.Content>
            </Dialog.Portal>
          </Dialog.Root>

          <Link className="wordmark mobile-wordmark" href="/">
            AI Atlas
          </Link>
          <button
            aria-label={toggleLabel}
            className="icon-button"
            onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
            type="button"
          >
            <ThemeGlyph resolvedTheme={resolvedTheme} />
          </button>
        </header>

        <main className="main-content" id="main-content" tabIndex={-1}>
          <div className="main-content-inner">{children}</div>
        </main>
      </div>
    </>
  );
}

function LocaleShell({ children }: { children: ReactNode }) {
  const locale = useSyncExternalStore<Locale>(
    subscribeToLocaleChange,
    readStoredLocale,
    (): Locale => "vi",
  );

  useEffect(() => {
    document.documentElement.lang = locale;
  }, [locale]);

  const setLocale = useCallback((nextLocale: Locale) => {
    fallbackLocale = nextLocale;
    try {
      window.localStorage.setItem(localeStorageKey, nextLocale);
    } catch {
      // The in-memory fallback keeps locale switching available without storage.
    }
    document.documentElement.lang = nextLocale;
    window.dispatchEvent(new Event(localeChangeEvent));
  }, []);

  const context = useMemo(() => ({ locale, setLocale }), [locale, setLocale]);

  return (
    <LocaleContext.Provider value={context}>
      <ShellFrame locale={locale} setLocale={setLocale}>
        {children}
      </ShellFrame>
    </LocaleContext.Provider>
  );
}

export function AppShell({ children }: { children: ReactNode }) {
  return (
    <ThemeProvider>
      <LocaleShell>{children}</LocaleShell>
    </ThemeProvider>
  );
}
