# PayerGuard

Claims quality and risk monitoring MVP. **Start with [`MVP_CONTEXT.md`](./MVP_CONTEXT.md)** — it is the source of truth for what this project is, what data it uses, the target architecture, MVP scope, and the phased build order.

## Current state

This repo currently contains only:
- `MVP_CONTEXT.md` — the full project context/spec.
- A modular repo skeleton (stub files only, no business logic).
- Docker Compose for local dev (backend + Postgres; a `frontend` service is stubbed in but commented out until frontend code exists). No CI/CD, no cloud deployment yet.
- `.specify/` — spec-kit vendored in for spec-driven development (see below).

No pipeline, model, or API logic has been implemented yet. See `MVP_CONTEXT.md` Section 5 for the phase-by-phase build order.

## Spec-driven development (speckit)

Speckit is installed and ready to use — no setup step required.

- `.specify/memory/constitution.md` — PayerGuard's actual engineering
  principles (empirical model selection, no fabricated values,
  deterministic-first, HITL-before-write, temporal integrity, etc.), not a
  blank template.
- `.specify/templates/` — spec/plan/tasks/checklist templates plus the raw
  `speckit.*` command templates.
- `.specify/scripts/bash/` — the helper scripts those commands call.
- `.claude/skills/speckit-*/SKILL.md` — the 10 Claude Code slash commands:
  `/speckit.specify`, `/speckit.plan`, `/speckit.tasks`,
  `/speckit.implement`, `/speckit.clarify`, `/speckit.analyze`,
  `/speckit.checklist`, `/speckit.constitution`, `/speckit.converge`,
  `/speckit.taskstoissues`. Just open this folder in Claude Code and use
  them.

**Provenance, for whoever continues this project:** the environment that
scaffolded this repo had no PyPI/apt access, so it couldn't run the real
`specify` CLI. `.specify/` was vendored verbatim from
[github/spec-kit](https://github.com/github/spec-kit); the
`.claude/skills/*/SKILL.md` files were hand-reconstructed by reading the
CLI's own generation code and reimplementing it (verified: valid
frontmatter, correct argument-hints, correctly rewritten script paths) —
a faithful best effort, not a guaranteed byte-for-byte match to the
official output. If exact CLI parity ever matters, run this once on a
machine with real internet access (needs `uv`/`uvx`) to regenerate via
the official installer — it will not touch
`.specify/memory/constitution.md`:

```bash
bash scripts/bootstrap_speckit.sh
```

## Repo layout

```
payerguard/
├── MVP_CONTEXT.md          # read this first
├── docker-compose.yml       # backend + postgres (local dev); frontend service stubbed, commented out
├── .env.example
├── .specify/                 # speckit: constitution, templates, helper scripts (see below)
├── data/
│   ├── raw/                 # inpatient.csv lives here
│   ├── sampled/
│   ├── processed/
│   ├── baseline/
│   └── features/
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/                 # one module per feature (see MVP_CONTEXT.md Section 3)
├── ml/
│   ├── training/             # benchmark runner scripts
│   ├── notebooks/
│   └── artifacts/            # trained model files (gitignored)
├── frontend/                 # placeholder, deferred; will be its own container when built
├── infra/
│   ├── docker/
│   └── github-actions/       # CI/CD, deferred
├── docs/
│   ├── architecture.md
│   └── data_profiling_report.md
└── scripts/
```

## Local dev quickstart (once implementation begins)

```bash
cp .env.example .env      # fill in MISTRAL_API_KEY etc.
docker compose up --build
```

## Dataset

Single dataset: `data/raw/inpatient.csv` — CMS Medicare inpatient claims
(pipe-delimited, `sep="|"`). See `MVP_CONTEXT.md` Section 2 for the full,
real profile of this file.
