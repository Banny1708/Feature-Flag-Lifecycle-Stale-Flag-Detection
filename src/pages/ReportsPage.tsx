import React, { useState } from 'react';
import { PageHeader } from '@/layouts/PageHeader';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { Badge } from '@/components/common/Badge';
import { Tabs } from '@/components/common/Tabs';
import { mockReports } from '@/data/mockReports';
import { mockEvidenceRecords } from '@/data/mockEvidence';
import { FileText, Download } from 'lucide-react';
import { formatDate } from '@/utils/formatters';

export const ReportsPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState('reports');

  const tabs = [
    { id: 'reports', label: 'Generated Reports', count: mockReports.length },
    { id: 'evidence', label: 'Staleness Evidence Vault', count: mockEvidenceRecords.length },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Evidence Records & Governance Reports"
        description="Audit logs, telemetry proof records, and executive reports documenting feature flag debt elimination and SOC2/compliance conformance."
        actions={
          <Button
            variant="primary"
            size="sm"
            onClick={() => alert('New executive compliance report generation started.')}
            icon={<FileText className="w-3.5 h-3.5" />}
          >
            Generate New Report
          </Button>
        }
      />

      {/* Tabs */}
      <Tabs tabs={tabs} activeTab={activeTab} onChange={setActiveTab} />

      {activeTab === 'reports' ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          {mockReports.map((report) => (
            <Card key={report.id} className="p-5 flex flex-col justify-between">
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <Badge variant="violet" size="sm" className="uppercase font-mono text-[10px] mb-1.5">
                      {report.type}
                    </Badge>
                    <h3 className="text-sm font-semibold text-zinc-100">{report.title}</h3>
                    <div className="text-[11px] text-zinc-400 mt-0.5">
                      Generated on {formatDate(report.generatedAt)}
                    </div>
                  </div>
                  <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded bg-surface-100 border border-border text-zinc-400">
                    {report.downloadFormat}
                  </span>
                </div>

                <div className="grid grid-cols-2 gap-2 p-3 rounded bg-surface-100/70 border border-border/60 text-xs">
                  <div>
                    <span className="text-zinc-400 text-[11px]">Flags Scanned:</span>
                    <div className="font-mono font-semibold text-zinc-200">
                      {report.summary.totalScannedFlags} flags
                    </div>
                  </div>
                  <div>
                    <span className="text-zinc-400 text-[11px]">Stale Flags:</span>
                    <div className="font-mono font-semibold text-rose-400">
                      {report.summary.staleFlagsIdentified} flags
                    </div>
                  </div>
                  <div>
                    <span className="text-zinc-400 text-[11px]">Lines Removed:</span>
                    <div className="font-mono font-semibold text-emerald-400">
                      -{report.summary.codeLinesEliminated} lines
                    </div>
                  </div>
                  <div>
                    <span className="text-zinc-400 text-[11px]">Debt Reclaimed:</span>
                    <div className="font-mono font-semibold text-indigo-300">
                      {report.summary.techDebtReductionHours} hrs
                    </div>
                  </div>
                </div>
              </div>

              <div className="pt-4 mt-3 border-t border-border flex items-center justify-between">
                <span className="text-[11px] text-zinc-400 font-mono">Status: Ready</span>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => alert(`Downloading ${report.title}.${report.downloadFormat}`)}
                  icon={<Download className="w-3.5 h-3.5" />}
                >
                  Download {report.downloadFormat.toUpperCase()}
                </Button>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <div className="space-y-4">
          {mockEvidenceRecords.map((item) => (
            <Card key={item.id} className="p-5">
              <div className="space-y-3">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-border/60 pb-3">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-zinc-100 font-bold text-sm">{item.flagName}</span>
                    <Badge variant="amber" size="sm" className="font-mono uppercase text-[10px]">
                      {item.evidenceType}
                    </Badge>
                  </div>
                  <div className="text-xs text-zinc-400 font-mono">
                    Confidence: <strong className="text-emerald-400">{(item.confidenceScore * 100).toFixed(0)}%</strong> • {item.source}
                  </div>
                </div>

                <p className="text-xs text-zinc-300">{item.summary}</p>

                <div className="p-3 rounded bg-[#0b0f19] border border-border text-xs font-mono text-zinc-400">
                  <div className="text-zinc-500 text-[11px] mb-1">Telemetry Proof Payload:</div>
                  <pre className="text-indigo-300 whitespace-pre-wrap">{JSON.stringify(item.payload, null, 2)}</pre>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};
