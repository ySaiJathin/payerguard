"""Constrained, deterministic remediation engine (Phase 13).

Three fixed handlers -- duplicate flagging, approved imputation, approved
status mapping -- each driven by a versioned YAML rule table under
`config/`, never an inline magic value. Remediation only executes against
an incident whose status is already "accepted" (Phase 12's HITL gate),
scoped strictly to the affected claims the caller supplies in the run
request. Any affected-claim condition matching no approved handler, or
whose precondition no longer holds at execution time, is recorded as
"Manual Action Required" instead of guessed at. No file in this module
imports Phase 11's LLM client -- handler selection is a pure function of
the rule tables, never a model call.
"""
