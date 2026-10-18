import React, { useState } from 'react';
import {
  FileText,
  Copy,
  Check,
  Download,
  AlertTriangle,
  ShieldAlert,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Scale,
  Clock,
  Layers,
} from 'lucide-react';
import { cn } from '../../lib/utils';

export interface DeepRiskReportPayload {
  code: string;
  snapshot_id?: number;
  holding_days: number;
  created_at: string;
  summary: string;
  cost_breakdown: {
    spread_cost_pct?: number | null;
    display_spread_cost?: string;
    daily_theta_decay?: number | null;
    display_daily_theta_decay?: string;
    flat_decay?: number | null;
    display_flat_decay?: string;
    effective_gearing?: number | null;
    display_effective_gearing?: string;
    holding_days?: number;
  };
  what_must_go_right: string[];
  key_risks: Array<{
    flag: string;
    description: string;
    severity?: string;
  }>;
  counterpoints: string[];
  data_limits: string[];
  disclaimer: string;
}

export interface DeepReportProps {
  code: string;
  holdingDays?: number;
  initialReport?: DeepRiskReportPayload | null;
  onGenerate?: (code: string, holdingDays: number) => Promise<DeepRiskReportPayload | null>;
  className?: string;
}

const PIPELINE_STEPS = [
  { id: 'collect', label: '1. Collect Market Data' },
  { id: 'draft', label: '2. Draft Quantitative Hurdle' },
  { id: 'review', label: '3. Adversarial Red-Team' },
  { id: 'assemble', label: '4. Grounded Assembly' },
];

export const DeepReport: React.FC<DeepReportProps> = ({
  code,
  holdingDays = 5,
  initialReport = null,
  onGenerate,
  className,
}) => {
  const [report, setReport] = useState<DeepRiskReportPayload | null>(initialReport);
  const [loading, setLoading] = useState<boolean>(false);
  const [currentStepIndex, setCurrentStepIndex] = useState<number>(0);
  const [copied, setCopied] = useState<boolean>(false);
  const [expanded, setExpanded] = useState<boolean>(true);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const formatReportAsPlainText = (rep: DeepRiskReportPayload): string => {
    return [
      `================================================================================`,
      `WARRANTS X-RAY DEEP RISK REPORT: ${rep.code}`,
      `Generated At: ${rep.created_at}`,
      `Holding Horizon: ${rep.holding_days} Days`,
      `================================================================================`,
      ``,
      `1. EXECUTIVE SUMMARY`,
      rep.summary,
      ``,
      `2. QUANTITATIVE COST BREAKDOWN`,
      `- Bid-Ask Spread Friction: ${rep.cost_breakdown.display_spread_cost || 'N/A'}`,
      `- Daily Theta Decay Drag : ${rep.cost_breakdown.display_daily_theta_decay || 'N/A'}`,
      `- Projected Total Decay  : ${rep.cost_breakdown.display_flat_decay || 'N/A'}`,
      `- Effective Gearing      : ${rep.cost_breakdown.display_effective_gearing || 'N/A'}`,
      ``,
      `3. WHAT MUST GO RIGHT`,
      ...rep.what_must_go_right.map((item, idx) => `  ${idx + 1}. ${item}`),
      ``,
      `4. KEY RISKS & WARNING FLAGS`,
      ...rep.key_risks.map((k) => `  * [${k.flag}] ${k.description}`),
      ``,
      `5. RED-TEAM ADVERSARIAL COUNTERPOINTS`,
      ...rep.counterpoints.map((c, idx) => `  ${idx + 1}. ${c}`),
      ``,
      `6. DATA LIMITS & MODEL BOUNDS`,
      ...rep.data_limits.map((l) => `  - ${l}`),
      ``,
      `================================================================================`,
      `REGULATORY DISCLAIMER`,
      rep.disclaimer || 'Educational only. Not investment advice or an endorsement.',
      `================================================================================`,
    ].join('\n');
  };

  const handleGenerate = async () => {
    setLoading(true);
    setErrorMsg(null);
    setCurrentStepIndex(0);

    try {
      // Step progress simulation
      const stepTimer1 = setTimeout(() => setCurrentStepIndex(1), 300);
      const stepTimer2 = setTimeout(() => setCurrentStepIndex(2), 600);
      const stepTimer3 = setTimeout(() => setCurrentStepIndex(3), 900);

      let fetchedReport: DeepRiskReportPayload | null = null;
      if (onGenerate) {
        fetchedReport = await onGenerate(code, holdingDays);
      } else {
        const resp = await fetch('/api/report', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ code, holding_days: holdingDays }),
        });
        if (!resp.ok) {
          const errData = await resp.json().catch(() => ({}));
          throw new Error(errData?.error?.message || `Failed to generate report (${resp.status})`);
        }
        const data = await resp.json();
        fetchedReport = data.report;
      }

      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      clearTimeout(stepTimer3);

      if (fetchedReport) {
        setReport(fetchedReport);
        setExpanded(true);
      }
    } catch (err: any) {
      setErrorMsg(err?.message || 'Error creating Deep Risk Report');
    } finally {
      setLoading(false);
    }
  };

  const handleCopy = async () => {
    if (!report) return;
    const text = formatReportAsPlainText(report);
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2500);
    } catch (e) {
      console.error('Failed to copy text', e);
    }
  };

  const handleExport = () => {
    if (!report) return;
    const text = formatReportAsPlainText(report);
    const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `warrant-${code.toLowerCase()}-deep-risk-report.txt`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div
      data-testid="deep-report-container"
      className={cn('rounded-xl border border-primary/20 bg-card p-4 shadow-sm space-y-4', className)}
    >
      {/* Top Header & Trigger Action */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center space-x-2">
          <div className="h-8 w-8 rounded-lg bg-primary/10 flex items-center justify-center text-primary">
            <FileText className="h-4 w-4" />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-foreground flex items-center gap-2">
              Deep Risk Report
              <span className="text-xs px-2 py-0.5 rounded-full bg-primary/10 text-primary font-mono font-medium">
                {code}
              </span>
            </h3>
            <p className="text-xs text-muted-foreground">
              4-stage sequential red-team stress test across a {holdingDays}-day horizon
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {!report && (
            <button
              data-testid="generate-deep-report-btn"
              onClick={handleGenerate}
              disabled={loading}
              className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-primary text-primary-foreground hover:bg-primary/90 transition disabled:opacity-50"
            >
              <RefreshCw className={cn('h-3.5 w-3.5', loading && 'animate-spin')} />
              <span>{loading ? 'Analyzing...' : 'Generate Deep Report'}</span>
            </button>
          )}

          {report && (
            <>
              <button
                data-testid="copy-report-btn"
                onClick={handleCopy}
                className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-md text-xs font-medium border border-border/80 bg-background hover:bg-accent text-foreground transition"
                title="Copy report text including regulatory disclaimer"
              >
                {copied ? <Check className="h-3.5 w-3.5 text-emerald-500" /> : <Copy className="h-3.5 w-3.5" />}
                <span>{copied ? 'Copied with Disclaimer' : 'Copy'}</span>
              </button>

              <button
                data-testid="export-report-btn"
                onClick={handleExport}
                className="inline-flex items-center space-x-1 px-2.5 py-1 rounded-md text-xs font-medium border border-border/80 bg-background hover:bg-accent text-foreground transition"
                title="Export as text file including regulatory disclaimer"
              >
                <Download className="h-3.5 w-3.5" />
                <span>Export (.txt)</span>
              </button>

              <button
                onClick={() => setExpanded(!expanded)}
                className="p-1 rounded-md hover:bg-accent text-muted-foreground transition"
                aria-label="Toggle report expand"
              >
                {expanded ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              </button>
            </>
          )}
        </div>
      </div>

      {/* Pipeline Step Progress Bar */}
      {loading && (
        <div data-testid="pipeline-progress-bar" className="space-y-2 py-2">
          <div className="grid grid-cols-4 gap-2">
            {PIPELINE_STEPS.map((step, idx) => (
              <div
                key={step.id}
                className={cn(
                  'text-[11px] p-2 rounded-lg border text-center transition-all',
                  idx <= currentStepIndex
                    ? 'border-primary/50 bg-primary/10 text-primary font-medium'
                    : 'border-border/40 bg-muted/40 text-muted-foreground'
                )}
              >
                {step.label}
              </div>
            ))}
          </div>
        </div>
      )}

      {errorMsg && (
        <div className="rounded-lg bg-destructive/10 border border-destructive/20 p-3 text-xs text-destructive flex items-center space-x-2">
          <AlertTriangle className="h-4 w-4 shrink-0" />
          <span>{errorMsg}</span>
        </div>
      )}

      {/* Expanded Deep Report Contents */}
      {report && expanded && (
        <div data-testid="deep-report-content" className="space-y-4 pt-2 border-t border-border/40 text-xs">
          {/* Section 1: Summary */}
          <div className="space-y-1">
            <h4 className="font-semibold text-foreground flex items-center space-x-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-primary" />
              <span>1. Executive Summary</span>
            </h4>
            <p className="text-muted-foreground leading-relaxed pl-3">{report.summary}</p>
          </div>

          {/* Section 2: Quantitative Cost Breakdown */}
          <div className="space-y-1.5">
            <h4 className="font-semibold text-foreground flex items-center space-x-1.5">
              <Scale className="h-3.5 w-3.5 text-primary" />
              <span>2. Quantitative Cost Breakdown ({report.holding_days} Days)</span>
            </h4>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pl-3">
              <div className="rounded-lg bg-muted/50 p-2 border border-border/50">
                <span className="text-[10px] text-muted-foreground block">Spread Friction</span>
                <span className="text-xs font-semibold text-foreground font-mono">
                  {report.cost_breakdown.display_spread_cost || 'N/A'}
                </span>
              </div>
              <div className="rounded-lg bg-muted/50 p-2 border border-border/50">
                <span className="text-[10px] text-muted-foreground block">Daily Theta Decay</span>
                <span className="text-xs font-semibold text-foreground font-mono">
                  {report.cost_breakdown.display_daily_theta_decay || 'N/A'}
                </span>
              </div>
              <div className="rounded-lg bg-muted/50 p-2 border border-border/50">
                <span className="text-[10px] text-muted-foreground block">Total Holding Drag</span>
                <span className="text-xs font-semibold text-foreground font-mono">
                  {report.cost_breakdown.display_flat_decay || 'N/A'}
                </span>
              </div>
              <div className="rounded-lg bg-muted/50 p-2 border border-border/50">
                <span className="text-[10px] text-muted-foreground block">Effective Gearing</span>
                <span className="text-xs font-semibold text-foreground font-mono">
                  {report.cost_breakdown.display_effective_gearing || 'N/A'}
                </span>
              </div>
            </div>
          </div>

          {/* Section 3: What Must Go Right */}
          <div className="space-y-1">
            <h4 className="font-semibold text-foreground flex items-center space-x-1.5">
              <Clock className="h-3.5 w-3.5 text-amber-500" />
              <span>3. What Must Go Right</span>
            </h4>
            <ul className="list-disc list-inside space-y-1 pl-3 text-muted-foreground">
              {report.what_must_go_right.map((item, idx) => (
                <li key={idx} className="leading-relaxed">
                  {item}
                </li>
              ))}
            </ul>
          </div>

          {/* Section 4: Key Risks & Flags */}
          <div className="space-y-1">
            <h4 className="font-semibold text-foreground flex items-center space-x-1.5">
              <AlertTriangle className="h-3.5 w-3.5 text-destructive" />
              <span>4. Triggered Risk Flags</span>
            </h4>
            <div className="space-y-1.5 pl-3">
              {report.key_risks.map((k, idx) => (
                <div key={idx} className="flex items-start space-x-2 rounded-md bg-destructive/5 p-1.5 border border-destructive/10">
                  <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-medium bg-destructive/10 text-destructive shrink-0">
                    {k.flag}
                  </span>
                  <span className="text-[11px] text-foreground/90">{k.description}</span>
                </div>
              ))}
            </div>
          </div>

          {/* Section 5: Red-Team Adversarial Counterpoints */}
          <div className="space-y-1">
            <h4 className="font-semibold text-foreground flex items-center space-x-1.5">
              <ShieldAlert className="h-3.5 w-3.5 text-rose-500" />
              <span>5. Red-Team Counterpoints (Adversarial Stress Test)</span>
            </h4>
            <div className="space-y-1.5 pl-3">
              {report.counterpoints.map((c, idx) => (
                <div key={idx} className="rounded-lg bg-accent/30 p-2 border border-border/40 text-[11px] text-foreground/90 leading-relaxed">
                  {c}
                </div>
              ))}
            </div>
          </div>

          {/* Section 6: Data Limits */}
          <div className="space-y-1">
            <h4 className="font-semibold text-muted-foreground flex items-center space-x-1.5">
              <Layers className="h-3.5 w-3.5 text-muted-foreground" />
              <span>6. Data Limits & Assumptions</span>
            </h4>
            <ul className="list-disc list-inside space-y-0.5 pl-3 text-[11px] text-muted-foreground">
              {report.data_limits.map((l, idx) => (
                <li key={idx}>{l}</li>
              ))}
            </ul>
          </div>

          {/* Mandatory Regulatory Disclaimer */}
          <div
            data-testid="deep-report-disclaimer"
            className="rounded-lg bg-amber-500/10 border border-amber-500/20 p-2.5 text-[11px] text-amber-700 dark:text-amber-400 font-medium"
          >
            {report.disclaimer || 'Educational only. Not investment advice or an endorsement.'}
          </div>
        </div>
      )}
    </div>
  );
};
