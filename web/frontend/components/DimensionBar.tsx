"use client";

import { scoreColor } from "@/lib/utils";

interface DimensionBarProps {
  id: string;
  name: string;
  score: number;
  compact?: boolean;
}

const DIMENSION_ICONS: Record<string, string> = {
  D1: "🔍",
  D2: "📝",
  D3: "🏷️",
  D4: "🗂️",
  D5: "🌐",
  D6: "⚙️",
};

export default function DimensionBar({ id, name, score, compact = false }: DimensionBarProps) {
  const color =
    score >= 70 ? "bg-emerald-500" : score >= 50 ? "bg-amber-500" : "bg-crimson-500";
  const glowColor =
    score >= 70
      ? "shadow-glow-emerald"
      : score >= 50
      ? ""
      : "shadow-glow-crimson";

  if (compact) {
    return (
      <div className="flex items-center gap-3">
        <span className="text-xs font-mono text-slate-500 w-5">{id}</span>
        <div className="flex-1 bg-white/5 rounded-full h-1.5 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-700 ${color}`}
            style={{ width: `${score}%` }}
          />
        </div>
        <span className={`text-xs font-mono font-bold w-8 text-right ${scoreColor(score)}`}>
          {score}
        </span>
      </div>
    );
  }

  return (
    <div className="card p-4 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-base">{DIMENSION_ICONS[id] || "📊"}</span>
          <div>
            <span className="text-xs font-mono text-slate-500">{id}</span>
            <p className="text-sm font-medium text-slate-200 leading-tight">{name}</p>
          </div>
        </div>
        <span className={`text-lg font-mono font-bold ${scoreColor(score)}`}>{score}</span>
      </div>
      <div className="bg-white/5 rounded-full h-1.5 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-700 ${color} ${glowColor}`}
          style={{ width: `${score}%` }}
        />
      </div>
    </div>
  );
}
