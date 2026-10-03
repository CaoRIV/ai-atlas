"use client";

import * as Dialog from "@radix-ui/react-dialog";
import { SlidersHorizontal, X } from "lucide-react";
import { useId, useMemo, useState } from "react";

import type { Category, Platform, PricingModel } from "../lib/catalog/types";
import type { ExplorerFilters } from "../lib/explorer-state";
import type { Locale } from "./locale-context";

export type CategoryLoadState =
  | { status: "loading" }
  | { data: Category[]; status: "success" }
  | { requestId: string | null; status: "error" };

type FilterControlsProps = {
  categoriesState: CategoryLoadState;
  locale: Locale;
  onApply: (filters: ExplorerFilters) => void;
  onRetryCategories: () => void;
  selection: ExplorerFilters;
};

type FilterFieldsProps = {
  categoriesState: CategoryLoadState;
  locale: Locale;
  onChange: (filters: ExplorerFilters) => void;
  onRetryCategories: () => void;
  selection: ExplorerFilters;
};

type AppliedFilterChipsProps = {
  categories: Category[];
  locale: Locale;
  onChange: (filters: ExplorerFilters) => void;
  selection: ExplorerFilters;
};

const platforms: Platform[] = ["web", "windows", "macos", "linux", "ios", "android"];
const pricingModels: PricingModel[] = [
  "free",
  "freemium",
  "paid",
  "usage_based",
  "contact",
  "unknown",
];

const copy = {
  vi: {
    all: "Tất cả",
    api: "Khả dụng API",
    apply: "Áp dụng",
    cancel: "Hủy",
    categories: "Danh mục",
    categoriesError: "Chưa thể tải danh mục.",
    categoriesLoading: "Đang tải danh mục…",
    categoryOrHint: "Chọn nhiều danh mục để tìm kết quả thuộc bất kỳ danh mục nào.",
    clear: "Xóa bộ lọc",
    clearDraft: "Xóa lựa chọn",
    close: "Đóng bộ lọc",
    drawerDescription: "Chọn bộ lọc rồi áp dụng một lần cho kết quả Explorer.",
    filters: (count: number) => `Bộ lọc (${count})`,
    no: "Không",
    openSource: "Mã nguồn mở",
    platform: "Nền tảng",
    platforms: {
      android: "Android",
      ios: "iOS",
      linux: "Linux",
      macos: "macOS",
      web: "Web",
      windows: "Windows",
    },
    pricing: "Mô hình giá",
    pricingModels: {
      contact: "Liên hệ",
      free: "Miễn phí",
      freemium: "Có gói miễn phí",
      paid: "Trả phí",
      unknown: "Chưa xác minh",
      usage_based: "Theo mức dùng",
    },
    pricingUnknownHint: "Chưa xác minh cũng gồm dữ liệu unknown, unverified hoặc stale.",
    remove: "Bỏ bộ lọc",
    requestId: "Mã yêu cầu",
    retry: "Thử lại",
    title: "Bộ lọc",
    yes: "Có",
  },
  en: {
    all: "All",
    api: "API available",
    apply: "Apply",
    cancel: "Cancel",
    categories: "Categories",
    categoriesError: "Categories are unavailable.",
    categoriesLoading: "Loading categories…",
    categoryOrHint: "Choose multiple categories to match tools in any selected category.",
    clear: "Clear filters",
    clearDraft: "Clear selection",
    close: "Close filters",
    drawerDescription: "Choose filters, then apply them once to the Explorer results.",
    filters: (count: number) => `Filters (${count})`,
    no: "No",
    openSource: "Open source",
    platform: "Platform",
    platforms: {
      android: "Android",
      ios: "iOS",
      linux: "Linux",
      macos: "macOS",
      web: "Web",
      windows: "Windows",
    },
    pricing: "Pricing model",
    pricingModels: {
      contact: "Contact",
      free: "Free",
      freemium: "Free tier available",
      paid: "Paid",
      unknown: "Not verified",
      usage_based: "Usage based",
    },
    pricingUnknownHint: "Not verified also includes unknown, unverified, or stale data.",
    remove: "Remove filter",
    requestId: "Request ID",
    retry: "Try again",
    title: "Filters",
    yes: "Yes",
  },
} as const;

export function countAppliedFilters(selection: ExplorerFilters): number {
  return (
    selection.categories.length +
    Number(selection.platform !== null) +
    Number(selection.pricingModel !== null) +
    Number(selection.apiAvailable !== null) +
    Number(selection.openSource !== null)
  );
}

export function emptyExplorerFilters(): ExplorerFilters {
  return {
    apiAvailable: null,
    categories: [],
    openSource: null,
    platform: null,
    pricingModel: null,
  };
}

function BooleanSelect({
  label,
  locale,
  onChange,
  value,
}: {
  label: string;
  locale: Locale;
  onChange: (value: boolean | null) => void;
  value: boolean | null;
}) {
  const text = copy[locale];
  return (
    <label className="filter-select">
      <span>{label}</span>
      <select
        onChange={(event) => {
          const next = event.target.value;
          onChange(next === "" ? null : next === "true");
        }}
        value={value === null ? "" : String(value)}
      >
        <option value="">{text.all}</option>
        <option value="true">{text.yes}</option>
        <option value="false">{text.no}</option>
      </select>
    </label>
  );
}

function FilterFields({
  categoriesState,
  locale,
  onChange,
  onRetryCategories,
  selection,
}: FilterFieldsProps) {
  const text = copy[locale];
  const pricingHintId = useId();

  const update = <Key extends keyof ExplorerFilters>(key: Key, value: ExplorerFilters[Key]) => {
    onChange({ ...selection, [key]: value });
  };

  const toggleCategory = (slug: string, checked: boolean) => {
    const categories = checked
      ? [...selection.categories, slug]
      : selection.categories.filter((category) => category !== slug);
    update("categories", categories);
  };

  return (
    <div className="filter-fields">
      <fieldset className="filter-group">
        <legend>{text.categories}</legend>
        <p className="filter-hint">{text.categoryOrHint}</p>
        {categoriesState.status === "loading" ? (
          <p aria-live="polite" className="filter-inline-status">{text.categoriesLoading}</p>
        ) : null}
        {categoriesState.status === "error" ? (
          <div className="filter-inline-error" role="alert">
            <p>{text.categoriesError}</p>
            {categoriesState.requestId ? (
              <p className="filter-request-id">{text.requestId}: {categoriesState.requestId}</p>
            ) : null}
            <button className="button button-secondary" onClick={onRetryCategories} type="button">
              {text.retry}
            </button>
          </div>
        ) : null}
        {categoriesState.status === "success" ? (
          <div className="filter-checkboxes">
            {categoriesState.data.map((category) => (
              <label className="filter-checkbox" key={category.id}>
                <input
                  checked={selection.categories.includes(category.slug)}
                  onChange={(event) => toggleCategory(category.slug, event.target.checked)}
                  type="checkbox"
                />
                <span>{category.name}</span>
              </label>
            ))}
          </div>
        ) : null}
      </fieldset>

      <label className="filter-select">
        <span>{text.platform}</span>
        <select
          onChange={(event) => update("platform", (event.target.value || null) as Platform | null)}
          value={selection.platform ?? ""}
        >
          <option value="">{text.all}</option>
          {platforms.map((platform) => (
            <option key={platform} value={platform}>{text.platforms[platform]}</option>
          ))}
        </select>
      </label>

      <label className="filter-select">
        <span>{text.pricing}</span>
        <select
          aria-describedby={pricingHintId}
          onChange={(event) => update("pricingModel", (event.target.value || null) as PricingModel | null)}
          value={selection.pricingModel ?? ""}
        >
          <option value="">{text.all}</option>
          {pricingModels.map((pricingModel) => (
            <option key={pricingModel} value={pricingModel}>{text.pricingModels[pricingModel]}</option>
          ))}
        </select>
        <small className="filter-hint" id={pricingHintId}>{text.pricingUnknownHint}</small>
      </label>

      <BooleanSelect
        label={text.api}
        locale={locale}
        onChange={(value) => update("apiAvailable", value)}
        value={selection.apiAvailable}
      />
      <BooleanSelect
        label={text.openSource}
        locale={locale}
        onChange={(value) => update("openSource", value)}
        value={selection.openSource}
      />
    </div>
  );
}

export function ExplorerFilterControls({
  categoriesState,
  locale,
  onApply,
  onRetryCategories,
  selection,
}: FilterControlsProps) {
  const text = copy[locale];
  const appliedCount = countAppliedFilters(selection);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [draft, setDraft] = useState<ExplorerFilters>(() => ({ ...selection, categories: [...selection.categories] }));

  const handleOpenChange = (open: boolean) => {
    if (open) setDraft({ ...selection, categories: [...selection.categories] });
    setDrawerOpen(open);
  };

  const applyDraft = () => {
    onApply(draft);
    setDrawerOpen(false);
  };

  return (
    <div className="explorer-filter-controls">
      <aside aria-label={text.title} className="filter-rail">
        <div className="filter-rail-heading">
          <h2>{text.title}</h2>
          {appliedCount > 0 ? (
            <button className="text-button" onClick={() => onApply(emptyExplorerFilters())} type="button">
              {text.clear}
            </button>
          ) : null}
        </div>
        <FilterFields
          categoriesState={categoriesState}
          locale={locale}
          onChange={onApply}
          onRetryCategories={onRetryCategories}
          selection={selection}
        />
      </aside>

      <Dialog.Root onOpenChange={handleOpenChange} open={drawerOpen}>
        <Dialog.Trigger asChild>
          <button className="button button-secondary mobile-filter-trigger" type="button">
            <SlidersHorizontal aria-hidden="true" size={18} strokeWidth={1.75} />
            <span>{text.filters(appliedCount)}</span>
          </button>
        </Dialog.Trigger>
        <Dialog.Portal>
          <Dialog.Overlay className="drawer-overlay" />
          <Dialog.Content className="filter-drawer-content">
            <div className="drawer-heading">
              <Dialog.Title>{text.title}</Dialog.Title>
              <Dialog.Close asChild>
                <button aria-label={text.close} className="icon-button" type="button">
                  <X aria-hidden="true" size={20} strokeWidth={1.75} />
                </button>
              </Dialog.Close>
            </div>
            <Dialog.Description className="visually-hidden">{text.drawerDescription}</Dialog.Description>
            <FilterFields
              categoriesState={categoriesState}
              locale={locale}
              onChange={setDraft}
              onRetryCategories={onRetryCategories}
              selection={draft}
            />
            <div className="filter-drawer-actions">
              <button className="text-button" onClick={() => setDraft(emptyExplorerFilters())} type="button">
                {text.clearDraft}
              </button>
              <div>
                <Dialog.Close asChild>
                  <button className="button button-secondary" type="button">{text.cancel}</button>
                </Dialog.Close>
                <button className="button button-primary" onClick={applyDraft} type="button">{text.apply}</button>
              </div>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}

export function AppliedFilterChips({
  categories,
  locale,
  onChange,
  selection,
}: AppliedFilterChipsProps) {
  const text = copy[locale];
  const categoryNames = useMemo(
    () => new Map(categories.map((category) => [category.slug, category.name])),
    [categories],
  );
  const chips: Array<{ key: string; label: string; remove: () => ExplorerFilters }> = [];

  for (const slug of selection.categories) {
    const label = `${text.categories}: ${categoryNames.get(slug) ?? slug}`;
    chips.push({
      key: `category:${slug}`,
      label,
      remove: () => ({
        ...selection,
        categories: selection.categories.filter((category) => category !== slug),
      }),
    });
  }
  if (selection.platform) {
    chips.push({
      key: "platform",
      label: `${text.platform}: ${text.platforms[selection.platform]}`,
      remove: () => ({ ...selection, platform: null }),
    });
  }
  if (selection.pricingModel) {
    chips.push({
      key: "pricing",
      label: `${text.pricing}: ${text.pricingModels[selection.pricingModel]}`,
      remove: () => ({ ...selection, pricingModel: null }),
    });
  }
  if (selection.apiAvailable !== null) {
    chips.push({
      key: "api",
      label: `${text.api}: ${selection.apiAvailable ? text.yes : text.no}`,
      remove: () => ({ ...selection, apiAvailable: null }),
    });
  }
  if (selection.openSource !== null) {
    chips.push({
      key: "open-source",
      label: `${text.openSource}: ${selection.openSource ? text.yes : text.no}`,
      remove: () => ({ ...selection, openSource: null }),
    });
  }

  if (chips.length === 0) return null;

  return (
    <div className="applied-filters">
      <ul aria-label={text.title} className="filter-chips">
        {chips.map((chip) => (
          <li key={chip.key}>
            <button aria-label={`${text.remove}: ${chip.label}`} onClick={() => onChange(chip.remove())} type="button">
              <span>{chip.label}</span>
              <X aria-hidden="true" size={16} strokeWidth={1.75} />
            </button>
          </li>
        ))}
      </ul>
      <button className="text-button" onClick={() => onChange(emptyExplorerFilters())} type="button">
        {text.clear}
      </button>
    </div>
  );
}
