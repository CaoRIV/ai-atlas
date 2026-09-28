import { describe, expect, it } from "vitest";

import { GET } from "./route";

describe("web health route", () => {
  it("returns a stable liveness response", async () => {
    const response = GET();

    expect(response.status).toBe(200);
    await expect(response.json()).resolves.toEqual({ status: "ok", service: "web" });
  });
});
