# Brit & Berat Content Intelligence OS

Evidence-grounded content intelligence for Brit & Berat (Istanbul travel). Start with `CLAUDE.md`,
then `docs/` (architecture, data model, scoring, roadmap, MVP spec). Setup steps: `docs/SETUP.md`.

```bash
uv sync
cp .env.example .env            # fill in (never commit .env)
uv run bbos db migrate
uv run bbos seed                # load config/*.yaml
uv run bbos doctor              # check credentials & connectivity
uv run bbos inbox add --captured-by brit --text "..." --url "..." --note "why it matters"
uv run bbos ig discover         # after setting handles in config/accounts.yaml
uv run bbos ig sync --max-media 50
```

Tests: `TEST_DATABASE_URL=postgresql://... uv run pytest` (needs Postgres with pgvector).
