"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Download, Plus, Search } from "lucide-react";
import SiteFooter from "@/components/SiteFooter";
import { cn } from "@/lib/utils";

type Row = {
  domain: string;
  company: string;
  category: "DevTools" | "FinTech" | "AI / ML" | "Other";
  overall_score: number;
  dimension_scores: { D1: number; D2: number; D3: number; D4: number; D5: number; D6: number };
  avatar: string;
};

const ROWS: Row[] = [
  { domain: "openai.com", company: "OpenAI, Inc.", category: "AI / ML", overall_score: 43, dimension_scores: { D1: 26, D2: 30, D3: 88, D4: 45, D5: 52, D6: 18 }, avatar: "bg-neutral-900" },
  { domain: "vercel.com", company: "Vercel Platform", category: "DevTools", overall_score: 65, dimension_scores: { D1: 50, D2: 88, D3: 88, D4: 64, D5: 52, D6: 32 }, avatar: "bg-neutral-900" },
  { domain: "anthropic.com", company: "Anthropic PBC", category: "AI / ML", overall_score: 44, dimension_scores: { D1: 26, D2: 30, D3: 88, D4: 45, D5: 52, D6: 18 }, avatar: "bg-neutral-800" },
  { domain: "linear.app", company: "Linear Orbit, Inc.", category: "DevTools", overall_score: 59, dimension_scores: { D1: 26, D2: 88, D3: 88, D4: 45, D5: 64, D6: 27 }, avatar: "bg-neutral-900" },
  { domain: "supabase.com", company: "Supabase Inc.", category: "DevTools", overall_score: 52, dimension_scores: { D1: 41, D2: 30, D3: 88, D4: 64, D5: 52, D6: 32 }, avatar: "bg-emerald-700" },
  { domain: "hubspot.com", company: "HubSpot, Inc.", category: "Other", overall_score: 48, dimension_scores: { D1: 35, D2: 30, D3: 88, D4: 45, D5: 52, D6: 32 }, avatar: "bg-orange-500" },
  { domain: "shopify.com", company: "Shopify Inc.", category: "FinTech", overall_score: 67, dimension_scores: { D1: 35, D2: 88, D3: 88, D4: 64, D5: 75, D6: 32 }, avatar: "bg-emerald-600" },
  { domain: "stripe.com", company: "Stripe, Inc.", category: "FinTech", overall_score: 49, dimension_scores: { D1: 35, D2: 30, D3: 88, D4: 64, D5: 52, D6: 18 }, avatar: "bg-neutral-800" },
  { domain: "adobe.com", company: "Adobe Inc.", category: "Other", overall_score: 48, dimension_scores: { D1: 35, D2: 30, D3: 88, D4: 64, D5: 52, D6: 18 }, avatar: "bg-red-600" },
  { domain: "craigslist.org", company: "Craigslist Foundation", category: "Other", overall_score: 46, dimension_scores: { D1: 26, D2: 30, D3: 25, D4: 9, D5: 75, D6: 32 }, avatar: "bg-neutral-500" },
];

const CATEGORIES = ["DevTools", "FinTech", "AI / ML"] as const;

function statusOf(score: number) {
  if (score >= 70) return { label: "GEO Ready", cls: "bg-emerald-50 text-emerald-700" };
  if (score >= 50) return { label: "Developing", cls: "bg-amber-50 text-amber-700" };
  return { label: "Action Needed", cls: "bg-red-50 text-red-600" };
}

function dimColor(score: number) {
  if (score >= 70) return "text-neutral-700";
  if (score >= 50) return "text-amber-600";
  return "text-red-500";
}

export default function BenchmarkPage() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<string | null>(null);
  const [sort, setSort] = useState<"score" | "domain">("score");

  const rows = useMemo(() => {
    const q = query.trim().toLowerCase();
    return [...ROWS]
      .filter((r) => !q || r.domain.includes(q) || r.company.toLowerCase().includes(q))
      .filter((r) => !category || r.category === category)
      .sort((a, b) => (sort === "domain" ? a.domain.localeCompare(b.domain) : b.overall_score - a.overall_score));
  }, [query, category, sort]);

  const exportCsv = () => {
    const header = ["rank", "domain", "company", "overall", "d1", "d2", "d3", "d4", "d5", "d6", "status"];
    const lines = rows.map((r, i) =>
      [
        i + 1,
        r.domain,
        r.company,
        r.overall_score,
        r.dimension_scores.D1,
        r.dimension_scores.D2,
        r.dimension_scores.D3,
        r.dimension_scores.D4,
        r.dimension_scores.D5,
        r.dimension_scores.D6,
        statusOf(r.overall_score).label,
      ].join(",")
    );
    const blob = new Blob([[header.join(","), ...lines].join("\n")], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "geoready-benchmark-index.csv";
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-[calc(100vh-56px)] bg-[#F7F6F1] text-neutral-900">
      <div className="mx-auto max-w-[1280px] px-4 pt-8 pb-10 sm:px-6">
        <p className="mb-3 text-[11px] font-medium tracking-[0.16em] text-neutral-400 uppercase">
          <span className="mr-1.5 inline-block h-1.5 w-1.5 rounded-full bg-emerald-500" />
          Index edition Q2 · 90 retrieval checks · Updated hourly
        </p>

        <div className="mb-8 flex flex-col gap-5 lg:flex-row lg:items-start lg:justify-between">
          <div className="max-w-2xl">
            <h1 className="text-3xl font-semibold tracking-tight">
              AI Discoverability Benchmark Index
            </h1>
            <p className="mt-2 text-sm leading-relaxed text-neutral-500">
              Comparative visibility index assessing enterprise web properties across 90 generative
              engine optimization (GEO) criteria, bot accessibility rules, knowledge graph entity
              anchors, and citation fidelity.
            </p>
          </div>
          <div className="flex shrink-0 gap-2">
            <button
              type="button"
              onClick={exportCsv}
              className="inline-flex items-center gap-1.5 rounded-lg border border-black/10 bg-white px-3 py-2 text-[13px] font-medium text-neutral-800 hover:bg-neutral-50"
            >
              <Download size={14} />
              Export CSV
            </button>
            <Link
              href="/#audit"
              className="inline-flex items-center gap-1.5 rounded-lg bg-neutral-950 px-3 py-2 text-[13px] font-medium text-white hover:bg-neutral-800"
            >
              <Plus size={14} />
              Add Custom Domain
            </Link>
          </div>
        </div>

        <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-1 flex-wrap items-center gap-2">
            <div className="relative">
              <Search size={14} className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-neutral-400" />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Filter by domain..."
                className="h-9 w-56 rounded-lg border border-black/10 bg-white pr-3 pl-9 text-[13px] placeholder:text-neutral-400 focus:outline-none"
              />
            </div>
            <div className="mx-1 hidden h-5 w-px bg-black/10 sm:block" />
            {CATEGORIES.map((c) => (
              <button
                key={c}
                type="button"
                onClick={() => setCategory((prev) => (prev === c ? null : c))}
                className={cn(
                  "rounded-full px-3 py-1.5 text-[12px] font-medium",
                  category === c
                    ? "bg-neutral-900 text-white"
                    : "text-neutral-500 hover:bg-neutral-100 hover:text-neutral-800"
                )}
              >
                {c}
              </button>
            ))}
          </div>
          <div className="flex flex-wrap items-center gap-3 text-[11px] text-neutral-500">
            <span className="inline-flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> GEO Ready ≥70
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500" /> Developing 50–69
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-red-500" /> Action Needed &lt;50
            </span>
            <select
              value={sort}
              onChange={(e) => setSort(e.target.value as "score" | "domain")}
              className="h-9 rounded-lg border border-black/10 bg-white px-2 text-[12px] text-neutral-700 focus:outline-none"
            >
              <option value="score">Sort: Overall Score</option>
              <option value="domain">Sort: Domain</option>
            </select>
          </div>
        </div>

        <div className="overflow-x-auto rounded-2xl border border-black/[0.06] bg-white">
          <table className="w-full min-w-[960px] text-left text-[13px]">
            <thead>
              <tr className="border-b border-black/[0.06] text-[11px] font-medium tracking-[0.08em] text-neutral-400 uppercase">
                <th className="px-4 py-3 font-medium">Rank</th>
                <th className="px-3 py-3 font-medium">Property</th>
                <th className="px-3 py-3 font-medium">Overall Score</th>
                <th className="px-2 py-3 font-medium">D1 Crawl</th>
                <th className="px-2 py-3 font-medium">D2 Content</th>
                <th className="px-2 py-3 font-medium">D3 Entity</th>
                <th className="px-2 py-3 font-medium">D4 Schema</th>
                <th className="px-2 py-3 font-medium">D5 Auth</th>
                <th className="px-2 py-3 font-medium">D6 Tech</th>
                <th className="px-3 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Actions</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => {
                const st = statusOf(r.overall_score);
                const scoreCls =
                  r.overall_score >= 70
                    ? "bg-emerald-50 text-emerald-700"
                    : r.overall_score >= 50
                      ? "bg-amber-50 text-amber-700"
                      : "bg-red-50 text-red-600";
                return (
                  <tr key={r.domain} className="border-b border-black/[0.04] last:border-0 hover:bg-neutral-50/80">
                    <td className="px-4 py-3.5 font-mono text-[12px] text-neutral-400">
                      #{String(i + 1).padStart(2, "0")}
                    </td>
                    <td className="px-3 py-3.5">
                      <div className="flex items-center gap-2.5">
                        <span
                          className={cn(
                            "flex h-7 w-7 items-center justify-center rounded-md text-[11px] font-semibold text-white",
                            r.avatar
                          )}
                        >
                          {r.domain.charAt(0).toUpperCase()}
                        </span>
                        <div>
                          <p className="font-medium text-neutral-900">{r.domain}</p>
                          <p className="text-[11px] text-neutral-400">{r.company}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-3 py-3.5">
                      <span className={cn("rounded-md px-2 py-0.5 font-mono text-[12px] font-medium", scoreCls)}>
                        {r.overall_score} /100
                      </span>
                    </td>
                    {(["D1", "D2", "D3", "D4", "D5", "D6"] as const).map((id) => (
                      <td key={id} className={cn("px-2 py-3.5 font-mono text-[13px]", dimColor(r.dimension_scores[id]))}>
                        {r.dimension_scores[id]}
                      </td>
                    ))}
                    <td className="px-3 py-3.5">
                      <span className={cn("inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium", st.cls)}>
                        <span
                          className={cn(
                            "h-1.5 w-1.5 rounded-full",
                            r.overall_score >= 70 ? "bg-emerald-500" : r.overall_score >= 50 ? "bg-amber-500" : "bg-red-500"
                          )}
                        />
                        {st.label}
                      </span>
                    </td>
                    <td className="px-4 py-3.5">
                      <Link
                        href={`/?url=${encodeURIComponent(r.domain)}#audit`}
                        className="text-[13px] text-neutral-500 hover:text-neutral-900"
                      >
                        View Audit
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="mt-6 grid gap-4 text-[12px] text-neutral-500 sm:grid-cols-2 lg:grid-cols-6">
          {[
            ["D1 · Crawlability", "LLM crawler directives"],
            ["D2 · Content", "Semantic factual density"],
            ["D3 · Entity", "Wikidata & KG anchors"],
            ["D4 · Schema", "JSON-LD validity rate"],
            ["D5 · Authority", "AI corpus co-citations"],
            ["D6 · Tech", "SSR payload accessibility"],
          ].map(([title, sub]) => (
            <div key={title}>
              <p className="font-medium text-neutral-800">{title}</p>
              <p>{sub}</p>
            </div>
          ))}
        </div>
      </div>

      <SiteFooter />
    </div>
  );
}
