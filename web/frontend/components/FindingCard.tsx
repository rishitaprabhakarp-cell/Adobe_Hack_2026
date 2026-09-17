"use client";

import { useMemo, useState } from "react";
import { ChevronDown, Copy, Check } from "lucide-react";
import { citationLift, cn } from "@/lib/utils";

export interface Finding {
  id: string;
  title: string;
  severity: string;
  evidence: string;
  suggested_action: {
    summary: string;
    priority: string;
    effort: string;
    proactive?: boolean;
  };
  research_lift?: string;
  platform_fix_code?: string | { platform?: string; code?: string };
}

interface FindingCardProps {
  finding: Finding;
  index: number;
  defaultOpen?: boolean;
}

export default function FindingCard({ finding, index, defaultOpen = false }: FindingCardProps) {
  const [open, setOpen] = useState(defaultOpen);
  const [copied, setCopied] = useState(false);

  const severity = finding.severity?.toUpperCase() || "LOW";
  const effort = finding.suggested_action?.effort;
  const lift = citationLift(finding.research_lift);
  const code = useMemo(() => realCode(finding), [finding]);

  const copy = async () => {
    if (!code) return;
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    } catch {
      /* ignore */
    }
  };

  return (
    <article className="border-b border-black/[0.07] last:border-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="grid w-full grid-cols-[2.25rem_minmax(0,1fr)_auto] items-start gap-3 py-4 text-left"
      >
        <span className="pt-0.5 font-mono text-[11px] text-neutral-400">
          {String(index + 1).padStart(2, "0")}
        </span>
        <span className="min-w-0">
          <span className="block text-[15px] leading-snug text-neutral-900">{finding.title}</span>
          <span className="mt-1 flex flex-wrap items-center gap-x-2 text-[12px] text-neutral-400">
            <span className={sevText(severity)}>{labelSeverity(severity)}</span>
            {effort && (
              <>
                <span className="text-neutral-300">·</span>
                <span>{capitalize(effort)} effort</span>
              </>
            )}
            {lift && (
              <>
                <span className="text-neutral-300">·</span>
                <span>{lift.startsWith("+") ? lift : `+${lift}`}</span>
              </>
            )}
          </span>
        </span>
        <ChevronDown
          size={15}
          className={cn(
            "mt-1 shrink-0 text-neutral-300 transition-transform",
            open && "rotate-180"
          )}
        />
      </button>

      {open && (
        <div className="space-y-5 pb-5 pl-[2.25rem]">
          {finding.evidence && (
            <p className="text-sm leading-[1.7] text-neutral-600">{finding.evidence}</p>
          )}
          {finding.suggested_action?.summary && (
            <p className="text-sm leading-[1.7] text-neutral-800">
              {finding.suggested_action.summary}
            </p>
          )}
          {code && (
            <div className="overflow-hidden rounded-lg border border-black/[0.08] bg-[#F4F3EE]">
              <div className="flex items-center justify-between px-3 py-1.5">
                <span className="text-[11px] text-neutral-400">Reference</span>
                <button
                  type="button"
                  onClick={copy}
                  className="inline-flex items-center gap-1 text-[11px] text-neutral-500 hover:text-neutral-900"
                >
                  {copied ? <Check size={11} /> : <Copy size={11} />}
                  {copied ? "Copied" : "Copy"}
                </button>
              </div>
              <pre className="overflow-x-auto px-3 pb-3 font-mono text-[12px] leading-6 text-neutral-700">
                {code}
              </pre>
            </div>
          )}
        </div>
      )}
    </article>
  );
}

function labelSeverity(severity: string) {
  if (severity === "CRITICAL") return "Critical";
  if (severity === "HIGH") return "High";
  if (severity === "MEDIUM") return "Medium";
  return "Low";
}

function sevText(severity: string) {
  if (severity === "CRITICAL") return "text-red-700";
  if (severity === "HIGH") return "text-neutral-700";
  return "text-neutral-400";
}

function capitalize(s: string) {
  return s ? s.charAt(0).toUpperCase() + s.slice(1) : s;
}

function realCode(finding: Finding): string {
  const pfc = finding.platform_fix_code;
  if (typeof pfc === "string" && pfc.trim()) return pfc.trim();
  if (pfc && typeof pfc === "object" && pfc.code?.trim()) return pfc.code.trim();
  return "";
}
