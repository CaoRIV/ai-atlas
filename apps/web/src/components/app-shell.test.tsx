import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import { AppShell } from "./app-shell";
import { HomeContent } from "./home-content";

describe("AppShell locale", () => {
  beforeEach(() => {
    window.localStorage.clear();
    document.documentElement.lang = "vi";
  });

  it("renders Vietnamese by default and switches to English", () => {
    render(
      <AppShell>
        <HomeContent />
      </AppShell>,
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
});
