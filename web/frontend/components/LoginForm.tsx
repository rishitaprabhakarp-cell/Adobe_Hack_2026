"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { getPendingAuditUrl } from "@/lib/audit-flow";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

function resolveNext(raw: string | null) {
  if (!raw || raw === "/" || raw.startsWith("/#")) return "/report";
  return raw.startsWith("/") ? raw : "/report";
}

export default function LoginForm({ mode }: { mode: "login" | "register" }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = resolveNext(searchParams.get("next"));
  const { login, register, user, ready } = useAuth();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const isRegister = mode === "register";

  useEffect(() => {
    if (!ready || !user) return;
    const pending = getPendingAuditUrl();
    router.replace(pending ? "/audit/resume" : next);
  }, [ready, user, next, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (isRegister) await register(email, password, name);
      else await login(email, password);
      const pending = getPendingAuditUrl();
      if (pending) {
        router.push("/audit/resume");
        return;
      }
      router.push(next);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setLoading(false);
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
    <div className="flex min-h-[calc(100vh-56px)] items-center justify-center bg-cream-50 px-4 py-12">
      <div className="w-full max-w-md">
        <p className="mb-3 text-[11px] font-medium tracking-[0.18em] text-neutral-400 uppercase">
          {isRegister ? "Create account" : "Welcome back"}
        </p>
        <h1 className="font-serif text-4xl tracking-tight text-neutral-950">
          {isRegister ? "Get your GEO workspace." : "Sign in to GEOReady."}
        </h1>
        <p className="mt-3 mb-8 text-sm leading-relaxed text-neutral-500">
          {isRegister
            ? "Save audits, rerun crawls, and pick up your live reports from any device."
            : "Continue to your audits, engine visibility, and diagnostic reports."}
        </p>

        <form
          onSubmit={handleSubmit}
          className="rounded-2xl border border-black/10 bg-white p-6 shadow-[0_12px_40px_-24px_rgba(0,0,0,0.12)]"
        >
          {isRegister && (
            <Field label="Name">
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Ada Lovelace"
                className={fieldClass}
              />
            </Field>
          )}
          <Field label="Work email">
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              className={fieldClass}
            />
          </Field>
          <Field label="Password">
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={isRegister ? "At least 8 characters" : "Your password"}
              className={fieldClass}
            />
          </Field>

          {error && <p className="mb-4 text-xs text-red-600">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className={cn(
              "w-full rounded-xl py-3 text-sm font-medium text-white transition-colors",
              loading ? "cursor-not-allowed bg-neutral-400" : "bg-neutral-950 hover:bg-neutral-800"
            )}
          >
            {loading ? "Please wait…" : isRegister ? "Create account" : "Sign in"}
          </button>
        </form>

        <p className="mt-5 text-center text-sm text-neutral-500">
          {isRegister ? (
            <>
              Already have an account?{" "}
              <Link href={`/login?next=${encodeURIComponent(next)}`} className="font-medium text-neutral-900 hover:underline">
                Sign in
              </Link>
            </>
          ) : (
            <>
              New here?{" "}
              <Link href={`/register?next=${encodeURIComponent(next)}`} className="font-medium text-neutral-900 hover:underline">
                Create an account
              </Link>
            </>
          )}
        </p>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="mb-4 block">
      <span className="mb-1.5 block text-[11px] font-medium tracking-wide text-neutral-500 uppercase">
        {label}
      </span>
      {children}
    </label>
  );
}

const fieldClass =
  "w-full rounded-xl border border-black/10 bg-cream-50 px-3.5 py-2.5 text-sm text-neutral-900 placeholder:text-neutral-400 focus:border-neutral-400 focus:outline-none";
