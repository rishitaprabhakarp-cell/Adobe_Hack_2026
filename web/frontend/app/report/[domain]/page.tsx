"use client";

import { useEffect } from "react";
import { useParams, useRouter } from "next/navigation";

export default function LegacyReportRedirect() {
  const { domain } = useParams<{ domain: string }>();
  const router = useRouter();

  useEffect(() => {
    const decoded = decodeURIComponent(domain || "");
    const params = new URLSearchParams(window.location.search);
    if (decoded) params.set("domain", decoded);
    router.replace(`/report${params.toString() ? `?${params.toString()}` : ""}`);
  }, [domain, router]);

  return (
    <div className="flex min-h-[40vh] items-center justify-center bg-[#F7F6F1] text-sm text-neutral-500">
      Opening report…
    </div>
  );
}
