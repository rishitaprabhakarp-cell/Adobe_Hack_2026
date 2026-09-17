import Link from "next/link";
import Logo from "@/components/Logo";

export default function Navbar({
  variant = "dark",
}: {
  variant?: "dark" | "light";
}) {
  if (variant === "light") {
    return (
      <nav className="sticky top-0 z-50 border-b border-black/[0.06] bg-[#F6F5F1]/80 backdrop-blur-md">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5 sm:px-8">
          <Link href="/" className="transition-opacity hover:opacity-80">
            <Logo dark />
          </Link>

          <div className="flex items-center gap-5">
            <Link
              href="/free-audit"
              className="text-sm text-neutral-500 transition-colors hover:text-neutral-900"
            >
              Sign in
            </Link>
            <Link
              href="#audit"
              className="rounded-lg bg-neutral-950 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-neutral-800"
            >
              Run Free Audit
            </Link>
          </div>
        </div>
      </nav>
    );
  }

  return (
    <nav className="fixed top-0 right-0 left-0 z-50 border-b border-white/5 bg-navy-900/80 backdrop-blur-md">
      <div className="mx-auto flex h-14 max-w-7xl items-center justify-between px-4 sm:px-6">
        <Link href="/" className="group flex items-center">
          <Logo />
        </Link>

        <div className="flex items-center gap-1">
          <Link href="/benchmark" className="btn-ghost px-3 py-1.5 text-sm">
            Benchmark
          </Link>
          <Link href="/free-audit" className="btn-primary px-4 py-1.5 text-sm">
            Free Audit
          </Link>
        </div>
      </div>
    </nav>
  );
}
