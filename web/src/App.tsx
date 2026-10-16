import React from 'react';

export default function App(): React.JSX.Element {
  return (
    <div className="flex min-h-screen flex-col bg-background text-foreground">
      <header className="border-b border-border px-6 py-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="h-8 w-8 rounded-lg bg-primary/20 flex items-center justify-center font-bold text-primary">
            WX
          </div>
          <div>
            <h1 className="text-lg font-semibold tracking-tight">Warrant X-Ray</h1>
            <p className="text-xs text-muted-foreground">Bursa Malaysia Structured Warrants Risk Copilot</p>
          </div>
        </div>
        <div className="flex items-center space-x-2 text-xs">
          <span className="inline-flex items-center rounded-full bg-emerald-500/10 px-2.5 py-0.5 text-emerald-500 font-medium border border-emerald-500/20">
            Replay Mode
          </span>
        </div>
      </header>

      <main className="flex-1 p-6 max-w-7xl mx-auto w-full grid grid-cols-1 md:grid-cols-12 gap-6">
        <section className="md:col-span-5 border border-border rounded-xl p-4 bg-card shadow-sm flex flex-col justify-between">
          <div>
            <h2 className="text-sm font-semibold mb-2">Risk Copilot Chat</h2>
            <p className="text-xs text-muted-foreground mb-4">
              Ask about holding costs, break-evens, or volatility shifts. Answers stream with verified numbers and citations.
            </p>
          </div>
          <div className="border-t border-border pt-3">
            <div className="text-[11px] text-muted-foreground italic">
              Describe, never advise. All figures computed deterministically.
            </div>
          </div>
        </section>

        <section className="md:col-span-7 border border-border rounded-xl p-4 bg-card shadow-sm">
          <h2 className="text-sm font-semibold mb-2">Evidence & Quant Panels</h2>
          <p className="text-xs text-muted-foreground">
            Warrant Card, Scenario Simulation, Comparison, and Data Provenance.
          </p>
        </section>
      </main>

      <footer className="border-t border-border px-6 py-3 text-center text-xs text-muted-foreground">
        Regulatory Disclaimer: Warrant X-Ray is an informational analytics tool and does not provide financial, investment, or trading advice.
      </footer>
    </div>
  );
}
