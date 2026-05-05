"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { isAllowedUser } from "@/lib/auth";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";

function safeGetClient() {
  try {
    return getSupabaseBrowserClient();
  } catch {
    return null;
  }
}

export function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const supabase = safeGetClient();
    if (!supabase) {
      return;
    }
    supabase.auth.getSession().then(({ data }) => {
      const allowed = isAllowedUser(data.session?.user.email ?? null);
      if (data.session && allowed) {
        router.replace("/dashboard");
      }
    });
  }, [router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const supabase = safeGetClient();
    if (!supabase) {
      setError("Missing Supabase public configuration.");
      return;
    }

    setLoading(true);
    setError(null);
    const { data, error: signInError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    setLoading(false);

    if (signInError) {
      setError(signInError.message);
      return;
    }

    const sessionEmail = data.user?.email ?? null;
    if (!isAllowedUser(sessionEmail)) {
      await supabase.auth.signOut();
      setError("Access denied.");
      return;
    }

    router.replace("/dashboard");
  }

  return (
    <div className="mx-auto flex max-w-md flex-col justify-center">
      <div className="space-y-2">
        <p className="font-mono text-xs uppercase tracking-[0.24em] text-black/48">
          Sign In
        </p>
        <h2 className="text-3xl font-semibold">Personal dashboard access only.</h2>
        <p className="text-sm leading-6 text-black/62">
          Public signup is intentionally absent. Create the user in Supabase Auth
          first, then sign in here.
        </p>
      </div>

      <form className="mt-8 space-y-4" onSubmit={handleSubmit}>
        <label className="block space-y-2">
          <span className="text-sm font-medium">Email</span>
          <input
            className="w-full rounded-2xl border border-black/12 bg-white px-4 py-3 outline-none transition focus:border-pine"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
            autoComplete="email"
            required
          />
        </label>
        <label className="block space-y-2">
          <span className="text-sm font-medium">Password</span>
          <input
            className="w-full rounded-2xl border border-black/12 bg-white px-4 py-3 outline-none transition focus:border-pine"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="••••••••"
            autoComplete="current-password"
            required
          />
        </label>

        {error ? (
          <div className="rounded-2xl border border-ember/18 bg-ember/8 px-4 py-3 text-sm text-ember">
            {error}
          </div>
        ) : null}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-2xl bg-ink px-4 py-3 text-sm font-medium text-white transition hover:bg-pine disabled:cursor-not-allowed disabled:opacity-60"
        >
          {loading ? "Signing in..." : "Sign in"}
        </button>
      </form>
    </div>
  );
}
