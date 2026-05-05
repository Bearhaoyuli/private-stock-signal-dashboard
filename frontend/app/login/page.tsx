import { LoginForm } from "@/components/login-form";

export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center px-5 py-10">
      <div className="panel grid w-full max-w-5xl overflow-hidden rounded-[28px] md:grid-cols-[1.1fr_0.9fr]">
        <section className="border-b border-black/10 bg-[linear-gradient(160deg,rgba(33,64,49,0.96),rgba(17,17,17,0.94))] p-8 text-white md:border-b-0 md:border-r md:p-10">
          <div className="max-w-md space-y-5">
            <p className="font-mono text-xs uppercase tracking-[0.32em] text-white/65">
              Private Research Signal
            </p>
            <h1 className="text-3xl font-semibold leading-tight md:text-5xl">
              Lean dashboard for Reddit-driven stock research signals.
            </h1>
            <p className="text-sm leading-6 text-white/74 md:text-base">
              This is a private tool. It ranks research setups, not buy or sell
              advice. Mock Reddit mode works before live API credentials exist.
            </p>
            <div className="grid gap-3 text-sm text-white/72">
              <div className="rounded-2xl border border-white/12 bg-white/6 p-4">
                Dense table only. No public landing page, no social features, no
                trade execution.
              </div>
              <div className="rounded-2xl border border-white/12 bg-white/6 p-4">
                Static GitHub Pages frontend, Supabase auth and data, optional
                FastAPI jobs for ingestion and scoring.
              </div>
            </div>
          </div>
        </section>
        <section className="bg-[#fffdf7] p-8 md:p-10">
          <LoginForm />
        </section>
      </div>
    </main>
  );
}

