"use client";

import { Suspense } from "react";
import LoginForm from "@/components/LoginForm";

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="min-h-[50vh] bg-cream-50" />}>
      <LoginForm mode="login" />
    </Suspense>
  );
}
