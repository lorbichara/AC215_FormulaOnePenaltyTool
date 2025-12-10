'use client';

import { ShieldAlert, FileText, Gauge, History } from 'lucide-react';

const severityStyles = {
    'Disqualification': { bg: 'bg-black text-white border border-primary', accent: 'text-primary' },
    'Grid Drop': { bg: 'bg-orange-500 text-black', accent: 'text-black' },
    'Time Penalty': { bg: 'bg-amber-400 text-black', accent: 'text-black' },
    'Warning': { bg: 'bg-slate-700 text-white', accent: 'text-white' },
    'No Action': { bg: 'bg-emerald-500 text-white', accent: 'text-white' },
};

const StatBadge = ({ label, value }) => (
    <div className="px-3 py-2 rounded-md bg-white/5 border border-white/10 text-xs uppercase tracking-[0.2em] text-muted-foreground font-heading">
        {label}: <span className="text-foreground ml-1">{value}</span>
    </div>
);

const RegulationCard = ({ reg }) => (
    <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4 shadow">
        <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">Article {reg.article}</span>
        </div>
        <p className="text-sm text-foreground mb-2">{reg.description}</p>
        <p className="text-xs text-muted-foreground">{reg.relevance}</p>
    </div>
);

const PrecedentCard = ({ item }) => (
    <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4 shadow hover:border-primary transition-colors">
        <div className="flex items-center justify-between mb-2">
            <h4 className="font-heading font-semibold text-foreground">{item.driver}</h4>
            <span className="text-xs text-muted-foreground">{item.year} {item.race}</span>
        </div>
        <p className="text-sm text-foreground mb-3">{item.incident}</p>
        <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>{item.penalty}</span>
            <span className="text-primary font-semibold">Match {item.similarity_score}%</span>
        </div>
    </div>
);

export default function AnalysisDashboard({ result }) {
    const severityStyle = severityStyles[result.penalty_severity] || severityStyles['No Action'];

    return (
        <div className="space-y-8">
            <div className="rounded-2xl border border-border bg-card dark:bg-[#0b1021] p-6 md:p-8 shadow-2xl relative overflow-hidden">
                <div className="absolute inset-0 pointer-events-none opacity-10 [--check:rgba(15,23,42,0.14)] dark:[--check:rgba(255,255,255,0.14)] [background-image:linear-gradient(45deg,var(--check)_25%,transparent_25%),linear-gradient(-45deg,var(--check)_25%,transparent_25%),linear-gradient(45deg,transparent_75%,var(--check)_75%),linear-gradient(-45deg,transparent_75%,var(--check)_75%)] [background-size:18px_18px] [background-position:0_0,0_9px,9px_-9px,-9px_0]" />
                <div className="relative z-10 flex flex-col gap-4">
                    <div className="flex flex-wrap items-center gap-3">
                        <div className={`px-4 py-2 rounded-md font-heading font-semibold uppercase tracking-[0.25em] shadow ${severityStyle.bg}`}>
                            {result.penalty_severity}
                        </div>
                        <StatBadge label="Fairness" value={`${result.fairness_rating}%`} />
                        <StatBadge label="Factors" value={result.key_factors.length} />
                    </div>
                    <h2 className="text-3xl md:text-4xl font-heading font-bold text-foreground">
                        {result.title || 'Penalty Analysis'}
                    </h2>
                    <p className="text-muted-foreground leading-relaxed">
                        {result.fan_summary}
                    </p>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-2">
                        <div className="rounded-xl bg-black/30 border border-slate-800 p-4">
                            <div className="flex items-center gap-2 text-muted-foreground uppercase tracking-[0.2em] text-xs mb-2">
                                <ShieldAlert className="h-4 w-4 text-primary" /> Verdict
                            </div>
                            <p className="text-sm text-foreground leading-relaxed">{result.technical_verdict}</p>
                        </div>
                        <div className="rounded-xl bg-black/30 border border-slate-800 p-4">
                            <div className="flex items-center gap-2 text-muted-foreground uppercase tracking-[0.2em] text-xs mb-2">
                                <Gauge className="h-4 w-4 text-primary" /> Consistency
                            </div>
                            <div className="h-2 w-full rounded-full bg-slate-800 overflow-hidden">
                                <div
                                    className="h-full bg-gradient-to-r from-emerald-400 via-amber-300 to-primary transition-all"
                                    style={{ width: `${result.fairness_rating}%` }}
                                />
                            </div>
                            <p className="text-xs text-muted-foreground mt-2">Higher values lean stricter; lower values lean lenient.</p>
                        </div>
                        <div className="rounded-xl bg-black/30 border border-slate-800 p-4">
                            <div className="flex items-center gap-2 text-muted-foreground uppercase tracking-[0.2em] text-xs mb-2">
                                <FileText className="h-4 w-4 text-primary" /> Key Factors
                            </div>
                            <ul className="text-sm text-foreground space-y-1">
                                {result.key_factors.map((factor, idx) => (
                                    <li key={idx} className="flex items-center gap-2">
                                        <span className="h-1.5 w-1.5 rounded-full bg-primary" />
                                        {factor}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <div className="lg:col-span-2 space-y-4">
                    <div className="flex items-center gap-2 text-muted-foreground uppercase tracking-[0.25em] text-xs">
                        <History className="h-4 w-4 text-primary" /> Historical precedents
                    </div>
                    <div className="grid md:grid-cols-2 gap-4">
                        {result.historical_precedents.length ? (
                            result.historical_precedents.map((item) => (
                                <PrecedentCard key={item.id || `${item.driver}-${item.race}`} item={item} />
                            ))
                        ) : (
                            <p className="text-sm text-muted-foreground">No precedents returned for this query.</p>
                        )}
                    </div>
                </div>
                <div className="space-y-4">
                    <div className="flex items-center gap-2 text-muted-foreground uppercase tracking-[0.25em] text-xs">
                        <FileText className="h-4 w-4 text-primary" /> Regulations cited
                    </div>
                    <div className="space-y-3">
                        {result.regulations_breached.map((reg) => (
                            <RegulationCard key={reg.id || reg.article} reg={reg} />
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}
