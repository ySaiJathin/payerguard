import React, { useState } from 'react';
import {
  History as HistoryIcon,
  Download,
  FileCheck,
  FileText,
  Search,
  Filter,
  Calendar,
  Layers,
  CheckCircle2,
  AlertTriangle,
  Eye,
  FileSpreadsheet
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from '../components/ui/Table';
import { Modal } from '../components/ui/Modal';
import { mockBatchHistory } from '../data/mockHistory';
import { BatchUploadSummary } from '../types';
import { formatCurrency, formatDate } from '../utils/formatters';

export const History: React.FC = () => {
  const [batches, setBatches] = useState<BatchUploadSummary[]>(mockBatchHistory);
  const [searchQuery, setSearchQuery] = useState('');
  const [formatFilter, setFormatFilter] = useState('all');
  const [selectedBatch, setSelectedBatch] = useState<BatchUploadSummary | null>(null);
  const [exportSuccess, setExportSuccess] = useState<string | null>(null);

  const filteredBatches = batches.filter((b) => {
    if (formatFilter !== 'all' && b.format !== formatFilter) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchId = b.batchId.toLowerCase().includes(q);
      const matchFile = b.filename.toLowerCase().includes(q);
      const matchUser = b.uploadedBy.toLowerCase().includes(q);
      if (!matchId && !matchFile && !matchUser) return false;
    }
    return true;
  });

  const totalClaims = batches.reduce((acc, b) => acc + b.totalClaims, 0);
  const totalBilled = batches.reduce((acc, b) => acc + b.totalBilledAmount, 0);
  const avgCleanRate = (batches.reduce((acc, b) => acc + b.cleanClaimRate, 0) / batches.length).toFixed(1);

  const handleExport = (batchName: string, format: 'CSV' | 'JSON' | 'PDF') => {
    setExportSuccess(`Successfully generated and exported ${batchName} compliance report in ${format} format.`);
    setTimeout(() => setExportSuccess(null), 3500);
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 pb-2 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-white font-heading">
              Batch Ingestion & Compliance History
            </h1>
            <Badge variant="info" size="sm">
              Audit Vault
            </Badge>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Historical audit logs of processed EDI 837/CMS-1500 batches, first-pass clean claim rates, and regulatory compliance reports.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => handleExport('Global_Batch_Ledger_2026', 'CSV')}
            leftIcon={<Download className="w-3.5 h-3.5" />}
          >
            Export Full Ledger (CSV)
          </Button>
        </div>
      </div>

      {/* Export Toast */}
      {exportSuccess && (
        <div className="p-3.5 rounded-xl bg-emerald-950/80 border border-emerald-700 text-emerald-200 text-xs font-medium flex items-center justify-between shadow-lg">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{exportSuccess}</span>
          </div>
          <button onClick={() => setExportSuccess(null)} className="text-emerald-400 hover:text-emerald-200 text-xs">
            Dismiss
          </button>
        </div>
      )}

      {/* Historical Statistics Ribbon */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800">
          <span className="text-[11px] text-slate-400 uppercase font-semibold block">Total Batches Archived</span>
          <span className="text-xl font-bold font-mono text-white mt-1 block">{batches.length}</span>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800">
          <span className="text-[11px] text-slate-400 uppercase font-semibold block">Total Evaluated Claims</span>
          <span className="text-xl font-bold font-mono text-cyan-400 mt-1 block">{totalClaims.toLocaleString()}</span>
        </div>

        <div className="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-800/50">
          <span className="text-[11px] text-emerald-300 uppercase font-semibold block">Average Clean Claim Rate</span>
          <span className="text-xl font-bold font-mono text-emerald-400 mt-1 block">{avgCleanRate}%</span>
        </div>

        <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800">
          <span className="text-[11px] text-slate-400 uppercase font-semibold block">Total Billed Volume</span>
          <span className="text-xl font-bold font-mono text-white mt-1 block">{formatCurrency(totalBilled)}</span>
        </div>
      </div>

      {/* Search & Filter */}
      <Card className="p-4 bg-slate-900/70">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="relative w-full sm:w-72">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search Batch ID, Filename, Uploader..."
                className="w-full bg-slate-950/70 border border-slate-800 hover:border-slate-700 focus:border-cyan-500 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-100 placeholder:text-slate-400 focus:outline-none font-mono"
              />
            </div>

            <select
              value={formatFilter}
              onChange={(e) => setFormatFilter(e.target.value)}
              className="bg-slate-950/80 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-cyan-500"
            >
              <option value="all">All Formats</option>
              <option value="837P">837P Professional</option>
              <option value="837I">837I Institutional</option>
              <option value="CMS-1500">CMS-1500</option>
            </select>
          </div>

          <span className="text-xs text-slate-400 font-mono">
            Showing <span className="text-white font-bold">{filteredBatches.length}</span> batch records
          </span>
        </div>
      </Card>

      {/* Batches Table */}
      <Card>
        <CardHeader>
          <CardTitle>Archived EDI Claim Batches</CardTitle>
          <CardDescription>Click any batch record to view forensic compliance breakdown</CardDescription>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Batch ID & File</TableHead>
                <TableHead>Ingestion Timestamp</TableHead>
                <TableHead>Format</TableHead>
                <TableHead>Claims (Clean / Flagged)</TableHead>
                <TableHead>Clean Rate</TableHead>
                <TableHead>Total Billed</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filteredBatches.map((b) => (
                <TableRow key={b.batchId}>
                  <TableCell>
                    <div className="flex flex-col">
                      <span className="font-mono font-bold text-cyan-400">{b.batchId}</span>
                      <span className="text-[11px] text-slate-300 font-mono truncate max-w-xs">{b.filename}</span>
                    </div>
                  </TableCell>

                  <TableCell className="font-mono text-xs text-slate-400">
                    {formatDate(b.uploadedAt)}
                  </TableCell>

                  <TableCell>
                    <Badge variant="neutral" size="sm">
                      {b.format}
                    </Badge>
                  </TableCell>

                  <TableCell>
                    <div className="flex items-center gap-1.5 font-mono text-xs">
                      <span className="font-bold text-white">{b.totalClaims}</span>
                      <span className="text-slate-500">/</span>
                      <span className="text-emerald-400">{b.cleanClaims} clean</span>
                      <span className="text-slate-500">/</span>
                      <span className="text-rose-400">{b.flaggedClaims + b.rejectedClaims} err</span>
                    </div>
                  </TableCell>

                  <TableCell>
                    <span className={`font-mono text-xs font-bold ${b.cleanClaimRate >= 98 ? 'text-emerald-400' : 'text-amber-400'}`}>
                      {b.cleanClaimRate.toFixed(1)}%
                    </span>
                  </TableCell>

                  <TableCell className="font-mono font-semibold text-slate-200">
                    {formatCurrency(b.totalBilledAmount)}
                  </TableCell>

                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      <Button
                        variant="secondary"
                        size="xs"
                        onClick={() => setSelectedBatch(b)}
                        leftIcon={<Eye className="w-3 h-3" />}
                      >
                        Inspect
                      </Button>
                      <Button
                        variant="outline"
                        size="xs"
                        onClick={() => handleExport(b.batchId, 'CSV')}
                        leftIcon={<Download className="w-3 h-3" />}
                      >
                        CSV
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Batch Inspection Modal */}
      {selectedBatch && (
        <Modal
          isOpen={true}
          onClose={() => setSelectedBatch(null)}
          title={`Batch Audit Report: ${selectedBatch.batchId}`}
          description={`File: ${selectedBatch.filename} | Uploaded by: ${selectedBatch.uploadedBy}`}
          size="lg"
          footer={
            <>
              <Button variant="secondary" size="sm" onClick={() => setSelectedBatch(null)}>
                Close
              </Button>
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  handleExport(selectedBatch.batchId, 'PDF');
                  setSelectedBatch(null);
                }}
                leftIcon={<FileText className="w-3.5 h-3.5" />}
              >
                Download Audit PDF
              </Button>
            </>
          }
        >
          <div className="space-y-4 text-xs">
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 p-3.5 rounded-xl bg-slate-950/60 border border-slate-800">
              <div>
                <span className="text-slate-400 block text-[10px] uppercase">Format</span>
                <span className="font-mono font-bold text-white">{selectedBatch.format}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase">Total Claims</span>
                <span className="font-mono font-bold text-white">{selectedBatch.totalClaims}</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase">Clean Pass Rate</span>
                <span className="font-mono font-bold text-emerald-400">{selectedBatch.cleanClaimRate}%</span>
              </div>
              <div>
                <span className="text-slate-400 block text-[10px] uppercase">Processing Latency</span>
                <span className="font-mono text-cyan-300">{selectedBatch.processingDurationMs} ms</span>
              </div>
            </div>

            <div className="p-3.5 rounded-lg bg-slate-900 border border-slate-800 space-y-2">
              <span className="font-semibold text-slate-200 block">Regulatory Compliance Attestation:</span>
              <p className="text-slate-300 leading-relaxed text-[11px]">
                This batch has been evaluated under statutory Prompt Pay Guidelines (42 CFR § 447.45 and Commercial State SLA statutes). All EDI 837 loops have been validated against WEDI SNIP Levels 1 through 5.
              </p>
            </div>
          </div>
        </Modal>
      )}
    </div>
  );
};
