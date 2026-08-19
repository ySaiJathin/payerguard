import React from 'react';
import { UploadCloud, Hourglass, FileText } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Badge } from '../components/ui/Badge';

/**
 * Deliberately a shell.
 *
 * Batch ingestion has no backend. `backend/app/ingestion/router.py` is still
 * the Phase-0 placeholder -- there is no `POST /claims/upload` endpoint to
 * call. The previous version of this page had a full drag-and-drop uploader
 * with progress bars and per-batch statistics, all of it driven by in-memory
 * mock state; it would have accepted a file, appeared to succeed, and sent
 * nothing anywhere.
 *
 * Rather than keep a convincing-looking uploader wired to nothing, this page
 * states what is missing and what would have to exist first.
 */
export const Upload: React.FC = () => (
  <div className="space-y-6 animate-in fade-in duration-200">
    <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-800/80">
      <div>
        <div className="flex items-center gap-2.5">
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white font-heading">
            Upload Claims
          </h1>
          <Badge variant="warning" size="sm">
            Not implemented
          </Badge>
        </div>
        <p className="text-xs text-slate-400 mt-1">
          Manual and repeated batch ingestion of the CMS inpatient extract.
        </p>
      </div>
    </div>

    <Card>
      <CardContent className="py-12 flex flex-col items-center text-center gap-4">
        <div className="p-4 rounded-2xl bg-slate-900 border border-slate-800">
          <UploadCloud className="w-8 h-8 text-slate-500" />
        </div>

        <div className="max-w-xl space-y-2">
          <h2 className="text-sm font-semibold text-slate-100">
            There is no upload endpoint to call yet
          </h2>
          <p className="text-xs text-slate-400 leading-relaxed">
            The ingestion module in the backend is still a placeholder — no{' '}
            <span className="font-mono text-slate-300">POST /claims/upload</span> route exists, and
            no batch record type is persisted. A file picker here could not do anything real, so
            none is shown.
          </p>
        </div>

        <div className="w-full max-w-xl mt-2 p-4 rounded-xl bg-slate-950/60 border border-slate-800 text-left space-y-3">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-200">
            <Hourglass className="w-3.5 h-3.5 text-amber-400" />
            What has to exist first
          </div>
          <ul className="text-xs text-slate-400 space-y-1.5 list-disc list-inside leading-relaxed">
            <li>
              A batch-ingestion spec and implementation (manual upload plus repeated batch upload of
              the same file shape — not live streaming).
            </li>
            <li>
              A persisted batch record carrying at least a batch id, upload timestamp, measured row
              count, and validation status.
            </li>
            <li>
              Hand-off into the existing profiling → cleaning → quality-validation pipeline, rather
              than a second copy of that logic.
            </li>
          </ul>
        </div>

        <div className="w-full max-w-xl p-4 rounded-xl bg-slate-950/60 border border-slate-800 text-left">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-200 mb-2">
            <FileText className="w-3.5 h-3.5 text-cyan-400" />
            Expected file shape, when it lands
          </div>
          <p className="text-xs text-slate-400 leading-relaxed">
            Pipe-delimited (<span className="font-mono text-slate-300">sep="|"</span>) despite the{' '}
            <span className="font-mono text-slate-300">.csv</span> extension, 197 columns, at
            claim-line grain. The backend currently reads this file from disk at{' '}
            <span className="font-mono text-slate-300">data/raw/inpatient.csv</span>.
          </p>
        </div>
      </CardContent>
    </Card>
  </div>
);

export default Upload;
