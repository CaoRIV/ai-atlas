"use client";

import { useLocale } from "./locale-context";

const copy = {
  vi: {
    eyebrow: "Khám phá có căn cứ",
    heading: "Tìm công cụ AI. Xây stack phù hợp.",
    supporting: "Khám phá công cụ theo nhu cầu và kết hợp thành quy trình có căn cứ.",
    note: "Catalog được tuyển chọn và mọi factual claim sẽ gắn với evidence còn hiệu lực.",
  },
  en: {
    eyebrow: "Evidence-led discovery",
    heading: "Find AI tools. Build the right stack.",
    supporting: "Explore tools for your needs and combine them into an evidence-led workflow.",
    note: "The catalog is curated, and every factual claim will link to current evidence.",
  },
} as const;

export function HomeContent() {
  const { locale } = useLocale();
  const text = copy[locale];

  return (
    <section className="home-intro" aria-labelledby="home-title">
      <p className="eyebrow">{text.eyebrow}</p>
      <h1 id="home-title">{text.heading}</h1>
      <p className="supporting">{text.supporting}</p>
      <p className="foundation-note">{text.note}</p>
    </section>
  );
}
