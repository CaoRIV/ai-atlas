import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { AppShell } from "./app-shell";
import { HomeContent } from "./home-content";

vi.mock("next/navigation", () => ({
  usePathname: () => "/",
}));

let systemUsesLightTheme = false;
const mediaListeners = new Set<(event: MediaQueryListEvent) => void>();

Object.defineProperty(window, "matchMedia", {
  configurable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    addEventListener: (_type: string, listener: (event: MediaQueryListEvent) => void) => {
      mediaListeners.add(listener);
    },
    dispatchEvent: () => true,
    matches: query === "(prefers-color-scheme: light)" && systemUsesLightTheme,
    media: query,
    onchange: null,
    removeEventListener: (_type: string, listener: (event: MediaQueryListEvent) => void) => {
      mediaListeners.delete(listener);
    },
  })),
  writable: true,
});

function setSystemTheme(light: boolean) {
  systemUsesLightTheme = light;
  const event = { matches: light } as MediaQueryListEvent;
  mediaListeners.forEach((listener) => listener(event));
}

afterEach(() => {
  cleanup();
  mediaListeners.clear();
});

beforeEach(() => {
  systemUsesLightTheme = false;
  window.localStorage.clear();
  document.documentElement.dataset.theme = "dark";
  document.documentElement.lang = "vi";
  document.documentElement.style.colorScheme = "dark";
});

describe("AppShell preferences", () => {
  it("renders the active Vietnamese navigation and switches locale", () => {
    render(
      <AppShell>
        <HomeContent />
      </AppShell>,
    );

    expect(screen.getByRole("link", { name: "Trang chủ" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(
      screen.getByRole("heading", { name: "Tìm công cụ AI. Xây stack phù hợp." }),
    ).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Ngôn ngữ"), {
      target: { value: "en" },
    });

    expect(
      screen.getByRole("heading", { name: "Find AI tools. Build the right stack." }),
    ).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("en");
    expect(window.localStorage.getItem("ai-atlas-locale")).toBe("en");
  });

  it("persists explicit themes and follows the OS only in system mode", () => {
    render(
      <AppShell>
        <HomeContent />
      </AppShell>,
    );

    const themeControl = screen.getByLabelText("Giao diện");
    fireEvent.change(themeControl, { target: { value: "light" } });

    expect(document.documentElement.dataset.theme).toBe("light");
    expect(document.documentElement.style.colorScheme).toBe("light");
    expect(window.localStorage.getItem("ai-atlas-theme")).toBe("light");

    setSystemTheme(false);
    expect(document.documentElement.dataset.theme).toBe("light");

    fireEvent.change(themeControl, { target: { value: "system" } });
    expect(document.documentElement.dataset.theme).toBe("dark");

    setSystemTheme(true);
    expect(document.documentElement.dataset.theme).toBe("light");
    expect(window.localStorage.getItem("ai-atlas-theme")).toBe("system");
  });

  it("traps focus in the responsive drawer and restores it after Escape", async () => {
    render(
      <AppShell>
        <HomeContent />
      </AppShell>,
    );

    const trigger = screen.getByRole("button", { name: "Mở điều hướng" });
    fireEvent.click(trigger);

    const drawer = await screen.findByRole("dialog", { name: "Điều hướng" });
    const closeButton = within(drawer).getByRole("button", { name: "Đóng điều hướng" });
    await waitFor(() => expect(closeButton).toHaveFocus());

    fireEvent.keyDown(drawer, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    expect(trigger).toHaveFocus();
  });
});
