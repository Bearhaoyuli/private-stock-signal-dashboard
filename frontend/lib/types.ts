export type DashboardRow = {
  signal_date?: string;
  ticker: string;
  company: string;
  current_price: number;
  change_1d_pct: number;
  change_5d_pct: number;
  reddit_post_count_today: number;
  mention_spike: number;
  sentiment: number;
  historical_win_rate: number;
  avg_5d_return_after_similar_posts: number;
  signal_score: number;
  risk_score: number;
  confidence: number;
  label: string;
  one_line_reason: string;
  subreddits: string[];
  sample_size: number;
};

export type TickerPostContext = {
  ticker: string;
  reddit_id: string;
  subreddit: string;
  title_original: string;
  title_translated?: string | null;
  body_original?: string | null;
  body_translated?: string | null;
  post_timestamp: string;
  summary: string;
  bullish_factors: string[];
  bearish_factors: string[];
  risk_flags: string[];
  sentiment_score: number;
  bullish_score: number;
  bearish_score: number;
  hype_score: number;
  catalyst_score: number;
  engagement_score: number;
  return_1d?: number | null;
  return_3d?: number | null;
  return_5d?: number | null;
  return_10d?: number | null;
  max_drawdown_10d?: number | null;
  beat_spy_5d?: boolean | null;
};

export type TickerDetail = {
  ticker: string;
  company: string;
  current_price: number;
  signal_score: number;
  risk_score: number;
  confidence: number;
  label: string;
  one_line_reason: string;
  explanation: string;
  recent_posts: Array<{
    reddit_id: string;
    ticker: string;
    title_original: string;
    title_translated?: string | null;
    subreddit: string;
    post_timestamp: string;
    summary: string;
    bullish_factors: string[];
    bearish_factors: string[];
    risk_flags: string[];
    historical_results: Record<string, number>;
    why_this_score: string;
  }>;
  historical_summary: Record<string, number>;
  warnings: string[];
};

export type DashboardResponse = {
  rows: DashboardRow[];
  warnings: string[];
  generated_at?: string;
};

export type DashboardFilters = {
  subreddit: string;
  window: "Today" | "3D" | "7D" | "30D";
  minSignal: number;
  search: string;
};

