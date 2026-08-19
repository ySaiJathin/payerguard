import React from 'react';
import { History as HistoryIcon, GitBranch, Search } from 'lucide-react';
import { Card, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';

/**
 * Deliberately a shell, pending a product decision.
 *
 * This page carries a genuine naming collision that should not be resolved by
 * guessing:
 *
 *  - As coded, "History" meant **batch upload history** — a list of past file
 *    uploads with per-batch counts. That depends on batch ingestion, which has
 *    no backend yet (see the Upload page).
 *  - The backend's real history module is something different: a **per-entity
 *    audit trail** at `GET /history/{entity_type}/{entity_id}`, listing every
 *    pipeline stage that touched one claim or incident. It is already wired
 *    into this UI — on the Investigation page's Audit Trail tab, where it
 *    answers a question a user actually asks.
 *
 * Repurposing this page around the audit endpoint would need an entity to
 * scope to, and a top-level "all audit entries" view does not exist in the API
 * (the endpoint requires an entity type and id). Building either interpretation
 * now would be a guess, so the page states the choice instead of making it.
 */
export const History: React.FC = () => (
  <div className="space-y-6 animate-in fade-in duration-200">
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-800/80">
      <div>
        <div className="flex items-center gap-2.5">
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white font-heading">
            History
          </h1>
          <Badge variant="warning" size="sm">
            Needs a decision
          </Badge>
        </div>
        <p className="text-xs text-slate-400 mt-1">
          Two different things share this name. Which one this page should be is unresolved.
        </p>
      </div>
    </div>

    <Card>
      <CardContent className="py-12 flex flex-col items-center text-center gap-4">
        <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800">
          <HistoryIcon className="w-8 h-8 text-slate-500" />
        </div>

        <div className="max-w-xl space-y-2">
          <h2 className="text-sm font-semibold text-slate-100">
            Not built, because the requirement is ambiguous
          </h2>
          <p className="text-xs text-slate-400 leading-relaxed">
            This page was originally coded as a batch-upload history view. The backend module that
            shares its name is a per-entity audit trail. These are different features, and picking
            one silently would bake in a guess.
          </p>
        </div>

        <div className="w-full max-w-2xl grid grid-cols-1 md:grid-cols-2 gap-3 mt-2 text-left">
          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-200">
              <GitBranch className="w-3.5 h-3.5 text-amber-400" />
              Option A — Batch upload history
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              A list of past file uploads with row counts and validation status. Blocked: batch
              ingestion has no backend, so there are no batches to list.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/60 border border-slate-800 space-y-2">
            <div className="flex items-center gap-2 text-xs font-semibold text-slate-200">
              <Search className="w-3.5 h-3.5 text-cyan-400" />
              Option B — Entity audit lookup
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              A search box to pull the audit trail for a given claim or incident id. The endpoint
              exists and is already used on the Investigation page's Audit Trail tab, so this page
              would mostly duplicate it.
            </p>
          </div>
        </div>

        <p className="text-[11px] text-slate-500 max-w-xl mt-1 leading-relaxed">
          The real audit trail is live today — open any incident and select the Audit Trail tab.
        </p>
      </CardContent>
    </Card>
  </div>
);

export default History;
