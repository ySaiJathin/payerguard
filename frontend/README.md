# Frontend (deferred)

Not started. Per MVP_CONTEXT.md Section 4, frontend implementation is on
hold until the backend pipeline is built and the user specifies pages/UX.

When implementation starts, this folder gets its own `Dockerfile` and is
wired up as a `frontend` service in the root `docker-compose.yml` (already
present there, commented out) — the frontend is deployed as a container,
same pattern as the backend, not as a separately-hosted static bundle.
