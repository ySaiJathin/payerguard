#!/usr/bin/env bash
# Completes the spec-kit installation started in this repo.
#
# WHY THIS SCRIPT EXISTS
# -----------------------
# The repo-scaffolding session that set up PayerGuard runs in a sandboxed
# cloud container without PyPI/apt access, so it could not run the real
# `specify` CLI (its deps -- typer, rich, readchar, json5 -- aren't
# installable there). Instead it vendored spec-kit's agent-agnostic core
# directly from https://github.com/github/spec-kit into .specify/:
#   .specify/memory/constitution.md   -- PayerGuard-specific, already filled in
#   .specify/templates/               -- spec/plan/tasks/checklist templates + raw command templates
#   .specify/scripts/bash/            -- the shell helpers those commands call
#
# That's everything needed to work by hand from the templates. What's
# missing is the AI-agent-specific layer the real CLI generates: Claude
# Code skills under .claude/skills/speckit-*/SKILL.md (the /speckit.specify,
# /speckit.plan, /speckit.tasks, /speckit.implement, etc. slash commands).
# Run this script once, on a machine with normal internet access, to
# generate that layer for real via the official CLI.
#
# Usage:
#   bash scripts/bootstrap_speckit.sh
#
# Requires: uv (https://docs.astral.sh/uv/) or pipx. Installs nothing
# permanently beyond what uvx caches for itself.

set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v uvx >/dev/null 2>&1; then
  echo "uvx not found. Install uv first: https://docs.astral.sh/uv/getting-started/installation/" >&2
  exit 1
fi

echo "Running: specify init --here --ai claude"
echo "(this will detect the existing .specify/ directory and fill in the .claude/ skills layer)"
uvx --from git+https://github.com/github/spec-kit.git specify init --here --ai claude

echo
echo "Done. Verify with: ls .claude/skills"
echo "The PayerGuard-specific constitution at .specify/memory/constitution.md was NOT touched by this script -- it is not part of what init writes."
