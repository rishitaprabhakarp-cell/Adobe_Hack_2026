"use client";

import { Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams, useRouter } from "next/navigation";
import {
  ArrowUpRight,
  Download,
  RefreshCw,
  Share2,
} from "lucide-react";
import AuditForm from "@/components/AuditForm";
import SiteFooter from "@/components/SiteFooter";
import FindingCard, { type Finding } from "@/components/FindingCard";
import { saveLastReport, startAuditFlow } from "@/lib/audit-flow";
import { getAuditStatus, listUserSites, type SiteAudit } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import {
  cn,
  relativeTime,
  scoreColor,
  scoreLabel,
} from "@/lib/utils";

type Severity = "CRITICAL" | "HIGH" | "MEDIUM" | "LOW" | "ALL";

const SEV_ORDER: Record<string, number> = { CRITICAL: 0, HIGH: 1, MEDIUM: 2, LOW: 3 };

const ENGINE_META: Record<string, { label: string; sub: string }> = {
  ChatGPT: { label: "ChatGPT", sub: "GPT-4o Retrieval" },
  Claude: { label: "Claude", sub: "Anthropic retrieval" },
  Perplexity: { label: "Perplexity", sub: "Source Citation" },
  Gemini: { label: "Gemini", sub: "Google Overviews" },
  "Google AI Overviews": { label: "Google", sub: "Search Overviews" },
  "Bing Copilot": { label: "Copilot", sub: "MS Index Grounding" },
};

const ENGINE_ORDER = [
  "ChatGPT",
  "Claude",
  "Perplexity",
  "Gemini",
  "Google AI Overviews",
  "Bing Copilot",
];

function ReportContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { user, ready } = useAuth();
  const jobId = searchParams.get("job") || "";
  const decoded = (searchParams.get("domain") || "").replace(/^www\./, "");

  const [report, setReport] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(Boolean(jobId));
  const [error, setError] = useState("");
  const [activeFilter, setActiveFilter] = useState<Severity>("ALL");
  const [rerunning, setRerunning] = useState(false);
  const [shareNote, setShareNote] = useState("");
  const [sites, setSites] = useState<SiteAudit[]>([]);

  useEffect(() => {
    if (ready && !user) {
      router.replace(`/login?next=${encodeURIComponent("/report")}`);
    }
  }, [ready, user, router]);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    listUserSites()
      .then((rows) => {
        if (!cancelled) setSites(rows);
      })
      .catch(() => {
        if (!cancelled) setSites([]);
      });
    return () => {
      cancelled = true;
    };
  }, [user, jobId]);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      if (!jobId) {
        setReport(null);
        setLoading(false);
        return;
      }
      try {
        const state = await getAuditStatus(jobId);
        if (cancelled) return;
        if (state.status === "done" && state.report) {
          setReport(state.report);
          try {
            const { saveAuditToSupabase } = await import("@/lib/audits-db");
            const summary = (state.report.summary as Record<string, number> | undefined) || {};
            await saveAuditToSupabase({
              job_id: jobId,
              domain: decoded || String(state.report.site || ""),
              url: state.url,
              status: "done",
              score: (state.report.overall_score as number) ?? null,
              findings: summary.total_findings ?? null,
              report: state.report,
            });
          } catch {
            /* listing still works from the live job */
          }
        } else if (state.status === "error") {
          setError(state.error || "Audit failed.");
        } else {
          setError("Report not ready. Please wait.");
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load report.");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [jobId]);

  useEffect(() => {
    if (!jobId) return;
    saveLastReport(jobId, decoded);
  }, [decoded, jobId]);

  const site = ((report?.site as string) || decoded || "example.com").replace(/^www\./, "");
  const score = (report?.overall_score as number) || 0;
  const summary = (report?.summary as Record<string, number>) || {};
  const dimScores =
    (report?.dimension_scores as Array<{
      id: string;
      name: string;
      score: number;
      finding_prefixes?: string[];
    }>) || [];
  const engineScores = (report?.engine_scores as Record<string, number>) || {};
  const findings = ((report?.findings as Finding[]) || []).slice().sort(
    (a, b) =>
      (SEV_ORDER[a.severity?.toUpperCase()] ?? 9) -
      (SEV_ORDER[b.severity?.toUpperCase()] ?? 9)
  );
  const projected = report?.projected_score as Record<string, number> | undefined;
  const citability = report?.citability_coverage as Record<string, unknown> | undefined;
  const benchmark = report?.vertical_benchmark as Record<string, unknown> | undefined;

  const failCounts = useMemo(() => {
    const map: Record<string, number> = {};
    for (const d of dimScores) {
      const prefixes = d.finding_prefixes || [];
      map[d.id] = findings.filter((f) =>
        prefixes.some((p) => f.id.toUpperCase().startsWith(p.toUpperCase()))
      ).length;
    }
    return map;
  }, [dimScores, findings]);

  const robotsBlocked = findings.some((f) =>
    /robot|disallow|crawler|gptbot|claudebot/i.test(`${f.title} ${f.evidence}`)
  );

  const filteredFindings = (
    activeFilter === "ALL"
      ? findings
      : findings.filter((f) => f.severity?.toUpperCase() === activeFilter)
  );

  const SEV_TABS: Array<{ label: string; key: Severity; count: number }> = [
    { label: "All", key: "ALL", count: summary.total_findings || findings.length },
    { label: "Critical", key: "CRITICAL", count: summary.critical || 0 },
    { label: "High", key: "HIGH", count: summary.high || 0 },
    { label: "Medium", key: "MEDIUM", count: summary.medium || 0 },
    { label: "Low", key: "LOW", count: summary.low || 0 },
  ];

  const engines = ENGINE_ORDER.filter((k) => k in engineScores).concat(
    Object.keys(engineScores).filter((k) => !ENGINE_ORDER.includes(k))
  );

  const handleShare = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href);
      setShareNote("Copied");
      setTimeout(() => setShareNote(""), 1400);
    } catch {
      /* ignore */
    }
  };

  const handleRerun = async () => {
    setRerunning(true);
    try {
      await startAuditFlow(`https://${site}`, {
        authenticated: Boolean(user),
        router,
      });
    } catch {
      setRerunning(false);
    }
  };

  if (!ready || !user) {
    return (
      <div className="flex min-h-[calc(100vh-56px)] items-center justify-center bg-[#F7F6F1]">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-neutral-900 border-t-transparent" />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="flex min-h-[calc(100vh-56px)] items-center justify-center bg-[#F7F6F1]">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-neutral-900 border-t-transparent" />
          <p className="text-sm text-neutral-500">Loading report…</p>
        </div>
      </div>
    );
  }

  if (!jobId) {
    const firstName = (user.name || "").split(" ")[0];
    return (
      <div className="flex min-h-[calc(100vh-56px)] flex-col bg-[#F7F6F1]">
        <div className="mx-auto w-full max-w-[960px] flex-1 px-4 pt-10 pb-16 sm:px-6 sm:pt-14">
          <p className="text-[11px] font-medium tracking-[0.18em] text-neutral-400 uppercase">
            Diagnostic workspace
          </p>
          <h1 className="mt-2 font-serif text-4xl tracking-tight text-neutral-950 sm:text-[2.75rem]">
            Live report
          </h1>
          <p className="mt-3 max-w-xl text-[15px] leading-relaxed text-neutral-500">
            {firstName ? `Welcome back, ${firstName}. ` : "Welcome. "}
            Audit as many sites as you need. Each domain stays on your account — open one below or start another.
          </p>

          <div className="mt-10 rounded-2xl border border-black/[0.08] bg-white p-6 shadow-[0_20px_50px_-36px_rgba(0,0,0,0.28)] sm:p-8">
            <div className="mb-5 flex items-start justify-between gap-4">
              <div>
                <p className="text-[11px] font-medium tracking-[0.14em] text-neutral-400 uppercase">
                  New site
                </p>
                <h2 className="mt-1 text-lg font-semibold tracking-tight text-neutral-950">
                  Audit a domain
                </h2>
                <p className="mt-1 text-sm text-neutral-500">
                  Add another website. Rerunning an existing domain replaces its latest report.
                </p>
              </div>
            </div>
            <AuditForm variant="workspace" />
          </div>

          {sites.length > 0 && (
            <div className="mt-8">
              <p className="mb-3 text-[13px] text-neutral-400">Your sites</p>
              <div className="overflow-hidden rounded-2xl border border-black/[0.08] bg-white">
                {sites.map((s, i) => (
                  <Link
                    key={s.job_id}
                    href={
                      s.status === "done"
                        ? `/report?job=${s.job_id}&domain=${encodeURIComponent(s.domain)}`
                        : `/loading?job=${s.job_id}&url=${encodeURIComponent(s.url || s.domain)}`
                    }
                    className={cn(
                      "flex items-center justify-between gap-4 px-5 py-4 hover:bg-neutral-50",
                      i > 0 && "border-t border-black/[0.05]"
                    )}
                  >
                    <div>
                      <p className="text-sm font-medium text-neutral-900">{s.domain}</p>
                      <p className="mt-0.5 text-[12px] text-neutral-400">
                        {s.status === "done"
                          ? s.created_at
                            ? `Updated ${relativeTime(s.created_at)}`
                            : "Ready"
                          : s.status === "error"
                            ? "Failed"
                            : "Running"}
                      </p>
                    </div>
                    <p className="font-serif text-2xl text-neutral-950">
                      {s.status === "done" && s.score != null ? s.score : "—"}
                    </p>
                  </Link>
                ))}
              </div>
            </div>
          )}

          <div className="mt-6 grid overflow-hidden rounded-2xl border border-black/[0.08] bg-white sm:grid-cols-3">
            {[
              ["90 checks", "Crawl, schema, entity, and extractability probes in a single pass."],
              ["5 engines", "ChatGPT, Claude, Perplexity, Gemini, and Copilot visibility."],
              ["~90 seconds", "Parallel skill scripts. Findings open in this workspace."],
            ].map(([title, body], i) => (
              <div
                key={title}
                className={cn(
                  "px-5 py-5",
                  i > 0 && "border-t border-black/[0.06] sm:border-t-0 sm:border-l"
                )}
              >
                <p className="text-sm font-semibold text-neutral-900">{title}</p>
                <p className="mt-1.5 text-[13px] leading-relaxed text-neutral-500">{body}</p>
              </div>
            ))}
          </div>
        </div>
        <SiteFooter />
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="flex min-h-[calc(100vh-56px)] flex-col bg-[#F7F6F1]">
        <div className="mx-auto flex w-full max-w-[960px] flex-1 flex-col justify-center px-4 py-16 sm:px-6">
          <p className="text-[11px] font-medium tracking-[0.18em] text-neutral-400 uppercase">
            Diagnostic workspace
          </p>
          <h1 className="mt-2 font-serif text-4xl tracking-tight text-neutral-950">Live report</h1>
          <p className="mt-3 max-w-md text-sm leading-relaxed text-neutral-500">
            {error || "This report is no longer available. Run a new audit to generate a diagnostic."}
          </p>
          <div className="mt-8 rounded-2xl border border-black/[0.08] bg-white p-6 shadow-[0_20px_50px_-36px_rgba(0,0,0,0.28)] sm:p-8">
            <p className="mb-4 text-[11px] font-medium tracking-[0.14em] text-neutral-400 uppercase">
              New audit
            </p>
            <AuditForm variant="workspace" initialUrl={decoded} />
          </div>
        </div>
        <SiteFooter />
      </div>
    );
  }

  const citabilityPct = Number(citability?.pct ?? 0);
  const hydrationPct = Math.max(0, 100 - citabilityPct);
  const highImpact = (summary.critical || 0) + (summary.high || 0);
  const issueCount = summary.total_findings || findings.length;

  return (
    <div className="min-h-screen bg-[#F7F6F1] text-neutral-900 print:bg-white">
      <div className="mx-auto max-w-[1120px] px-4 pt-10 pb-16 sm:px-6">
        <div className="mb-10 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-[12px] text-neutral-400">
              <Link href="/report" className="hover:text-neutral-700">
                All sites
              </Link>
              <span className="mx-1.5 text-neutral-300">/</span> {site}
            </p>
            <h1 className="mt-2 font-serif text-4xl tracking-tight text-neutral-950">{site}</h1>
            <p className="mt-2 text-sm text-neutral-500">
              Audited {relativeTime(report.audited_at as string)}
              <span className="mx-2 text-neutral-300">·</span>
              <a
                href={`https://${site}`}
                target="_blank"
                rel="noreferrer"
                className="text-neutral-600 hover:text-neutral-900"
              >
                Open site
              </a>
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-2 print:hidden">
            <button
              type="button"
              onClick={handleRerun}
              disabled={rerunning}
              className="inline-flex items-center gap-1.5 rounded-full border border-black/10 bg-white px-3.5 py-1.5 text-[13px] text-neutral-600 hover:text-neutral-900"
            >
              <RefreshCw size={13} className={rerunning ? "animate-spin" : ""} />
              Rerun
            </button>
            <button
              type="button"
              onClick={handleShare}
              className="inline-flex items-center gap-1.5 rounded-full border border-black/10 bg-white px-3.5 py-1.5 text-[13px] text-neutral-600 hover:text-neutral-900"
            >
              <Share2 size={13} />
              {shareNote || "Share"}
            </button>
            <button
              type="button"
              onClick={() => window.print()}
              className="inline-flex items-center gap-1.5 rounded-full bg-neutral-950 px-3.5 py-1.5 text-[13px] font-medium text-white hover:bg-neutral-800"
            >
              <Download size={13} />
              Export
            </button>
          </div>
        </div>

        <div className="mb-10 grid gap-8 border-y border-black/[0.06] py-8 lg:grid-cols-[220px_1fr] lg:items-center">
          <div>
            <p className="font-serif text-6xl leading-none tracking-tight text-neutral-950">{score}</p>
            <p className="mt-2 text-sm text-neutral-500">{scoreLabel(score)}</p>
            <p className="mt-1 text-[13px] text-neutral-400">
              {issueCount} {issueCount === 1 ? "issue" : "issues"} to review
            </p>
          </div>
          <div id="engines" className="scroll-mt-20">
            <p className="mb-4 text-[13px] text-neutral-400">How engines see this site</p>
            <div className="grid grid-cols-2 gap-x-8 gap-y-4 sm:grid-cols-3 lg:grid-cols-5">
              {engines.map((key) => {
                const val = engineScores[key];
                const meta = ENGINE_META[key] || { label: key, sub: "" };
                const blocked = robotsBlocked && val < 35;
                return (
                  <div key={key}>
                    <p className="text-[13px] text-neutral-600">{meta.label}</p>
                    <p className={cn("mt-0.5 text-lg tabular-nums", scoreColor(val, "light"))}>{val}%</p>
                    {blocked && <p className="mt-0.5 text-[11px] text-red-500">Blocked for crawlers</p>}
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        <div className="grid items-start gap-10 lg:grid-cols-[200px_1fr]">
          <aside id="dimensions" className="lg:sticky lg:top-24">
            {sites.length > 0 && (
              <div className="mb-8">
                <p className="mb-3 text-[13px] text-neutral-400">Sites</p>
                <div className="space-y-1">
                  {sites.map((s) => {
                    const active = s.job_id === jobId || s.domain === site;
                    return (
                      <Link
                        key={s.job_id}
                        href={
                          s.status === "done"
                            ? `/report?job=${s.job_id}&domain=${encodeURIComponent(s.domain)}`
                            : `/loading?job=${s.job_id}&url=${encodeURIComponent(s.url || s.domain)}`
                        }
                        className={cn(
                          "flex items-baseline justify-between gap-3 rounded-lg px-2 py-1.5 text-[13px]",
                          active ? "bg-white text-neutral-950" : "text-neutral-500 hover:text-neutral-800"
                        )}
                      >
                        <span className="truncate">{s.domain}</span>
                        <span className="tabular-nums text-neutral-400">
                          {s.status === "done" && s.score != null ? s.score : "…"}
                        </span>
                      </Link>
                    );
                  })}
                </div>
                <Link
                  href="/report#audit"
                  className="mt-2 inline-block px-2 text-[12px] text-neutral-400 hover:text-neutral-800"
                >
                  + New site
                </Link>
              </div>
            )}
            <p className="mb-4 text-[13px] text-neutral-400">Breakdown</p>
            <div className="space-y-4">
              {dimScores.map((d) => {
                const fails = failCounts[d.id] || 0;
                return (
                  <div key={d.id}>
                    <div className="mb-1 flex items-baseline justify-between gap-2">
                      <span className="text-[13px] text-neutral-700">{d.name}</span>
                      <span className="text-[13px] tabular-nums text-neutral-500">{d.score}</span>
                    </div>
                    <div className="h-[2px] overflow-hidden rounded-full bg-black/[0.07]">
                      <div
                        className="h-full rounded-full bg-neutral-800"
                        style={{ width: `${d.score}%`, opacity: d.score >= 70 ? 1 : d.score >= 50 ? 0.55 : 0.28 }}
                      />
                    </div>
                    {fails > 0 && (
                      <p className="mt-1 text-[11px] text-neutral-400">
                        {fails} open
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          </aside>

          <div className="min-w-0">
            {projected && (
              <div className="mb-8 flex flex-col gap-2 sm:flex-row sm:items-baseline sm:justify-between">
                <p className="text-sm leading-relaxed text-neutral-600">
                  Fixing {projected.fixes_required} high-impact issues could lift this score from{" "}
                  {projected.current_overall ?? score} to {projected.projected_overall}
                  <span className="text-neutral-400"> (+{projected.score_lift})</span>.
                </p>
                <button
                  type="button"
                  onClick={() => {
                    setActiveFilter("CRITICAL");
                    document.getElementById("findings")?.scrollIntoView({ behavior: "smooth" });
                  }}
                  className="inline-flex shrink-0 items-center gap-1 text-[13px] text-neutral-700 hover:text-neutral-950"
                >
                  View {highImpact} fixes
                  <ArrowUpRight size={14} />
                </button>
              </div>
            )}

            {(citability || benchmark) && (
              <div className="mb-10 grid gap-6 sm:grid-cols-2">
                {citability && (
                  <div>
                    <p className="text-[13px] text-neutral-400">Quotable copy</p>
                    <p className="mt-1 font-serif text-3xl text-neutral-950">{citabilityPct}%</p>
                    <p className="mt-1 text-[13px] leading-relaxed text-neutral-500">
                      of core features can be extracted by language models
                      {typeof citability.citeable_passages === "number" && (
                        <> ({citability.citeable_passages as number}/{citability.total_passages as number} passages)</>
                      )}
                      . {hydrationPct}% is hidden behind client rendering.
                    </p>
                  </div>
                )}
                {benchmark && (
                  <div>
                    <p className="text-[13px] text-neutral-400">Among peers</p>
                    <p className="mt-1 font-serif text-3xl text-neutral-950">
                      {benchmark.estimated_percentile as number}
                      <span className="text-xl text-neutral-400">th</span>
                    </p>
                    <p className="mt-1 text-[13px] leading-relaxed text-neutral-500">
                      percentile vs a median of {benchmark.benchmark_median as number}. {benchmark.overall_position as string}.
                    </p>
                  </div>
                )}
              </div>
            )}

            <div id="findings" className="scroll-mt-24">
              <div className="mb-2 flex flex-col gap-3 border-b border-black/[0.07] pb-3 sm:flex-row sm:items-end sm:justify-between">
                <div>
                  <h2 className="text-[13px] font-medium tracking-[0.12em] text-neutral-500 uppercase">
                    Findings
                  </h2>
                  <p className="mt-1 text-sm text-neutral-500">
                    {filteredFindings.length} ranked by citation impact
                  </p>
                </div>
                <div className="flex flex-wrap gap-x-3 gap-y-1 text-[13px]">
                  {SEV_TABS.map((tab) =>
                    tab.count > 0 || tab.key === "ALL" ? (
                      <button
                        key={tab.key}
                        type="button"
                        onClick={() => setActiveFilter(tab.key)}
                        className={cn(
                          "transition-colors",
                          activeFilter === tab.key
                            ? "text-neutral-950"
                            : "text-neutral-400 hover:text-neutral-700"
                        )}
                      >
                        {tab.label}
                        <span className="ml-1 text-neutral-400">{tab.count}</span>
                      </button>
                    ) : null
                  )}
                </div>
              </div>

              <div>
                {filteredFindings.map((finding, i) => (
                  <FindingCard
                    key={finding.id}
                    finding={finding}
                    index={i}
                    defaultOpen={false}
                  />
                ))}
                {filteredFindings.length === 0 && (
                  <p className="py-10 text-sm text-neutral-500">No findings in this filter.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ReportPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[calc(100vh-56px)] items-center justify-center bg-[#F7F6F1]">
          <p className="text-sm text-neutral-500">Loading report…</p>
        </div>
      }
    >
      <ReportContent />
    </Suspense>
  );
}
