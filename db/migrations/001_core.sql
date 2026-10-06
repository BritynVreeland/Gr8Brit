-- 001_core.sql — MVP schema (see docs/DATA_MODEL.md)
-- Enumerations are TEXT + CHECK constraints so vocabularies can evolve with a migration, not a type rewrite.

create extension if not exists pgcrypto;
create extension if not exists vector;

-- ---------------------------------------------------------------------------
-- Operations
-- ---------------------------------------------------------------------------
create table pipeline_runs (
  id uuid primary key default gen_random_uuid(),
  cycle_id text,
  stage text not null,
  status text not null default 'running' check (status in ('running','succeeded','failed')),
  config_hash text,
  git_sha text,
  params jsonb not null default '{}',
  error text,
  started_at timestamptz not null default now(),
  finished_at timestamptz
);

create table llm_calls (
  id uuid primary key default gen_random_uuid(),
  pipeline_run_id uuid references pipeline_runs(id),
  stage text not null,
  model text not null,
  prompt_key text not null,
  prompt_version text not null,
  input_tokens int,
  output_tokens int,
  cache_read_tokens int,
  cache_write_tokens int,
  cost_usd numeric(10,5),
  latency_ms int,
  batch_id text,
  stop_reason text,
  status text not null check (status in ('succeeded','failed','refused','invalid_output')),
  error text,
  created_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Business knowledge
-- ---------------------------------------------------------------------------
create table accounts (
  id uuid primary key default gen_random_uuid(),
  key text unique not null,
  platform text not null default 'instagram',
  name text not null,
  handle text,
  ig_user_id text unique,
  role text not null check (role in ('personal_brand','company')),
  primary_objectives text[] not null default '{}',
  weekly_feed_target int,
  weekly_feed_min int,
  stories_per_week int,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create table offers (
  id uuid primary key default gen_random_uuid(),
  key text unique not null,
  name text not null,
  description text,
  price_range text,
  url text,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create table taxonomy_nodes (
  id uuid primary key default gen_random_uuid(),
  key text unique not null,
  parent_id uuid references taxonomy_nodes(id),
  label text not null,
  description text,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create table facts_registry (
  id uuid primary key default gen_random_uuid(),
  claim text not null,
  value text,
  source_url text,
  volatility text not null default 'seasonal' check (volatility in ('stable','seasonal','volatile')),
  last_verified_at timestamptz,
  verified_by text,
  expires_at timestamptz,
  created_at timestamptz not null default now()
);

create table brand_rules (
  id uuid primary key default gen_random_uuid(),
  rule_type text not null check (rule_type in ('banned_phrase','voice','sensitive_topic','disclosure')),
  value text not null,
  note text,
  active boolean not null default true,
  unique (rule_type, value)
);

-- ---------------------------------------------------------------------------
-- Collection & raw evidence (immutable layer)
-- ---------------------------------------------------------------------------
create table sources (
  id uuid primary key default gen_random_uuid(),
  key text unique not null,
  name text not null,
  access_method text not null check (access_method in
    ('official_api','mcp','authenticated_integration','third_party_api','manual_export','manual_capture','webhook')),
  terms_basis text not null,
  retention_days int,
  is_first_party boolean not null default false,
  active boolean not null default true,
  created_at timestamptz not null default now()
);

create table collection_runs (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references sources(id),
  pipeline_run_id uuid references pipeline_runs(id),
  status text not null default 'running' check (status in ('running','succeeded','failed','partial')),
  params jsonb not null default '{}',
  items_fetched int not null default 0,
  error text,
  started_at timestamptz not null default now(),
  finished_at timestamptz
);

create table raw_documents (
  id uuid primary key default gen_random_uuid(),
  source_id uuid not null references sources(id),
  collection_run_id uuid references collection_runs(id),
  external_id text not null,
  parent_external_id text,
  url text,
  author_hash text,
  author_meta jsonb not null default '{}',
  published_at timestamptz,
  fetched_at timestamptz not null default now(),
  title text,
  body_text text not null,
  raw_payload jsonb,
  raw_object_path text,
  content_hash text not null,
  engagement jsonb not null default '{}',
  language text,
  capture_method text not null check (capture_method in
    ('api','manual_paste','manual_url','export_file','webhook')),
  captured_by text,
  capture_note text,
  relevance jsonb,
  deleted_at_source boolean not null default false,
  purge_after date,
  unique (source_id, external_id)
);
create index raw_documents_published_idx on raw_documents (published_at);

-- Raw documents are immutable: only compliance/relevance bookkeeping columns may change.
create or replace function raw_documents_immutable() returns trigger as $$
begin
  if new.body_text is distinct from old.body_text
     or new.content_hash is distinct from old.content_hash
     or new.raw_payload is distinct from old.raw_payload
     or new.external_id is distinct from old.external_id
     or new.source_id is distinct from old.source_id then
    raise exception 'raw_documents content is immutable (id=%)', old.id;
  end if;
  return new;
end $$ language plpgsql;

create trigger raw_documents_immutable_trg
  before update on raw_documents
  for each row execute function raw_documents_immutable();

-- ---------------------------------------------------------------------------
-- Evidence (atomic signals)
-- ---------------------------------------------------------------------------
create table evidence_items (
  id uuid primary key default gen_random_uuid(),
  raw_document_id uuid not null references raw_documents(id),
  signal_type text not null check (signal_type in
    ('question','fear','objection','desire','excitement','misconception','planning_problem',
     'recommendation_request','experience_report','complaint','purchase_intent','resource_request',
     'cultural_curiosity')),
  verbatim_quote text not null,
  quote_start int not null,
  quote_end int not null,
  normalized_statement text not null,
  topic_node_id uuid references taxonomy_nodes(id),
  subtopic_node_ids uuid[] not null default '{}',
  travel_stage text not null default 'unknown' check (travel_stage in
    ('dreaming','considering','planning','booked','in_trip','post_trip','unknown')),
  emotions text[] not null default '{}',
  emotion_intensity smallint check (emotion_intensity between 1 and 5),
  purchase_intent smallint not null default 0 check (purchase_intent between 0 and 3),
  offer_fit jsonb not null default '[]',
  resource_signal boolean not null default false,
  resource_hint text,
  us_likelihood real check (us_likelihood between 0 and 1),
  trip_context jsonb not null default '{}',
  extraction_confidence real check (extraction_confidence between 0 and 1),
  pipeline_run_id uuid references pipeline_runs(id),
  model text,
  prompt_version text,
  created_at timestamptz not null default now(),
  check (quote_end > quote_start)
);
create index evidence_items_dims_idx on evidence_items (topic_node_id, travel_stage, signal_type);

create table evidence_embeddings (
  evidence_item_id uuid primary key references evidence_items(id) on delete cascade,
  model text not null,
  embedding vector(1024) not null,
  created_at timestamptz not null default now()
);
create index evidence_embeddings_hnsw on evidence_embeddings using hnsw (embedding vector_cosine_ops);

create table audience_phrases (
  id uuid primary key default gen_random_uuid(),
  evidence_item_id uuid not null references evidence_items(id) on delete cascade,
  phrase text not null,
  phrase_type text not null check (phrase_type in
    ('hook_candidate','objection_wording','desire_wording','fear_wording'))
);

-- ---------------------------------------------------------------------------
-- Understanding
-- ---------------------------------------------------------------------------
create table clusters (
  id uuid primary key default gen_random_uuid(),
  label text,
  canonical_question text,
  summary text,
  status text not null default 'active' check (status in ('active','merged','dormant')),
  merged_into_id uuid references clusters(id),
  centroid vector(1024),
  taxonomy_node_id uuid references taxonomy_nodes(id),
  first_seen_at timestamptz,
  last_seen_at timestamptz,
  pipeline_run_id uuid references pipeline_runs(id),
  created_at timestamptz not null default now()
);

create table cluster_members (
  cluster_id uuid not null references clusters(id),
  evidence_item_id uuid not null references evidence_items(id),
  membership_prob real,
  assigned_run_id uuid references pipeline_runs(id),
  primary key (cluster_id, evidence_item_id)
);

create table cluster_snapshots (
  cluster_id uuid not null references clusters(id),
  week_start date not null,
  signal_count int not null,
  independent_author_count int not null,
  source_count int not null,
  first_party_count int not null,
  mean_emotion_intensity real,
  purchase_intent_dist jsonb,
  travel_stage_dist jsonb,
  engagement_sum numeric,
  velocity_z real,
  baseline_weeks int not null default 0,
  primary key (cluster_id, week_start)
);

-- ---------------------------------------------------------------------------
-- Market / category content
-- ---------------------------------------------------------------------------
create table market_content (
  id uuid primary key default gen_random_uuid(),
  platform text not null,
  account_handle text,
  external_id text not null,
  url text,
  published_at timestamptz,
  caption_or_title text,
  format text,
  public_metrics jsonb not null default '{}',
  hook_text text,
  audio text,
  relative_performance real,
  discovered_via text check (discovered_via in ('hashtag','watchlist','swipe_file','youtube_search','youtube_channel')),
  swipe_note text,
  capture_method text not null default 'api',
  topic_node_ids uuid[] not null default '{}',
  angle_summary text,
  embedding vector(1024),
  fetched_at timestamptz not null default now(),
  unique (platform, external_id)
);

-- ---------------------------------------------------------------------------
-- Opportunities → concepts → recommendations
-- ---------------------------------------------------------------------------
create table opportunities (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  opportunity_type text not null check (opportunity_type in
    ('content','resource','offer_messaging','faq_page','experiment')),
  audience_need text not null,
  why_now text,
  bb_advantage text,
  primary_offer_key text references offers(key),
  offer_fit text check (offer_fit in ('natural','plausible','none')),
  measured_factors jsonb not null default '{}',
  evidence_strength text check (evidence_strength in ('anecdotal','emerging','established')),
  status text not null default 'open',
  pipeline_run_id uuid references pipeline_runs(id),
  created_at timestamptz not null default now()
);

create table opportunity_clusters (
  opportunity_id uuid references opportunities(id) on delete cascade,
  cluster_id uuid references clusters(id),
  primary key (opportunity_id, cluster_id)
);

create table opportunity_evidence (
  opportunity_id uuid references opportunities(id) on delete cascade,
  evidence_item_id uuid references evidence_items(id),
  role text not null default 'supporting' check (role in ('primary','supporting','counter')),
  primary key (opportunity_id, evidence_item_id)
);

create table concepts (
  id uuid primary key default gen_random_uuid(),
  opportunity_id uuid references opportunities(id),
  target_account_key text references accounts(key),
  format text not null check (format in ('reel','carousel','story_sequence','static','live','guide_page','pdf','email')),
  objective text not null check (objective in
    ('reach','trust','authority','education','engagement','lead','conversion','experiment','storytelling','proof')),
  basis text not null default 'evidence' check (basis in ('evidence','experiment','business_priority')),
  basis_rationale text,
  angle text not null,
  hook_options jsonb not null default '[]',
  outline text,
  cta text,
  perspective_used text check (perspective_used in ('american','local','both')),
  required_assets jsonb not null default '[]',
  similar_past_asset_ids uuid[] not null default '{}',
  novelty_sim real,
  status text not null default 'candidate' check (status in ('candidate','rejected','transformed','selected')),
  pipeline_run_id uuid references pipeline_runs(id),
  created_at timestamptz not null default now()
);

create table concept_scores (
  id uuid primary key default gen_random_uuid(),
  concept_id uuid not null references concepts(id) on delete cascade,
  dimension text not null,
  value real not null,
  scale text not null,
  rationale text,
  evidence_ids uuid[] not null default '{}',
  scorer text not null check (scorer in ('code','llm')),
  scoring_version text not null,
  created_at timestamptz not null default now()
);

create table critiques (
  id uuid primary key default gen_random_uuid(),
  concept_id uuid not null references concepts(id) on delete cascade,
  verdict text not null check (verdict in ('accept','transform','reject')),
  failure_modes text[] not null default '{}',
  any_creator_test text check (any_creator_test in ('pass','fail')),
  notes text,
  transformed_concept_id uuid references concepts(id),
  critic_version text not null,
  created_at timestamptz not null default now()
);

create table recommendations (
  id uuid primary key default gen_random_uuid(),
  concept_id uuid not null references concepts(id),
  cycle_id text not null,
  account_key text references accounts(key),
  rank int,
  portfolio_slot text,
  why_it_exists text not null,
  expected_outcome jsonb not null default '{}',
  status text not null default 'proposed' check (status in ('proposed','approved','rejected','modified','deferred','produced')),
  created_at timestamptz not null default now()
);

create table decisions (
  id uuid primary key default gen_random_uuid(),
  object_type text not null,
  object_id uuid not null,
  decided_by text not null,
  decision text not null check (decision in ('approve','reject','modify','defer')),
  reason_codes text[] not null default '{}',
  comment text,
  decided_at timestamptz not null default now()
);

-- ---------------------------------------------------------------------------
-- Content memory
-- ---------------------------------------------------------------------------
create table assets (
  id uuid primary key default gen_random_uuid(),
  platform text not null default 'instagram',
  external_id text not null,
  permalink text,
  published_at timestamptz,
  owner_account_id uuid references accounts(id),
  collaborator_account_ids uuid[] not null default '{}',
  media_type text,
  media_product_type text,
  format text,
  duration_s real,
  topic_node_id uuid references taxonomy_nodes(id),
  subtopic_node_ids uuid[] not null default '{}',
  hook_text text,
  hook_type text,
  angle text,
  perspective_used text,
  script text,
  caption text,
  on_screen_text text,
  cta_type text,
  cta_text text,
  manychat_keyword text,
  offer_key text references offers(key),
  resource_id uuid,
  objective text,
  recommendation_id uuid references recommendations(id),
  campaign_id uuid,
  experiment_arm_id uuid,
  production_meta jsonb not null default '{}',
  labels_source text check (labels_source in ('manual','llm_backfill','system')),
  label_confidence real,
  raw_payload jsonb,
  embedding vector(1024),
  first_seen_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (platform, external_id)
);

create table asset_metric_snapshots (
  id uuid primary key default gen_random_uuid(),
  asset_id uuid not null references assets(id) on delete cascade,
  captured_at timestamptz not null default now(),
  age_hours real,
  metrics jsonb not null,
  views bigint,
  reach bigint,
  likes bigint,
  comments bigint,
  saves bigint,
  shares bigint,
  reposts bigint,
  follows bigint,
  profile_visits bigint,
  total_interactions bigint,
  avg_watch_time_s real,
  total_watch_time_s real,
  skip_rate real,
  follower_count_at_capture bigint
);
create index asset_metric_snapshots_asset_idx on asset_metric_snapshots (asset_id, captured_at);

create table asset_comments (
  id uuid primary key default gen_random_uuid(),
  asset_id uuid not null references assets(id) on delete cascade,
  raw_document_id uuid references raw_documents(id),
  external_id text not null unique,
  parent_external_id text,
  is_own_reply boolean not null default false,
  published_at timestamptz,
  like_count int
);

create table reports (
  id uuid primary key default gen_random_uuid(),
  cycle_id text not null,
  report_type text not null default 'weekly',
  html_path text,
  markdown text,
  stats jsonb not null default '{}',
  created_at timestamptz not null default now()
);

-- Normalized performance at a glance: latest snapshot per asset.
create view v_asset_latest_metrics as
select distinct on (s.asset_id)
  a.id as asset_id, a.permalink, a.published_at, a.format, a.media_product_type,
  acc.key as owner_account_key,
  s.captured_at, s.age_hours, s.views, s.reach, s.likes, s.comments, s.saves, s.shares,
  s.follows, s.profile_visits, s.avg_watch_time_s, s.skip_rate,
  case when s.reach > 0 then s.saves::real / s.reach end as save_rate,
  case when s.reach > 0 then s.shares::real / s.reach end as share_rate,
  case when s.reach > 0 then 1000.0 * s.follows / s.reach end as follows_per_1k_reach,
  case when a.duration_s > 0 then s.avg_watch_time_s / a.duration_s end as completion_proxy
from asset_metric_snapshots s
join assets a on a.id = s.asset_id
left join accounts acc on acc.id = a.owner_account_id
order by s.asset_id, s.captured_at desc;
