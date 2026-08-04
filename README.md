# Loupe

A conversational curator agent over an editorial photo archive. Describe a
brief in plain language — a campaign, a mood, a story you're building — and
an LLM agent translates it into structured + semantic search, grounded in
the photographer's own Lightroom metadata (EXIF, star ratings, keywords,
IPTC captions), and answers conversationally, citing specific frames.

Built and tested against the author's own Lightroom catalog of editorial
and documentary work.

## License

The code in this repository is MIT licensed (see `LICENSE`). The photo
archive itself — images, captions, keywords, and EXIF/IPTC metadata — is not
distributed here and remains © Eric Cortes, all rights reserved.

## Stack

- **Postgres + pgvector** — metadata, keywords, collections, and embeddings in one schema
- **LangChain (`create_agent`) + OpenAI (`gpt-4o-mini`)** — two-agent pipeline: a *planner* agent (`agents/planner.py`) decomposes a brief into `search_archive` tool calls (semantic query + EXIF/keyword/collection filters); a *curator* agent (`agents/curator.py`) answers grounded only in what was retrieved, or hands refinement instructions back to the planner for one more round if the results are too thin — orchestrated in `agents/orchestrator.py`
- **FastAPI + Vite/React/Tailwind chat UI** — `/chat` endpoint, conversation history kept client-side
- **Docker Compose** — Postgres + API for local dev
- **GitHub Actions CI** — spins up Postgres, applies the schema, lints (ruff), runs pytest

## Status

- Metadata ingestion from the `.lrcat` catalog — done, verified against a real production catalog (`ingest/lrcat_reader.py`)
- Baseline keyword-retrieval eval (full-text search, no ML) — done, see `eval/results/keyword_retrieval_baseline.csv`
- Caption/keyword text embeddings (OpenAI) + pgvector semantic search — implemented (`ingest/embed_captions.py`), not yet run against the live archive
- Planner/curator agent pipeline + FastAPI + Docker + CI — implemented and tested (orchestration logic covered by mocked unit tests in `tests/test_orchestrator.py`); needs an API key for the configured LLM provider (OpenAI by default) to actually call the model
- SigLIP image embeddings (real pixel access, not just captions) — blocked on source images not currently being mounted/accessible

## Running locally

```
cp .env.example .env   # fill in the API key for your LLM provider (OpenAI by default)
docker compose up -d   # Postgres + pgvector, schema auto-applied

python -m venv .venv && .venv/bin/pip install -r requirements.txt

# one-time ingestion from your Lightroom catalog
.venv/bin/python ingest/lrcat_reader.py "/path/to/catalog.lrcat"
.venv/bin/python ingest/embed_captions.py

cd frontend && pnpm install && pnpm run build && cd ..   # builds into api/static/

.venv/bin/uvicorn api.main:app --port 8000
```

Open http://localhost:8000

For frontend development with hot reload, run `pnpm --dir frontend dev` (port
5173) alongside the API on port 8000 — Vite proxies `/chat` and `/health` to
it. Rerun `pnpm run build` to refresh `api/static/` for the single-origin
FastAPI setup above.

## Eval

```
.venv/bin/python eval/keyword_retrieval_eval.py
```

Holds out Lightroom keywords, uses each as a query against the full-text
baseline (captions only — keywords are never indexed), and reports
precision@k, recall@k, and MRR against the images actually tagged with each
keyword. Numbers are honestly low right now: only a small minority of images
have a caption at all, so this baseline is really measuring caption coverage.
It's the number embeddings need to beat.
