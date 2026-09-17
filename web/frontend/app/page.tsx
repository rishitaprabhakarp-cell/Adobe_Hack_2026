"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowRight } from "lucide-react";
import AuditForm from "@/components/AuditForm";
import SiteFooter from "@/components/SiteFooter";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

const TRUST_LOGOS = ["Stripe", "Plaid", "Square", "Linear", "OpenAI", "Anthropic"];

const SNIPPET = `{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "YourBrand",
  "sameAs": [
    "https://www.wikidata.org/wiki/Q…"
  ]
}`;

export default function LandingPage() {
  const router = useRouter();
  const { user, ready } = useAuth();
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    if (ready && user) router.replace("/report");
  }, [ready, user, router]);

  const copySnippet = async () => {
    try {
      await navigator.clipboard.writeText(SNIPPET);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      setCopied(false);
    }
  };

  if (!ready || user) {
    return (
      <div className="flex min-h-[calc(100vh-56px)] items-center justify-center bg-cream-50">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-neutral-900 border-t-transparent" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-cream-50 text-ink-950">
      <section className="px-5 pt-16 pb-8 sm:px-8 sm:pt-24">
        <div className="mx-auto max-w-3xl text-center">
          <Link
            href="#methodology"
            className="mb-8 inline-flex items-center gap-2 rounded-full border border-black/10 bg-white/70 px-3.5 py-1.5 text-[11px] tracking-wide text-neutral-500 transition-colors hover:border-black/15 hover:text-neutral-800"
          >
            <span className="h-1.5 w-1.5 rounded-full bg-neutral-900" />
            Generative Engine Optimization · GEO Codex 2025
            <span className="text-neutral-400">·</span>
            <span className="inline-flex items-center gap-0.5 font-medium text-neutral-800">
              Read Report <ArrowRight size={11} />
            </span>
          </Link>

          <h1 className="font-serif text-[3.25rem] leading-[1.05] tracking-tight text-neutral-950 sm:text-7xl">
            Is your brand
            <br />
            <em className="italic">invisible to AI?</em>
          </h1>

          <p className="mx-auto mt-6 max-w-xl text-[15px] leading-relaxed text-neutral-500">
            Search is shifting to conversational synthesis. GEOReady audits your
            digital footprint across ChatGPT, Perplexity, and Claude to safeguard
            organic discovery.
          </p>

          <div className="mt-10">
            <Suspense fallback={<AuditForm />}>
              <HomeAuditForm />
            </Suspense>
          </div>

          <div className="mt-6 flex flex-wrap items-center justify-center gap-x-8 gap-y-2 text-[11px] tracking-wide text-neutral-400 uppercase">
            <span>GEO synthesis infrastructure</span>
            <span>AI citation engines</span>
            <span>Audit execution in 90s</span>
          </div>
        </div>
      </section>

      <section className="px-5 pb-20 sm:px-8">
        <div className="mx-auto max-w-4xl rounded-3xl border border-black/10 bg-white p-4 shadow-[0_20px_60px_-24px_rgba(0,0,0,0.12)] sm:p-6">
          <div className="mb-4 flex items-center justify-between px-1">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-emerald-500" />
              <span className="text-sm font-medium text-neutral-800">Live snapshot</span>
            </div>
            <span className="text-[11px] text-neutral-400">90 checks</span>
          </div>

          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            <Metric label="Citation index" value="89" hint="Perplexity" bar={89} barClass="bg-neutral-800" />
            <Metric label="Brand share" value="94.2%" hint="Share of ChatGPT share" />
            <Metric label="Entity score" value="92/100" hint="Wikidata + sameAs" />
            <Metric label="LLM accessibility" value="100%" hint="GPTBot · ClaudeBot" />
          </div>

          <div className="mt-3 flex flex-col gap-3 rounded-2xl border border-black/10 bg-cream-50 p-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="min-w-0">
              <p className="text-[10px] font-medium tracking-[0.14em] text-neutral-400 uppercase">
                Prompt
              </p>
              <p className="mt-1 truncate text-sm text-neutral-800">
                What is the #1 fintech for global subscriptions?
              </p>
            </div>
            <span className="shrink-0 rounded-full bg-neutral-100 px-2.5 py-1 text-[10px] font-medium tracking-wide text-neutral-700 uppercase">
              Citation
            </span>
          </div>

          <div className="mt-3 grid gap-4 rounded-2xl border border-black/10 bg-cream-50 p-4 sm:grid-cols-[1fr_auto] sm:items-end">
            <div>
              <p className="mb-3 text-[11px] font-medium text-neutral-500">Engine Citation Mix</p>
              <EngineBar name="ChatGPT" width="72%" color="#111111" />
              <EngineBar name="Claude" width="54%" color="#525252" />
              <EngineBar name="Perplexity" width="38%" color="#A3A3A3" />
            </div>
            <p className="text-[11px] text-neutral-400 sm:text-right">
              AI answer synthesized 2.4s
              <br />
              3 sources cited
            </p>
          </div>
        </div>
      </section>

      <section className="border-y border-black/10 py-10">
        <p className="mb-6 text-center text-[10px] font-medium tracking-[0.22em] text-neutral-400 uppercase">
          Trusted by financial leaders optimizing for generative discovery
        </p>
        <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-center gap-x-10 gap-y-3 px-6">
          {TRUST_LOGOS.map((name) => (
            <span key={name} className="text-lg font-semibold tracking-tight text-neutral-300">
              {name}
            </span>
          ))}
        </div>
      </section>

      <section id="methodology" className="scroll-mt-20 px-5 py-24 sm:px-8">
        <div className="mx-auto grid max-w-6xl items-start gap-16 lg:grid-cols-[1.1fr_0.9fr]">
          <div>
            <p className="mb-4 text-[11px] font-medium tracking-[0.2em] text-neutral-400 uppercase">
              Architecture · Methodology
            </p>
            <h2 className="font-serif text-4xl leading-tight text-neutral-950 sm:text-5xl">
              What is Generative Engine Optimization?
            </h2>
            <p className="mt-6 max-w-lg text-[15px] leading-relaxed text-neutral-500">
              Traditional SEO optimizes for ten-link result pages. GEO optimizes for
              citation probability, entity density, and structured semantic grounding
              inside LLMs — so ChatGPT, Perplexity, and Claude can find, trust, and
              quote your brand.
            </p>
          </div>

          <div className="space-y-4">
            <div className="overflow-hidden rounded-2xl border border-emerald-200/70 bg-emerald-50/70 p-5">
              <p className="mb-3 text-[11px] font-medium text-emerald-800/70">
                Citation probability · 90-day lift
              </p>
              <Sparkline />
            </div>

            <div className="rounded-2xl border border-black/10 bg-white p-5 shadow-[0_8px_30px_-18px_rgba(0,0,0,0.12)]">
              <div className="mb-3 flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-sm font-semibold text-neutral-900">
                    Prioritized Code Patches
                  </h3>
                  <p className="mt-1 text-xs leading-relaxed text-neutral-500">
                    Every finding ships with copy-ready Schema, speakable markup, and
                    entity fixes — not just a checklist.
                  </p>
                </div>
                <div className="flex shrink-0 gap-2">
                  <span className="text-[10px] tracking-wide text-neutral-400 uppercase">
                    View snippet
                  </span>
                  <button
                    type="button"
                    onClick={copySnippet}
                    className="text-[10px] font-medium tracking-wide text-neutral-700 uppercase hover:text-neutral-950"
                  >
                    {copied ? "Copied" : "Copy snippet"}
                  </button>
                </div>
              </div>
              <pre className="overflow-x-auto rounded-xl bg-neutral-950 p-4 font-mono text-[11px] leading-relaxed text-emerald-300">
                {SNIPPET}
              </pre>
            </div>
          </div>
        </div>
      </section>

      <section className="px-5 pb-24 sm:px-8">
        <div className="mx-auto max-w-4xl text-center">
          <h2 className="font-serif text-4xl text-neutral-950 sm:text-5xl">
            Traditional Search vs. AI Synthesis
          </h2>
          <p className="mx-auto mt-4 max-w-lg text-[15px] text-neutral-500">
            Search has transformed from ten paginated blue links to authoritative,
            single-answer AI synthesis.
          </p>
        </div>

        <div className="mx-auto mt-12 grid max-w-5xl gap-4 md:grid-cols-2">
          <article className="rounded-2xl border border-black/10 bg-white p-7 text-left">
            <div className="mb-5 flex items-center justify-between text-[10px] tracking-[0.16em] text-neutral-400 uppercase">
              <span>1998 – 2022</span>
              <span>Then</span>
            </div>
            <h3 className="text-xl font-semibold tracking-tight text-neutral-900">
              Traditional Search (10 Blue Links)
            </h3>
            <p className="mt-3 text-sm leading-relaxed text-neutral-500">
              Rankings rewarded keywords, backlinks, and page authority. Users scanned
              ten blue links — and often never reached you.
            </p>
            <div className="mt-6 space-y-2">
              <Chip>Keyword density over evidence</Chip>
              <Chip>Ten-link ranking infrastructure</Chip>
              <Chip>Why it broke: engines skip through you</Chip>
            </div>
          </article>

          <article className="rounded-2xl border border-black/10 bg-neutral-50 p-7 text-left">
            <div className="mb-5 flex items-center justify-between text-[10px] tracking-[0.16em] text-neutral-400 uppercase">
              <span>The now</span>
              <span>2023 – present</span>
            </div>
            <h3 className="text-xl font-semibold tracking-tight text-neutral-900">
              AI Answer Engines (Direct Synthesis)
            </h3>
            <p className="mt-3 text-sm leading-relaxed text-neutral-500">
              ChatGPT, Perplexity, and Claude synthesize one answer. You are cited —
              or you are erased from the retrieval set.
            </p>
            <div className="mt-6 space-y-2">
              <Chip>Entity corroboration</Chip>
              <Chip>Citing authority</Chip>
              <Chip>Definition position in answer-span</Chip>
            </div>
          </article>
        </div>
      </section>

      <section className="px-5 pb-24 sm:px-8">
        <div className="mx-auto flex max-w-5xl flex-col items-start justify-between gap-8 rounded-3xl bg-neutral-950 px-8 py-12 sm:flex-row sm:items-center sm:px-12">
          <div className="min-w-0 flex-1">
            <h2 className="font-serif text-3xl leading-tight text-white sm:text-4xl">
              Inspect your AI discoverability profile.
            </h2>
            <p className="mt-3 text-sm text-neutral-400 sm:whitespace-nowrap">
              Uncover citation leaks, entity gaps, and crawl blocks before your competitors do.
            </p>
          </div>
          <div className="flex shrink-0 flex-col gap-3 sm:w-44">
            <Link
              href="#audit"
              className="inline-flex items-center justify-center rounded-xl bg-white px-5 py-2.5 text-sm font-medium text-neutral-950 hover:bg-neutral-200"
            >
              Run Free Audit
            </Link>
            <Link
              href="/benchmark"
              className="inline-flex items-center justify-center rounded-xl border border-white/20 px-5 py-2.5 text-sm text-neutral-300 hover:text-white"
            >
              View benchmark
            </Link>
          </div>
        </div>
      </section>

      <SiteFooter />
    </div>
  );
}

function HomeAuditForm() {
  const params = useSearchParams();
  const preset = params.get("url") || "";
  return <AuditForm key={preset} initialUrl={preset} />;
}

function Metric({
  label,
  value,
  hint,
  bar,
  barClass,
}: {
  label: string;
  value: string;
  hint: string;
  bar?: number;
  barClass?: string;
}) {
  return (
    <div className="rounded-2xl border border-black/10 bg-cream-50 p-4">
      <p className="text-[10px] font-medium tracking-[0.14em] text-neutral-400 uppercase">
        {label}
      </p>
      <p className="mt-2 font-serif text-3xl text-emerald-700">{value}</p>
      {bar != null && (
        <div className="mt-2 h-1 overflow-hidden rounded-full bg-black/10">
          <div className={cn("h-full rounded-full", barClass)} style={{ width: `${bar}%` }} />
        </div>
      )}
      <p className="mt-2 text-[10px] tracking-wide text-neutral-400 uppercase">{hint}</p>
    </div>
  );
}

function EngineBar({
  name,
  width,
  color,
}: {
  name: string;
  width: string;
  color: string;
}) {
  return (
    <div className="mb-2 flex items-center gap-3">
      <span className="w-20 text-[11px] text-neutral-500">{name}</span>
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-black/10">
        <div className="h-full rounded-full" style={{ width, background: color }} />
      </div>
    </div>
  );
}

function Sparkline() {
  return (
    <svg viewBox="0 0 360 120" className="h-28 w-full" aria-hidden="true">
      <defs>
        <linearGradient id="geo-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#34D399" stopOpacity="0.35" />
          <stop offset="100%" stopColor="#34D399" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path
        d="M0 92 C 40 88, 70 78, 100 70 S 160 62, 190 48 S 260 40, 300 22 L 360 14 L 360 120 L 0 120 Z"
        fill="url(#geo-fill)"
      />
      <path
        d="M0 92 C 40 88, 70 78, 100 70 S 160 62, 190 48 S 260 40, 300 22 L 360 14"
        fill="none"
        stroke="#059669"
        strokeWidth="2.2"
      />
    </svg>
  );
}

function Chip({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg bg-neutral-100 px-3 py-2 text-sm text-neutral-700">
      {children}
    </div>
  );
}
