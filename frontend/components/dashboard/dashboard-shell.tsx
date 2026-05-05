"use client";

import clsx from "clsx";
import { Fragment, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { isAllowedUser } from "@/lib/auth";
import { fetchDashboard, fetchTickerDetail } from "@/lib/api";
import { getSupabaseBrowserClient } from "@/lib/supabase/client";
import type { DashboardFilters, DashboardRow, TickerDetail } from "@/lib/types";

const DEFAULT_FILTERS: DashboardFilters = {
  subreddit: "",
  window: "Today",
  minSignal: 40,
  search: "",
};

function safeGetClient() {
  try {
    return getSupabaseBrowserClient();
  } catch {
    return null;
  }
}

function confidenceLabel(confidence: number) {
  if (confidence >= 75) {
    return "High";
  }
  if (confidence >= 45) {
    return "Medium";
  }
  return "Low";
}

function scoreTone(value: number, reverse = false) {
  if ((!reverse && value >= 70) || (reverse && value <= 35)) {
    return "text-pine";
  }
  if ((!reverse && value < 40) || (reverse && value >= 75)) {
    return "text-ember";
  }
  return "text-brass";
}

export function DashboardShell() {
  const router = useRouter();
  const [authorized, setAuthorized] = useState(false);
  const [accessDenied, setAccessDenied] = useState(false);
  const [rows, setRows] = useState<DashboardRow[]>([]);
  const [warnings, setWarnings] = useState<string[]>([]);
  const [filters, setFilters] = useState<DashboardFilters>(DEFAULT_FILTERS);
  const [loading, setLoading] = useState(true);
  const [expandedTicker, setExpandedTicker] = useState<string | null>(null);
  const [detailCache, setDetailCache] = useState<Record<string, TickerDetail>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const supabase = safeGetClient();
    if (!supabase) {
      setError("Missing Supabase public configuration.");
      setLoading(false);
      return;
    }
    let mounted = true;
    supabase.auth.getSession().then(async ({ data }) => {
      const session = data.session;
      const email = session?.user.email ?? null;

      if (!session) {
        router.replace("/login");
        return;
      }
      if (!isAllowedUser(email)) {
        setAccessDenied(true);
        setAuthorized(false);
        return;
      }
      if (!mounted) {
        return;
      }
      setAuthorized(true);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      const email = session?.user.email ?? null;
      if (!session) {
        router.replace("/login");
        return;
      }
      if (!isAllowedUser(email)) {
        setAccessDenied(true);
        setAuthorized(false);
      }
    });

    return () => {
      mounted = false;
      subscription.unsubscribe();
    };
  }, [router]);

  useEffect(() => {
    if (!authorized) {
      return;
    }
    setLoading(true);
    setError(null);
    fetchDashboard(filters)
      .then((response) => {
        setRows(response.rows);
        setWarnings(response.warnings);
      })
      .catch((err: Error) => {
        setError(err.message);
      })
      .finally(() => setLoading(false));
  }, [authorized, filters]);

  async function toggleRow(ticker: string) {
    const nextTicker = expandedTicker === ticker ? null : ticker;
    setExpandedTicker(nextTicker);
    if (!nextTicker || detailCache[nextTicker]) {
      return;
    }
    try {
      const detail = await fetchTickerDetail(nextTicker);
      setDetailCache((current) => ({ ...current, [nextTicker]: detail }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load ticker detail.");
    }
  }

  async function handleSignOut() {
    const supabase = safeGetClient();
    if (!supabase) {
      router.replace("/login");
      return;
    }
    await supabase.auth.signOut();
    router.replace("/login");
  }

  const subredditOptions = useMemo(() => {
    const unique = new Set<string>();
    rows.forEach((row) => row.subreddits?.forEach((subreddit) => unique.add(subreddit)));
    return Array.from(unique).sort();
  }, [rows]);

  if (accessDenied) {
    return (
      <main className="flex min-h-screen items-center justify-center px-5">
        <div className="panel w-full max-w-xl rounded-[28px] p-8">
          <h1 className="text-3xl font-semibold">Access denied.</h1>
          <p className="mt-3 text-sm leading-6 text-black/65">
            The authenticated email does not match the allowed user.
          </p>
          <button
            type="button"
            className="mt-6 rounded-2xl bg-ink px-4 py-3 text-sm font-medium text-white"
            onClick={handleSignOut}
          >
            Sign out
          </button>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen px-4 py-5 md:px-7 md:py-7">
      <div className="mx-auto max-w-[1400px] space-y-5">
        <header className="panel rounded-[28px] px-5 py-5 md:px-7">
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <p className="font-mono text-xs uppercase tracking-[0.28em] text-black/45">
                Private Dashboard
              </p>
              <h1 className="mt-2 text-2xl font-semibold md:text-4xl">
                Reddit stock research signals
              </h1>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-black/62">
                Scores reflect research setup quality, not investment advice.
                Mock Reddit ingestion remains active until live credentials are enabled.
              </p>
            </div>
            <button
              type="button"
              className="rounded-2xl border border-black/10 bg-white px-4 py-3 text-sm font-medium text-black transition hover:border-black/25"
              onClick={handleSignOut}
            >
              Sign out
            </button>
          </div>
        </header>

        <section className="panel rounded-[28px] p-4 md:p-5">
          <div className="grid gap-3 md:grid-cols-[1.2fr_0.9fr_0.9fr_1.2fr_auto]">
            <select
              className="rounded-2xl border border-black/10 bg-white px-4 py-3"
              value={filters.subreddit}
              onChange={(event) =>
                setFilters((current) => ({ ...current, subreddit: event.target.value }))
              }
            >
              <option value="">All subreddits</option>
              {subredditOptions.map((subreddit) => (
                <option key={subreddit} value={subreddit}>
                  {subreddit}
                </option>
              ))}
            </select>

            <select
              className="rounded-2xl border border-black/10 bg-white px-4 py-3"
              value={filters.window}
              onChange={(event) =>
                setFilters((current) => ({
                  ...current,
                  window: event.target.value as DashboardFilters["window"],
                }))
              }
            >
              <option value="Today">Today</option>
              <option value="3D">3D</option>
              <option value="7D">7D</option>
              <option value="30D">30D</option>
            </select>

            <label className="flex items-center gap-3 rounded-2xl border border-black/10 bg-white px-4 py-3">
              <span className="text-sm text-black/60">Min signal</span>
              <input
                className="w-full"
                type="range"
                min={0}
                max={100}
                step={5}
                value={filters.minSignal}
                onChange={(event) =>
                  setFilters((current) => ({
                    ...current,
                    minSignal: Number(event.target.value),
                  }))
                }
              />
              <span className="font-mono text-sm">{filters.minSignal}</span>
            </label>

            <input
              className="rounded-2xl border border-black/10 bg-white px-4 py-3"
              placeholder="Search ticker"
              value={filters.search}
              onChange={(event) =>
                setFilters((current) => ({ ...current, search: event.target.value }))
              }
            />

            <div className="rounded-2xl border border-black/10 bg-[#f7f1e5] px-4 py-3 text-sm text-black/65">
              {rows.length} rows
            </div>
          </div>

          {warnings.length ? (
            <div className="mt-4 rounded-2xl border border-brass/20 bg-brass/10 px-4 py-3 text-sm text-black/75">
              {warnings.join(" ")}
            </div>
          ) : null}
          {error ? (
            <div className="mt-4 rounded-2xl border border-ember/18 bg-ember/8 px-4 py-3 text-sm text-ember">
              {error}
            </div>
          ) : null}
        </section>

        <section className="panel overflow-hidden rounded-[28px]">
          <div className="overflow-x-auto">
            <table className="min-w-[1320px] w-full border-collapse text-sm">
              <thead className="bg-black/[0.03] font-mono text-[11px] uppercase tracking-[0.18em] text-black/55">
                <tr>
                  {[
                    "Ticker",
                    "Company",
                    "Current price",
                    "1D %",
                    "5D %",
                    "Reddit post count today",
                    "Mention spike",
                    "Sentiment",
                    "Historical win rate",
                    "Avg 5D return after similar posts",
                    "Signal score",
                    "Risk score",
                    "Confidence",
                    "Label",
                    "One-line reason",
                  ].map((header) => (
                    <th key={header} className="whitespace-nowrap px-4 py-4 text-left">
                      {header}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td className="px-4 py-10 text-center text-black/55" colSpan={15}>
                      Loading signals...
                    </td>
                  </tr>
                ) : rows.length === 0 ? (
                  <tr>
                    <td className="px-4 py-10 text-center text-black/55" colSpan={15}>
                      No rows match the current filters.
                    </td>
                  </tr>
                ) : (
                  rows.map((row) => {
                    const detail = detailCache[row.ticker];
                    const expanded = expandedTicker === row.ticker;
                    return (
                      <Fragment key={row.ticker}>
                        <tr
                          className="cursor-pointer border-t border-black/8 transition hover:bg-black/[0.025]"
                          onClick={() => toggleRow(row.ticker)}
                        >
                          <td className="px-4 py-4 font-semibold">{row.ticker}</td>
                          <td className="px-4 py-4 text-black/72">{row.company}</td>
                          <td className="px-4 py-4 font-mono">${row.current_price.toFixed(2)}</td>
                          <td
                            className={clsx(
                              "px-4 py-4 font-mono",
                              row.change_1d_pct >= 0 ? "text-pine" : "text-ember",
                            )}
                          >
                            {row.change_1d_pct.toFixed(2)}%
                          </td>
                          <td
                            className={clsx(
                              "px-4 py-4 font-mono",
                              row.change_5d_pct >= 0 ? "text-pine" : "text-ember",
                            )}
                          >
                            {row.change_5d_pct.toFixed(2)}%
                          </td>
                          <td className="px-4 py-4 font-mono">{row.reddit_post_count_today}</td>
                          <td className="px-4 py-4 font-mono">{row.mention_spike.toFixed(2)}x</td>
                          <td className="px-4 py-4 font-mono">{row.sentiment.toFixed(2)}</td>
                          <td className="px-4 py-4 font-mono">{row.historical_win_rate.toFixed(1)}%</td>
                          <td className="px-4 py-4 font-mono">
                            {row.avg_5d_return_after_similar_posts.toFixed(2)}%
                          </td>
                          <td className={clsx("px-4 py-4 font-mono font-semibold", scoreTone(row.signal_score))}>
                            {row.signal_score.toFixed(1)}
                          </td>
                          <td
                            className={clsx(
                              "px-4 py-4 font-mono font-semibold",
                              scoreTone(row.risk_score, true),
                            )}
                          >
                            {row.risk_score.toFixed(1)}
                          </td>
                          <td className="px-4 py-4">
                            <span className="rounded-full border border-black/10 bg-white px-3 py-1 font-mono text-xs uppercase tracking-[0.16em]">
                              {confidenceLabel(row.confidence)}
                            </span>
                          </td>
                          <td className="px-4 py-4">
                            <span className="rounded-full bg-black px-3 py-1 text-xs font-medium text-white">
                              {row.label}
                            </span>
                          </td>
                          <td className="max-w-[300px] px-4 py-4 text-black/65">
                            {row.one_line_reason}
                          </td>
                        </tr>
                        {expanded ? (
                          <tr className="border-t border-black/8 bg-[#fcf8ef]">
                            <td colSpan={15} className="px-5 py-5">
                              {!detail ? (
                                <div className="text-sm text-black/55">Loading details...</div>
                              ) : (
                                <div className="grid gap-5 lg:grid-cols-[1.15fr_0.85fr]">
                                  <div className="space-y-4">
                                    <div>
                                      <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-black/45">
                                        Score explanation
                                      </p>
                                      <p className="mt-2 text-sm leading-6 text-black/72">
                                        {detail.explanation}
                                      </p>
                                    </div>
                                    <div className="space-y-3">
                                      {detail.recent_posts.map((post) => (
                                        <article
                                          key={post.reddit_id}
                                          className="rounded-2xl border border-black/8 bg-white px-4 py-4"
                                        >
                                          <h3 className="text-base font-semibold">{post.title_original}</h3>
                                          {post.title_translated ? (
                                            <p className="mt-2 text-sm text-black/58">
                                              {post.title_translated}
                                            </p>
                                          ) : null}
                                          <div className="mt-3 flex flex-wrap gap-2 text-xs text-black/55">
                                            <span>{post.subreddit}</span>
                                            <span>•</span>
                                            <span>{new Date(post.post_timestamp).toLocaleString()}</span>
                                          </div>
                                          <p className="mt-3 text-sm leading-6 text-black/72">
                                            {post.summary}
                                          </p>
                                          <div className="mt-3 grid gap-3 md:grid-cols-3">
                                            <div>
                                              <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-black/45">
                                                Bullish factors
                                              </p>
                                              <p className="mt-1 text-sm text-black/70">
                                                {post.bullish_factors.join(", ") || "None"}
                                              </p>
                                            </div>
                                            <div>
                                              <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-black/45">
                                                Bearish factors
                                              </p>
                                              <p className="mt-1 text-sm text-black/70">
                                                {post.bearish_factors.join(", ") || "None"}
                                              </p>
                                            </div>
                                            <div>
                                              <p className="font-mono text-[11px] uppercase tracking-[0.14em] text-black/45">
                                                Risk flags
                                              </p>
                                              <p className="mt-1 text-sm text-black/70">
                                                {post.risk_flags.join(", ") || "None"}
                                              </p>
                                            </div>
                                          </div>
                                          <div className="mt-4 grid gap-3 md:grid-cols-5">
                                            {Object.entries(post.historical_results).map(([key, value]) => (
                                              <div
                                                key={key}
                                                className="rounded-2xl border border-black/8 bg-[#faf5ea] px-3 py-3"
                                              >
                                                <p className="font-mono text-[11px] uppercase tracking-[0.12em] text-black/40">
                                                  {key.replaceAll("_", " ")}
                                                </p>
                                                <p className="mt-1 font-mono text-sm">{value}</p>
                                              </div>
                                            ))}
                                          </div>
                                          <p className="mt-3 text-sm text-black/65">
                                            {post.why_this_score}
                                          </p>
                                        </article>
                                      ))}
                                    </div>
                                  </div>

                                  <div className="space-y-4">
                                    <div className="rounded-[24px] border border-black/8 bg-white p-5">
                                      <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-black/45">
                                        Historical similar-post results
                                      </p>
                                      <div className="mt-4 grid gap-3">
                                        {Object.entries(detail.historical_summary).map(([key, value]) => (
                                          <div
                                            key={key}
                                            className="flex items-center justify-between rounded-2xl border border-black/8 bg-[#faf5ea] px-4 py-3"
                                          >
                                            <span className="text-sm text-black/64">
                                              {key.replaceAll("_", " ")}
                                            </span>
                                            <span className="font-mono text-sm">{value}</span>
                                          </div>
                                        ))}
                                      </div>
                                    </div>
                                    <div className="rounded-[24px] border border-black/8 bg-white p-5">
                                      <p className="font-mono text-[11px] uppercase tracking-[0.16em] text-black/45">
                                        Coverage
                                      </p>
                                      <div className="mt-3 flex flex-wrap gap-2">
                                        {row.subreddits.map((subreddit) => (
                                          <span
                                            key={subreddit}
                                            className="rounded-full border border-black/10 bg-[#f9f2e3] px-3 py-1 text-xs"
                                          >
                                            {subreddit}
                                          </span>
                                        ))}
                                      </div>
                                      <p className="mt-4 text-sm leading-6 text-black/67">
                                        Confidence is capped by sample size. High confidence is
                                        only possible after 30+ similar historical posts.
                                      </p>
                                    </div>
                                  </div>
                                </div>
                              )}
                            </td>
                          </tr>
                        ) : null}
                      </Fragment>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </main>
  );
}
