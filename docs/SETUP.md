# Setup Guide — accounts & credentials for the MVP

Plain-language steps for Brit. Do them in order. **Never paste keys, tokens, or passwords into
chat.** Each one goes into two places:

- **GitHub repository secrets** (Settings → Secrets and variables → Actions → New repository secret).
  The weekly jobs read them from here.
- **The Claude Code cloud environment's settings** (the environment menu in the session's title bar →
  Edit → environment variables / API credentials), so Claude Code sessions can run and test the
  system. A new session picks them up.

Use exactly the variable names shown below.

## 0. Network access for Claude Code sessions (one-time)

The cloud environment currently blocks the APIs we need. In the environment's settings → **Network
access** → Custom, add these allowed domains and keep the default package-manager list:
`graph.facebook.com`, `*.supabase.co`, `supabase.com`, `api.voyageai.com`, `www.googleapis.com`,
`youtube.googleapis.com`, `api.stripe.com`, `*.api-us1.com` (ActiveCampaign).
Docs: https://code.claude.com/docs/en/cloud-environments#network-access

## 1. Supabase (database) — ~10 minutes

1. Create an account at supabase.com → **New project** named `bb-content-os`, region **East US**,
   strong database password (save it in your password manager).
2. Project Settings → **Database** → Connection string → **URI** (Session pooler). Replace the password placeholder.
   - Secret name: `DATABASE_URL`
3. Project Settings → **API**: copy the Project URL and the `service_role` key.
   - `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`

## 2. Anthropic API (the AI) — ~5 minutes

1. console.anthropic.com → create an organization for Brit & Berat → add billing → set a **monthly
   spend limit** (suggest $150 to start).
2. API Keys → Create key named `bb-content-os`.
   - `ANTHROPIC_API_KEY`

## 3. Voyage AI (text embeddings) — ~5 minutes

voyageai.com → sign up → API key. - `VOYAGE_API_KEY`

## 4. Instagram — both accounts — ~30–60 minutes

Prerequisites for **each** of Brit in Istanbul and Brit & Berat:
- The Instagram account is a **Professional** account (Settings → Account type and tools → switch to
  Professional; Creator for Brit in Istanbul, Business for Brit & Berat).
- It is **linked to a Facebook Page** (Instagram → Settings → Accounts Center / Sharing → connect a
  Page; create a simple Page for each brand if needed). You must be an admin of both Pages.

Then:
1. Go to developers.facebook.com → My Apps → **Create App** → use case "Other" → type **Business** →
   name `BB Content OS`.
2. Add the product **Instagram** → choose **API setup with Facebook login**.
3. Open **Graph API Explorer** (Tools menu), select the app, and add permissions:
   `instagram_basic`, `instagram_manage_insights`, `instagram_manage_comments`,
   `pages_show_list`, `pages_read_engagement`, `business_management`.
   Click **Generate Access Token** and approve **both** Pages / Instagram accounts.
4. **Preferred — a token that doesn't expire:** in Meta Business Suite → Settings → Users → **System
   users** → Add (Admin) → assign both Pages/Instagram accounts and the app → **Generate token** with the
   permissions above, expiration **Never**.
   **Fallback:** exchange the Explorer token for a **long-lived token** (60 days) in the Access Token
   Debugger → "Extend Access Token" (Claude will remind you before it expires).
   - `META_ACCESS_TOKEN`
   - `META_APP_ID`, `META_APP_SECRET` (App settings → Basic)
5. Tell Claude the two **Instagram handles** (just the handles in chat — those aren't secret). Claude
   finds the account IDs automatically (`bbos ig discover`).

## 4b. Salt for anonymizing usernames

Generate any long random string (e.g. from your password manager) → secret `AUTHOR_HASH_SALT`.
Never change it afterwards (changing it breaks "independent author" counts).

Hashtag Search (for the Istanbul category research) may require extra permission
(`instagram_basic` + Hashtag Search feature). If Meta asks for App Review, we'll do it together;
your own-account data works without it.

## 5. YouTube Data API — ~10 minutes

console.cloud.google.com → New project `bb-content-os` → APIs & Services → Enable **YouTube Data API v3**
→ Credentials → Create **API key** → restrict it to YouTube Data API v3.
- `YOUTUBE_API_KEY`

## 6. Phase 2 (not needed yet — listed so nothing surprises you)

| Service | What to create | Secret names |
|---|---|---|
| Stripe | Restricted key (read: Checkout Sessions, Charges, Customers) + webhook endpoint secret | `STRIPE_RESTRICTED_KEY`, `STRIPE_WEBHOOK_SECRET` |
| ActiveCampaign | Settings → Developer → API URL + key | `ACTIVECAMPAIGN_API_URL`, `ACTIVECAMPAIGN_API_KEY` |
| ManyChat (Pro) | Settings → API → generate token (one per account if both use ManyChat) | `MANYCHAT_TOKEN_BIT`, `MANYCHAT_TOKEN_BB` |
| Lovable website | Small change so links' UTM/ManyChat IDs pass into Stripe Checkout metadata (Claude will write the exact prompt) | — |

## 7. Content Claude needs from you (not secrets — chat is fine)

- The two Instagram handles.
- Offer details for `config/offers.yaml`: name, 1–2 sentence description, price range, booking URL.
- 5–10 sentences on how you talk ("we say…", "we never say…") for `config/brand_voice.md`.
- Over the first two weeks: **swipe file** links (great Istanbul/Turkey posts + why), and a creator
  **watchlist** — Claude will propose candidates from hashtag/YouTube data for you to approve.
- 20–50 anonymized customer questions (from DMs, emails, WhatsApp) to seed the Evidence Inbox.
