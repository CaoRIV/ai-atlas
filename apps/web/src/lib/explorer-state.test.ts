import { describe, expect, it } from "vitest";

import {
  buildExplorerHref,
  getEffectiveExplorerSort,
  parseExplorerState,
  toCatalogQuery,
  withExplorerFilters,
  withExplorerSearch,
} from "./explorer-state";

describe("Explorer URL state", () => {
  it("parses every applied filter and serializes the canonical catalog request", () => {
    const state = parseExplorerState(
      new URLSearchParams(
        "q=%20mo%CC%82+hi%CC%80nh%20&category=coding-development,research-learning,coding-development&platform=windows&pricing_model=freemium&api_available=false&open_source=true&sort=updated&page=3",
      ),
    );

    expect(state).toEqual({
      apiAvailable: false,
      categories: ["coding-development", "research-learning"],
      openSource: true,
      page: 3,
      platform: "windows",
      pricingModel: "freemium",
      q: "mô hình",
      sort: "updated",
    });
    expect(toCatalogQuery(state).toString()).toBe(
      "q=m%C3%B4+h%C3%ACnh&category=coding-development%2Cresearch-learning&platform=windows&pricing_model=freemium&api_available=false&open_source=true&sort=updated&page=3&page_size=20",
    );
    expect(buildExplorerHref(state)).toBe(
      "/explorer?q=m%C3%B4+h%C3%ACnh&category=coding-development%2Cresearch-learning&platform=windows&pricing_model=freemium&api_available=false&open_source=true&sort=updated&page=3",
    );
  });

  it("uses relevance only with a query and resets pagination after search or filter changes", () => {
    const searched = parseExplorerState(new URLSearchParams("q=assistant&page=4"));
    expect(getEffectiveExplorerSort(searched)).toBe("relevance");

    const cleared = withExplorerSearch(
      parseExplorerState(new URLSearchParams("q=assistant&sort=relevance&page=4")),
      " ",
    );
    expect(cleared.page).toBe(1);
    expect(cleared.sort).toBeNull();
    expect(toCatalogQuery(cleared).toString()).toBe("sort=name&page=1&page_size=20");

    const filtered = withExplorerFilters(searched, {
      apiAvailable: true,
      categories: ["ai-agents"],
    });
    expect(filtered.page).toBe(1);
    expect(filtered.apiAvailable).toBe(true);
    expect(filtered.categories).toEqual(["ai-agents"]);
  });

  it("falls back safely for malformed scalar URL values", () => {
    const state = parseExplorerState(
      new URLSearchParams(
        "platform=desktop&pricing_model=cheap&api_available=yes&open_source=0&sort=relevance&page=0",
      ),
    );

    expect(state).toMatchObject({
      apiAvailable: null,
      openSource: null,
      page: 1,
      platform: null,
      pricingModel: null,
      sort: null,
    });
    expect(getEffectiveExplorerSort(state)).toBe("name");
  });
});
