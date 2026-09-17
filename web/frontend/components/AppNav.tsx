"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LogOut, Menu, X } from "lucide-react";
import Logo from "@/components/Logo";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/report", label: "Report", match: (path: string) => path.startsWith("/report") },
  { href: "/benchmark", label: "Benchmarks", match: (path: string) => path.startsWith("/benchmark") },
];

export default function AppNav() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout, ready } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [userOpen, setUserOpen] = useState(false);
  const userMenuRef = useRef<HTMLDivElement>(null);
  const isAuthPage = pathname === "/login" || pathname === "/register";
  const signedIn = Boolean(ready && user);
  const [navPath, setNavPath] = useState(pathname);
  if (navPath !== pathname) {
    setNavPath(pathname);
    setMenuOpen(false);
    setUserOpen(false);
  }

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (!userMenuRef.current?.contains(e.target as Node)) setUserOpen(false);
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  const initial = (user?.name || user?.email || "?").charAt(0).toUpperCase();
  const homeHref = signedIn ? "/report" : "/";

  return (
    <nav className="sticky top-0 z-50 border-b border-black/[0.06] bg-white/90 backdrop-blur-md print:hidden">
      <div className="mx-auto flex h-14 max-w-[1280px] items-center justify-between px-4 sm:px-6">
        <div className="flex items-center gap-6">
          <Link href={homeHref} className="shrink-0" aria-label="GEOReady home">
            <Logo dark size={24} />
          </Link>
          {signedIn && (
            <div className="hidden items-center gap-1 md:flex">
              {LINKS.map((l) => (
                <Link
                  key={l.label}
                  href={l.href}
                  className={cn(
                    "rounded-md px-2.5 py-1.5 text-[13px] transition-colors",
                    l.match(pathname)
                      ? "bg-neutral-100 font-medium text-neutral-950"
                      : "text-neutral-400 hover:text-neutral-700"
                  )}
                >
                  {l.label}
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center gap-3">
          {ready && user ? (
            <>
              <div className="relative" ref={userMenuRef}>
                <button
                  type="button"
                  onClick={() => setUserOpen((v) => !v)}
                  className="flex items-center gap-2 rounded-full border border-black/[0.06] bg-white py-0.5 pr-2.5 pl-0.5 hover:bg-neutral-50"
                >
                  <span className="flex h-7 w-7 items-center justify-center rounded-full bg-neutral-900 text-[11px] font-semibold text-white">
                    {initial}
                  </span>
                  <span className="hidden max-w-[140px] truncate text-[13px] font-medium text-neutral-800 sm:block">
                    {user.name || user.email}
                  </span>
                </button>
                {userOpen && (
                  <div className="absolute right-0 mt-2 w-56 overflow-hidden rounded-xl border border-black/10 bg-white shadow-[0_12px_40px_-18px_rgba(0,0,0,0.2)]">
                    <div className="border-b border-black/5 px-3 py-2.5">
                      <p className="truncate text-sm font-medium text-neutral-900">
                        {user.name || "Account"}
                      </p>
                      <p className="truncate text-[12px] text-neutral-400">{user.email}</p>
                    </div>
                    <button
                      type="button"
                      onClick={() => {
                        logout();
                        setUserOpen(false);
                        router.push("/");
                      }}
                      className="flex w-full items-center gap-2 px-3 py-2.5 text-left text-[13px] text-neutral-600 hover:bg-neutral-50"
                    >
                      <LogOut size={14} />
                      Sign out
                    </button>
                  </div>
                )}
              </div>
              {!pathname.startsWith("/report") && (
                <Link
                  href="/report#audit"
                  className="inline-flex items-center rounded-lg bg-neutral-950 px-3 py-1.5 text-[13px] font-medium text-white hover:bg-neutral-800"
                >
                  New audit
                </Link>
              )}
              <button
                type="button"
                className="rounded-md p-1.5 text-neutral-500 hover:bg-neutral-100 md:hidden"
                onClick={() => setMenuOpen((v) => !v)}
                aria-label="Toggle menu"
              >
                {menuOpen ? <X size={18} /> : <Menu size={18} />}
              </button>
            </>
          ) : ready && !isAuthPage ? (
            <>
              <Link
                href="/login"
                className="text-[13px] text-neutral-500 transition-colors hover:text-neutral-900"
              >
                Sign in
              </Link>
              <Link
                href="/#audit"
                className="inline-flex items-center rounded-lg bg-neutral-950 px-3 py-1.5 text-[13px] font-medium text-white hover:bg-neutral-800"
              >
                Run audit
              </Link>
            </>
          ) : !ready ? (
            <span className="h-7 w-24 rounded-lg bg-neutral-100" />
          ) : null}
        </div>
      </div>

      {menuOpen && signedIn && (
        <div className="border-t border-black/[0.06] bg-white px-4 py-3 md:hidden">
          <div className="flex flex-col">
            {LINKS.map((l) => (
              <Link
                key={l.label}
                href={l.href}
                className={cn(
                  "rounded-md px-2 py-2 text-sm",
                  l.match(pathname) ? "font-medium text-neutral-950" : "text-neutral-500"
                )}
              >
                {l.label}
              </Link>
            ))}
          </div>
        </div>
      )}
    </nav>
  );
}
