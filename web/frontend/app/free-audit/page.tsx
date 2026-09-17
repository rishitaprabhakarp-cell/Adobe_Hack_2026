"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function FreeAuditRedirect() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/#audit");
  }, [router]);

  return (
    <div className="flex min-h-[calc(100vh-56px)] items-center justify-center bg-[#F7F6F1]">
      <p className="text-sm text-neutral-500">Opening audit…</p>
    </div>
  );
}
