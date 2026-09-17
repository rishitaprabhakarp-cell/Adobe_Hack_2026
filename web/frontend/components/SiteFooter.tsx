"use client";

import Link from "next/link";
import Logo from "@/components/Logo";
import { useAuth } from "@/lib/auth";

export default function SiteFooter() {
  const { user } = useAuth();
  return (
    <footer className="border-t border-black/10 px-4 py-8 sm:px-6">
      <div className="mx-auto max-w-[1280px]">
        <Link
          href={user ? "/report" : "/"}
          className="inline-flex items-center text-neutral-400 hover:text-neutral-700"
        >
          <Logo dark size={20} />
        </Link>
      </div>
    </footer>
  );
}
