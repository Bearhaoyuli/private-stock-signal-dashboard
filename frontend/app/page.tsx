"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { getSupabaseBrowserClient } from "@/lib/supabase/client";
import { isAllowedUser } from "@/lib/auth";

export default function HomePage() {
  const router = useRouter();

  useEffect(() => {
    const supabase = getSupabaseBrowserClient();
    supabase.auth.getSession().then(({ data }) => {
      const email = data.session?.user.email ?? null;
      if (data.session && isAllowedUser(email)) {
        router.replace("/dashboard");
        return;
      }
      router.replace("/login");
    });
  }, [router]);

  return <main className="min-h-screen" />;
}

