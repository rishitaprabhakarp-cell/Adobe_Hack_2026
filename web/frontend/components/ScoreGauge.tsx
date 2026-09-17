"use client";

import { scoreColor, scoreLabel, scoreRingColor } from "@/lib/utils";

interface ScoreGaugeProps {
  score: number;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
}

export default function ScoreGauge({ score, size = "md", showLabel = true }: ScoreGaugeProps) {
  const sizes = { sm: 80, md: 120, lg: 160 };
  const dim = sizes[size];
  const strokeWidth = size === "lg" ? 10 : size === "md" ? 8 : 6;
  const radius = (dim - strokeWidth * 2) / 2;
  const circumference = 2 * Math.PI * radius;
  const progress = Math.max(0, Math.min(100, score));
  const dashOffset = circumference * (1 - progress / 100);
  const color = scoreRingColor(score);
  const textSize = size === "lg" ? "text-4xl" : size === "md" ? "text-2xl" : "text-lg";
  const labelSize = size === "lg" ? "text-sm" : "text-xs";

  return (
    <div className="relative flex flex-col items-center gap-1">
      <svg width={dim} height={dim} className="-rotate-90">
        {/* Track */}
        <circle
          cx={dim / 2}
          cy={dim / 2}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth={strokeWidth}
        />
        {/* Progress */}
        <circle
          cx={dim / 2}
          cy={dim / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          style={{
            transition: "stroke-dashoffset 1s cubic-bezier(0.4, 0, 0.2, 1)",
            filter: `drop-shadow(0 0 6px ${color}60)`,
          }}
        />
      </svg>
      {/* Score text overlay */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className={`font-mono font-bold leading-none ${textSize} ${scoreColor(score)}`}>
          {score}
        </span>
        <span className="text-slate-500 text-[10px] font-mono leading-none mt-0.5">/100</span>
      </div>
      {showLabel && (
        <span className={`${labelSize} font-medium ${scoreColor(score)} mt-1`}>
          {scoreLabel(score)}
        </span>
      )}
    </div>
  );
}
