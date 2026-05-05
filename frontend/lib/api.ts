import { getSupabaseBrowserClient } from "@/lib/supabase/client";
import type {
  DashboardFilters,
  DashboardResponse,
  DashboardRow,
  TickerDetail,
  TickerPostContext,
} from "@/lib/types";

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "");

function dateThreshold(window: DashboardFilters["window"]) {
  const today = new Date();
  const thresholds: Record<DashboardFilters["window"], number> = {
    Today: 0,
    "3D": 3,
    "7D": 7,
    "30D": 30,
  };
  const next = new Date(today);
  next.setDate(today.getDate() - thresholds[window]);
  return next.toISOString();
}

export async function fetchDashboard(filters: DashboardFilters): Promise<DashboardResponse> {
  if (apiBaseUrl) {
    const params = new URLSearchParams({
      window: filters.window,
      min_signal: String(filters.minSignal),
    });
    if (filters.subreddit) {
      params.set("subreddit", filters.subreddit);
    }
    if (filters.search) {
      params.set("search", filters.search);
    }
    const response = await fetch(`${apiBaseUrl}/api/dashboard?${params.toString()}`, {
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error("Failed to load dashboard data.");
    }
    return response.json();
  }

  const supabase = getSupabaseBrowserClient();
  const { data, error } = await supabase
    .from("dashboard_rows")
    .select("*")
    .gte("signal_date", dateThreshold(filters.window))
    .order("signal_score", { ascending: false });

  if (error) {
    throw error;
  }

  let rows = (data ?? []) as DashboardRow[];
  if (filters.subreddit) {
    rows = rows.filter((row) => row.subreddits?.includes(filters.subreddit));
  }
  if (filters.search) {
    const needle = filters.search.toLowerCase();
    rows = rows.filter(
      (row) =>
        row.ticker.toLowerCase().includes(needle) ||
        row.company.toLowerCase().includes(needle),
    );
  }
  rows = rows.filter((row) => row.signal_score >= filters.minSignal);
  return { rows, warnings: [] };
}

export async function fetchTickerDetail(ticker: string): Promise<TickerDetail> {
  if (apiBaseUrl) {
    const response = await fetch(`${apiBaseUrl}/api/ticker/${ticker}`, { cache: "no-store" });
    if (!response.ok) {
      throw new Error("Failed to load ticker detail.");
    }
    return response.json();
  }

  const supabase = getSupabaseBrowserClient();
  const [{ data: signalRows, error: signalError }, { data: contextRows, error: contextError }] =
    await Promise.all([
      supabase
        .from("dashboard_rows")
        .select("*")
        .eq("ticker", ticker)
        .order("signal_date", { ascending: false })
        .limit(1),
      supabase
        .from("ticker_post_context")
        .select("*")
        .eq("ticker", ticker)
        .order("post_timestamp", { ascending: false })
        .limit(6),
    ]);

  if (signalError) {
    throw signalError;
  }
  if (contextError) {
    throw contextError;
  }
  if (!signalRows?.length) {
    throw new Error("Ticker not found.");
  }

  const signal = signalRows[0] as DashboardRow;
  const posts = (contextRows ?? []) as TickerPostContext[];
  const historical = posts.filter((post) => typeof post.return_5d === "number");
  const avg5d =
    historical.length > 0
      ? historical.reduce((sum, post) => sum + (post.return_5d ?? 0), 0) / historical.length
      : 0;
  const downsideRate =
    historical.length > 0
      ? historical.filter((post) => (post.return_5d ?? 0) < -0.05).length / historical.length
      : 0;

  return {
    ticker: signal.ticker,
    company: signal.company,
    current_price: signal.current_price,
    signal_score: signal.signal_score,
    risk_score: signal.risk_score,
    confidence: signal.confidence,
    label: signal.label,
    one_line_reason: signal.one_line_reason,
    explanation: `${signal.ticker} has a ${signal.signal_score.toFixed(1)} signal score with ${signal.historical_win_rate.toFixed(1)}% historical 5D wins across ${signal.sample_size} similar posts.`,
    recent_posts: posts.map((post) => ({
      reddit_id: post.reddit_id,
      ticker: post.ticker,
      title_original: post.title_original,
      title_translated: post.title_translated,
      subreddit: post.subreddit,
      post_timestamp: post.post_timestamp,
      summary: post.summary,
      bullish_factors: post.bullish_factors ?? [],
      bearish_factors: post.bearish_factors ?? [],
      risk_flags: post.risk_flags ?? [],
      historical_results: {
        return_1d: Number(((post.return_1d ?? 0) * 100).toFixed(2)),
        return_3d: Number(((post.return_3d ?? 0) * 100).toFixed(2)),
        return_5d: Number(((post.return_5d ?? 0) * 100).toFixed(2)),
        return_10d: Number(((post.return_10d ?? 0) * 100).toFixed(2)),
      },
      why_this_score: `Sentiment ${post.sentiment_score.toFixed(2)}, hype ${post.hype_score.toFixed(2)}, catalyst ${post.catalyst_score.toFixed(2)}, engagement ${post.engagement_score.toFixed(2)}.`,
    })),
    historical_summary: {
      historical_win_rate_5d: signal.historical_win_rate,
      avg_return_5d_after_similar_posts: Number((avg5d * 100).toFixed(2)),
      downside_rate_5d: Number((downsideRate * 100).toFixed(2)),
      sample_size: signal.sample_size,
    },
    warnings: [],
  };
}

