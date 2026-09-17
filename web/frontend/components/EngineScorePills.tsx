"use client";

import { scoreColor } from "@/lib/utils";

interface EngineScorePillsProps {
  scores: Record<string, number>;
}

const ENGINE_ICONS: Record<string, string> = {
  ChatGPT: "🤖",
  Perplexity: "🔮",
  "Google AI Overviews": "🔍",
  Gemini: "✨",
  "Bing Copilot": "🪟",
};

export default function EngineScorePills({ scores }: EngineScorePillsProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {Object.entries(scores).map(([engine, score]) => (
        <div
          key={engine}
          className="flex items-center gap-1.5 bg-navy-700 border border-white/8 rounded-lg px-3 py-1.5"
        >
          <span className="text-sm">{ENGINE_ICONS[engine] || "🤖"}</span>
          <span className="text-xs text-slate-400 font-medium">{engine}</span>
          <span className={`text-sm font-mono font-bold ${scoreColor(score)}`}>{score}</span>
        </div>
      ))}
    </div>
  );
}
