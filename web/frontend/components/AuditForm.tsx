"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Globe } from "lucide-react";
import { startAuditFlow } from "@/lib/audit-flow";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

export default function AuditForm({
  id = "audit",
  initialUrl = "",
  variant = "hero",
}: {
  id?: string;
  initialUrl?: string;
  variant?: "hero" | "workspace";
}) {
  const router = useRouter();
  const { user, ready } = useAuth();
  const [url, setUrl] = useState(initialUrl);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim() || !ready) return;
    setError("");
    setLoading(true);
    try {
      await startAuditFlow(url, {
        authenticated: Boolean(user),
        router,
      });
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong. Please try again.");
      setLoading(false);
    }
  };

  const hero = variant === "hero";

  return (
    <form
      id={id}
      onSubmit={handleSubmit}
      className={cn("scroll-mt-28", hero ? "mx-auto max-w-xl" : "w-full")}
    >
      <div
        className={cn(
          "relative flex items-center",
          hero
            ? "rounded-2xl border border-black/10 bg-white shadow-[0_1px_2px_rgba(0,0,0,0.04)]"
            : "rounded-xl border border-black/10 bg-[#F7F6F1]"
        )}
      >
        <Globe size={16} className="pointer-events-none absolute left-4 text-neutral-400" />
        <input
          type="text"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="yourbrand.com"
          aria-label="Domain to audit"
          className={cn(
            "w-full bg-transparent text-sm text-neutral-900 placeholder:text-neutral-400 focus:outline-none",
            hero ? "py-4 pr-32 pl-11" : "py-4 pr-36 pl-11"
          )}
          disabled={loading}
        />
        <button
          type="submit"
          disabled={loading || !url.trim() || !ready}
          className={cn(
            "absolute right-2 rounded-xl px-4 py-2 text-sm font-medium transition-all",
            loading || !url.trim()
              ? "cursor-not-allowed bg-neutral-200 text-neutral-400"
              : "bg-neutral-950 text-white hover:bg-neutral-800"
          )}
        >
          {loading ? "Starting…" : "Run Audit"}
        </button>
      </div>
      {error && <p className="mt-2 text-left text-xs text-red-600">{error}</p>}
    </form>
  );
}
