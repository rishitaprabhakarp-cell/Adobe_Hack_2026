"use client";

import { cn, scoreColor, scoreLabel } from "@/lib/utils";

interface BenchmarkRow {
  domain: string;
  overall_score: number;
  dimension_scores?: Record<string, number>;
  geo_readiness?: string;
}

interface BenchmarkTableProps {
  data: BenchmarkRow[];
  highlightDomain?: string;
}

function TierBadge({ score }: { score: number }) {
  if (score >= 70)
    return (
      <span className="badge bg-emerald-500/15 text-emerald-400 border border-emerald-500/25">
        🟢 GEO Ready
      </span>
    );
  if (score >= 50)
    return (
      <span className="badge bg-amber-500/15 text-amber-400 border border-amber-500/25">
        🟡 Developing
      </span>
    );
  return (
    <span className="badge bg-crimson-500/15 text-crimson-400 border border-crimson-500/25">
      🔴 Not Ready
    </span>
  );
}

export default function BenchmarkTable({ data, highlightDomain }: BenchmarkTableProps) {
  const sorted = [...data].sort((a, b) => b.overall_score - a.overall_score);

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-white/5">
            <th className="text-left py-3 px-4 text-xs font-mono text-slate-500 uppercase tracking-wider">
              #
            </th>
            <th className="text-left py-3 px-4 text-xs font-mono text-slate-500 uppercase tracking-wider">
              Site
            </th>
            <th className="text-right py-3 px-4 text-xs font-mono text-slate-500 uppercase tracking-wider">
              Score
            </th>
            {["D1", "D2", "D3", "D4", "D5", "D6"].map((d) => (
              <th
                key={d}
                className="text-right py-3 px-2 text-xs font-mono text-slate-500 uppercase tracking-wider hidden md:table-cell"
              >
                {d}
              </th>
            ))}
            <th className="text-right py-3 px-4 text-xs font-mono text-slate-500 uppercase tracking-wider">
              Tier
            </th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, i) => {
            const isHighlight = row.domain === highlightDomain;
            return (
              <tr
                key={row.domain}
                className={cn(
                  "border-b border-white/3 transition-colors",
                  isHighlight
                    ? "bg-indigo-600/10 border-indigo-600/20"
                    : "hover:bg-white/2"
                )}
              >
                <td className="py-3 px-4 text-slate-500 font-mono text-xs">{i + 1}</td>
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2">
                    {isHighlight && (
                      <span className="badge badge-indigo text-[10px]">you</span>
                    )}
                    <span
                      className={cn(
                        "font-medium",
                        isHighlight ? "text-indigo-300" : "text-slate-200"
                      )}
                    >
                      {row.domain}
                    </span>
                  </div>
                </td>
                <td className="py-3 px-4 text-right">
                  <span className={cn("font-mono font-bold text-base", scoreColor(row.overall_score))}>
                    {row.overall_score}
                  </span>
                </td>
                {["D1", "D2", "D3", "D4", "D5", "D6"].map((d) => {
                  const dimScore = row.dimension_scores?.[d] ?? null;
                  return (
                    <td
                      key={d}
                      className="py-3 px-2 text-right hidden md:table-cell"
                    >
                      {dimScore !== null ? (
                        <span className={cn("font-mono text-xs", scoreColor(dimScore))}>
                          {dimScore}
                        </span>
                      ) : (
                        <span className="text-slate-600 text-xs">—</span>
                      )}
                    </td>
                  );
                })}
                <td className="py-3 px-4 text-right">
                  <TierBadge score={row.overall_score} />
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
