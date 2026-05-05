create extension if not exists pgcrypto;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null unique,
  created_at timestamptz not null default timezone('utc', now())
);

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, email)
  values (new.id, new.email)
  on conflict (id) do update
  set email = excluded.email;
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute procedure public.handle_new_user();

create table if not exists public.stocks (
  id uuid primary key default gen_random_uuid(),
  ticker text not null unique,
  company_name text not null,
  exchange text,
  sector text,
  market_cap numeric,
  avg_volume numeric,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.reddit_posts (
  id uuid primary key default gen_random_uuid(),
  reddit_id text not null unique,
  subreddit text not null,
  author text,
  title_original text not null,
  body_original text,
  title_translated text,
  body_translated text,
  detected_language text,
  url text,
  permalink text,
  score integer,
  upvote_ratio numeric,
  num_comments integer,
  created_utc timestamptz not null,
  collected_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.reddit_comments (
  id uuid primary key default gen_random_uuid(),
  reddit_comment_id text not null unique,
  reddit_post_id text not null references public.reddit_posts(reddit_id) on delete cascade,
  author text,
  body_original text not null,
  body_translated text,
  detected_language text,
  score integer,
  created_utc timestamptz not null,
  collected_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.ticker_mentions (
  id uuid primary key default gen_random_uuid(),
  ticker text not null references public.stocks(ticker) on delete cascade,
  reddit_post_id text not null references public.reddit_posts(reddit_id) on delete cascade,
  reddit_comment_id text references public.reddit_comments(reddit_comment_id) on delete cascade,
  mention_source text not null check (mention_source in ('post', 'comment')),
  mention_count integer not null default 1,
  created_utc timestamptz not null
);

create table if not exists public.stock_prices (
  id uuid primary key default gen_random_uuid(),
  ticker text not null references public.stocks(ticker) on delete cascade,
  price_date timestamptz not null,
  open numeric not null,
  high numeric not null,
  low numeric not null,
  close numeric not null,
  volume numeric not null,
  adjusted_close numeric not null,
  unique (ticker, price_date)
);

create table if not exists public.post_features (
  id uuid primary key default gen_random_uuid(),
  reddit_post_id text not null references public.reddit_posts(reddit_id) on delete cascade,
  ticker text not null references public.stocks(ticker) on delete cascade,
  text_length integer,
  title_length integer,
  num_comments integer,
  score integer,
  upvote_ratio numeric,
  engagement_score numeric,
  sentiment_score numeric,
  bullish_score numeric,
  bearish_score numeric,
  hype_score numeric,
  catalyst_score numeric,
  risk_language_score numeric,
  language text,
  subreddit text,
  created_utc timestamptz not null,
  summary text,
  bullish_factors jsonb not null default '[]'::jsonb,
  bearish_factors jsonb not null default '[]'::jsonb,
  risk_flags jsonb not null default '[]'::jsonb,
  unique (reddit_post_id, ticker)
);

create table if not exists public.historical_returns (
  id uuid primary key default gen_random_uuid(),
  reddit_post_id text not null references public.reddit_posts(reddit_id) on delete cascade,
  ticker text not null references public.stocks(ticker) on delete cascade,
  signal_date timestamptz not null,
  price_at_post numeric not null,
  return_1d numeric,
  return_3d numeric,
  return_5d numeric,
  return_10d numeric,
  max_drawdown_10d numeric,
  beat_spy_5d boolean,
  created_at timestamptz not null default timezone('utc', now()),
  unique (reddit_post_id, ticker)
);

create table if not exists public.daily_signals (
  id uuid primary key default gen_random_uuid(),
  signal_date timestamptz not null,
  ticker text not null references public.stocks(ticker) on delete cascade,
  current_price numeric not null,
  mention_count_today integer not null default 0,
  mention_count_7d_avg numeric not null default 0,
  mention_spike numeric not null default 0,
  sentiment_score numeric not null default 0,
  historical_win_rate_5d numeric not null default 0,
  avg_return_5d_after_similar_posts numeric not null default 0,
  signal_score numeric not null default 0,
  risk_score numeric not null default 0,
  confidence numeric not null default 0,
  label text not null,
  one_line_reason text not null,
  sample_size integer not null default 0,
  downside_rate_5d numeric not null default 0,
  cross_subreddit_confirmation numeric not null default 0,
  sentiment_label text,
  created_at timestamptz not null default timezone('utc', now()),
  unique (signal_date, ticker)
);

create index if not exists idx_reddit_posts_created_utc on public.reddit_posts(created_utc desc);
create index if not exists idx_ticker_mentions_ticker_created_utc on public.ticker_mentions(ticker, created_utc desc);
create index if not exists idx_post_features_ticker_created_utc on public.post_features(ticker, created_utc desc);
create index if not exists idx_historical_returns_ticker_signal_date on public.historical_returns(ticker, signal_date desc);
create index if not exists idx_daily_signals_signal_date_ticker on public.daily_signals(signal_date desc, ticker);
create index if not exists idx_stock_prices_ticker_date on public.stock_prices(ticker, price_date desc);

drop trigger if exists stocks_set_updated_at on public.stocks;
create trigger stocks_set_updated_at
before update on public.stocks
for each row execute procedure public.set_updated_at();

create or replace view public.dashboard_rows as
with latest_prices as (
  select
    sp.ticker,
    sp.close as current_price,
    lag(sp.close, 1) over (partition by sp.ticker order by sp.price_date) as prev_1d_close,
    lag(sp.close, 5) over (partition by sp.ticker order by sp.price_date) as prev_5d_close,
    row_number() over (partition by sp.ticker order by sp.price_date desc) as rn
  from public.stock_prices sp
)
select
  ds.signal_date,
  ds.ticker,
  s.company_name as company,
  lp.current_price,
  round(((lp.current_price / nullif(lp.prev_1d_close, 0)) - 1) * 100, 2) as change_1d_pct,
  round(((lp.current_price / nullif(lp.prev_5d_close, 0)) - 1) * 100, 2) as change_5d_pct,
  ds.mention_count_today as reddit_post_count_today,
  ds.mention_spike,
  ds.sentiment_score as sentiment,
  round(ds.historical_win_rate_5d * 100, 1) as historical_win_rate,
  round(ds.avg_return_5d_after_similar_posts * 100, 2) as avg_5d_return_after_similar_posts,
  ds.signal_score,
  ds.risk_score,
  ds.confidence,
  ds.label,
  ds.one_line_reason,
  ds.sample_size,
  coalesce(
    array(
      select distinct pf.subreddit
      from public.post_features pf
      where pf.ticker = ds.ticker
        and pf.created_utc::date = ds.signal_date::date
      order by 1
    ),
    array[]::text[]
  ) as subreddits
from public.daily_signals ds
join public.stocks s on s.ticker = ds.ticker
join latest_prices lp on lp.ticker = ds.ticker and lp.rn = 1;

create or replace view public.ticker_post_context as
select
  pf.ticker,
  rp.reddit_id,
  rp.subreddit,
  rp.title_original,
  rp.title_translated,
  rp.body_original,
  rp.body_translated,
  rp.created_utc as post_timestamp,
  pf.summary,
  pf.bullish_factors,
  pf.bearish_factors,
  pf.risk_flags,
  pf.sentiment_score,
  pf.bullish_score,
  pf.bearish_score,
  pf.hype_score,
  pf.catalyst_score,
  pf.engagement_score,
  hr.return_1d,
  hr.return_3d,
  hr.return_5d,
  hr.return_10d,
  hr.max_drawdown_10d,
  hr.beat_spy_5d
from public.post_features pf
join public.reddit_posts rp on rp.reddit_id = pf.reddit_post_id
left join public.historical_returns hr
  on hr.reddit_post_id = pf.reddit_post_id
 and hr.ticker = pf.ticker;

alter table public.profiles enable row level security;
alter table public.stocks enable row level security;
alter table public.reddit_posts enable row level security;
alter table public.reddit_comments enable row level security;
alter table public.ticker_mentions enable row level security;
alter table public.stock_prices enable row level security;
alter table public.post_features enable row level security;
alter table public.historical_returns enable row level security;
alter table public.daily_signals enable row level security;

create policy "profiles_select_self"
on public.profiles
for select
to authenticated
using (auth.uid() = id);

create policy "profiles_insert_self"
on public.profiles
for insert
to authenticated
with check (auth.uid() = id);

create policy "profiles_update_self"
on public.profiles
for update
to authenticated
using (auth.uid() = id)
with check (auth.uid() = id);

create policy "authenticated_read_stocks"
on public.stocks
for select
to authenticated
using (true);

create policy "authenticated_read_reddit_posts"
on public.reddit_posts
for select
to authenticated
using (true);

create policy "authenticated_read_reddit_comments"
on public.reddit_comments
for select
to authenticated
using (true);

create policy "authenticated_read_ticker_mentions"
on public.ticker_mentions
for select
to authenticated
using (true);

create policy "authenticated_read_stock_prices"
on public.stock_prices
for select
to authenticated
using (true);

create policy "authenticated_read_post_features"
on public.post_features
for select
to authenticated
using (true);

create policy "authenticated_read_historical_returns"
on public.historical_returns
for select
to authenticated
using (true);

create policy "authenticated_read_daily_signals"
on public.daily_signals
for select
to authenticated
using (true);
