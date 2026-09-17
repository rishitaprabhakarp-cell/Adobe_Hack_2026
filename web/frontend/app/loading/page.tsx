"use client";

import { Suspense, useEffect, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { formatDomain } from "@/lib/utils";
import { getAuditStatus } from "@/lib/api";

const SKILLS: Array<{ id: string; title: string; detail: string }> = [
  { id: "crawlability", title: "Crawler access", detail: "Checking robots.txt and whether GPTBot can enter." },
  { id: "render", title: "What bots see", detail: "Comparing raw HTML with the rendered page." },
  { id: "schema", title: "Structured data", detail: "Validating JSON-LD and entity markup." },
  { id: "entity", title: "Brand identity", detail: "Looking up Wikidata, sameAs, and knowledge-graph anchors." },
  { id: "content", title: "Extractable copy", detail: "Measuring how much of the page an LLM can quote." },
  { id: "eeeat", title: "Trust signals", detail: "Reviewing authorship, about pages, and credentials." },
  { id: "engagement", title: "Answer usefulness", detail: "Looking for definitions, steps, and citable facts." },
  { id: "rsl", title: "Licensing", detail: "Checking whether AI use is declared on the site." },
  { id: "opengraph", title: "Link previews", detail: "Reading Open Graph and social metadata." },
  { id: "technical", title: "Technical access", detail: "Timing server HTML and client-side hydration." },
];

type SkillStatus = "pending" | "running" | "done" | "error";

function LoadingContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const jobId = searchParams.get("job") || "";
  const urlParam = searchParams.get("url") || "";
  const domain = formatDomain(urlParam);

  const [progress, setProgress] = useState<Record<string, SkillStatus>>({});
  const [doneCount, setDoneCount] = useState(0);
  const [status, setStatus] = useState<"queued" | "running" | "done" | "error">("queued");
  const [errorMsg, setErrorMsg] = useState("");
  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const startedAt = useRef(Date.now());
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setElapsed(Math.round((Date.now() - startedAt.current) / 1000)), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    if (!jobId) {
      router.push("/report");
      return;
    }

    const poll = async () => {
      try {
        const state = await getAuditStatus(jobId);
        setProgress(state.progress || {});
        setDoneCount(state.done_count || 0);
        setStatus(state.status);

        if (state.status === "done") {
          if (intervalRef.current) clearInterval(intervalRef.current);
          try {
            const { saveAuditToSupabase } = await import("@/lib/audits-db");
            const report = state.report as Record<string, unknown> | undefined;
            const summary = (report?.summary as Record<string, number> | undefined) || {};
            await saveAuditToSupabase({
              job_id: jobId,
              domain,
              url: urlParam,
              status: "done",
              score: (report?.overall_score as number) ?? null,
              findings: summary.total_findings ?? null,
              report: report || null,
            });
          } catch {
            /* Redis still has the live job; list may catch up on next save */
          }
          setTimeout(() => {
            router.push(`/report?job=${jobId}&domain=${encodeURIComponent(domain)}`);
          }, 700);
        } else if (state.status === "error") {
          if (intervalRef.current) clearInterval(intervalRef.current);
          setErrorMsg(state.error || "Audit failed. Please try again.");
        }
      } catch (err) {
        setErrorMsg(err instanceof Error ? err.message : "Connection error");
        if (intervalRef.current) clearInterval(intervalRef.current);
      }
    };

    poll();
    intervalRef.current = setInterval(poll, 2000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [jobId, domain, router]);

  const pct = Math.round((doneCount / SKILLS.length) * 100);
  const active = useMemo(() => {
    const running = SKILLS.find((s) => progress[s.id] === "running");
    if (running) return running;
    if (status === "done") return { id: "done", title: "Complete", detail: "Opening your report." };
    return SKILLS.find((s) => !progress[s.id] || progress[s.id] === "pending") || SKILLS[0];
  }, [progress, status]);

  const remaining = Math.max(8, 90 - elapsed);

  return (
    <div className="min-h-[calc(100vh-56px)] bg-[#F7F6F1] px-4 py-10 sm:px-6 sm:py-16">
      <div className="mx-auto grid w-full max-w-[1080px] items-start gap-12 lg:grid-cols-[1.1fr_0.9fr] lg:gap-16">
        <div>
          <p className="text-[11px] font-medium tracking-[0.18em] text-neutral-400 uppercase">
            {status === "done" ? "Complete" : "Audit in progress"}
          </p>
          <h1 className="mt-3 font-serif text-4xl tracking-tight text-neutral-950 sm:text-5xl">
            Reading {domain || "your site"}
          </h1>
          <p className="mt-4 max-w-md text-[15px] leading-relaxed text-neutral-500">
            {errorMsg
              ? errorMsg
              : status === "done"
                ? "Checks are in. Opening the live report."
                : active.detail}
          </p>

          <div className="mt-10">
            <div className="mb-2 flex items-baseline justify-between gap-4">
              <span className="font-serif text-4xl text-neutral-950">{pct}%</span>
              <span className="text-[13px] text-neutral-400">
                {doneCount} of {SKILLS.length} checks
                {status !== "done" && !errorMsg ? ` · about ${remaining}s left` : ""}
              </span>
            </div>
            <div className="h-[3px] overflow-hidden rounded-full bg-black/[0.08]">
              <div
                className="h-full origin-left rounded-full bg-neutral-900"
                style={{
                  width: `${Math.max(pct, status === "queued" ? 4 : pct)}%`,
                  transition: "width 0.7s ease",
                }}
              />
            </div>
          </div>

          {errorMsg ? (
            <button
              type="button"
              onClick={() => router.push("/report")}
              className="mt-8 text-sm font-medium text-neutral-900 underline underline-offset-4"
            >
              Back to workspace
            </button>
          ) : (
            <p
              className="mt-8 text-sm text-neutral-500"
              style={{ animation: status === "running" ? "geoPulse 2.4s ease-in-out infinite" : undefined }}
            >
              {status === "done" ? "Preparing the diagnostic…" : `Now: ${active.title}`}
            </p>
          )}
        </div>

        <div className="rounded-2xl border border-black/[0.06] bg-white/80 p-2 sm:p-3">
          <ol className="divide-y divide-black/[0.05]">
            {SKILLS.map((skill, i) => {
              const s: SkillStatus = progress[skill.id] || "pending";
              return (
                <li key={skill.id} className="flex items-center gap-3 px-3 py-2.5">
                  <span className="w-5 shrink-0 font-mono text-[11px] text-neutral-300">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <span
                    className={
                      s === "done"
                        ? "flex-1 text-[13px] text-neutral-500"
                        : s === "running"
                          ? "flex-1 text-[13px] font-medium text-neutral-950"
                          : s === "error"
                            ? "flex-1 text-[13px] text-red-600"
                            : "flex-1 text-[13px] text-neutral-400"
                    }
                  >
                    {skill.title}
                  </span>
                  <StatusMark status={s} />
                </li>
              );
            })}
          </ol>
        </div>
      </div>
    </div>
  );
}

function StatusMark({ status }: { status: SkillStatus }) {
  if (status === "done") {
    return (
      <span className="flex h-4 w-4 items-center justify-center rounded-full bg-neutral-900 text-white">
        <svg width="8" height="8" viewBox="0 0 8 8" fill="none" aria-hidden="true">
          <path d="M1.5 4.1L3.2 5.8L6.5 2.2" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
        </svg>
      </span>
    );
  }
  if (status === "running") {
    return (
      <span
        className="h-1.5 w-1.5 rounded-full bg-neutral-900"
        style={{ animation: "geoPulse 1.4s ease-in-out infinite" }}
      />
    );
  }
  if (status === "error") {
    return <span className="h-1.5 w-1.5 rounded-full bg-red-500" />;
  }
  return <span className="h-1.5 w-1.5 rounded-full bg-neutral-200" />;
}

export default function LoadingPage() {
  return (
    <Suspense
      fallback={
        <div className="flex min-h-[calc(100vh-56px)] items-center justify-center bg-[#F7F6F1]">
          <p className="text-sm text-neutral-500">Starting audit…</p>
        </div>
      }
    >
      <LoadingContent />
    </Suspense>
  );
}
