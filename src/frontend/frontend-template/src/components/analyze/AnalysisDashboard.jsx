'use client';

import { ShieldAlert, FileText, Gauge, History, Flag } from 'lucide-react';

const severityStyles = {
    'Disqualification': { bg: 'bg-black text-white border border-primary', accent: 'text-primary' },
    'Grid Drop': { bg: 'bg-orange-500 text-black', accent: 'text-black' },
    'Time Penalty': { bg: 'bg-amber-400 text-black', accent: 'text-black' },
    'Warning': { bg: 'bg-slate-700 text-white', accent: 'text-white' },
    'No Action': { bg: 'bg-emerald-500 text-white', accent: 'text-white' },
};

const StatBadge = ({ label, value }) => (
    <div className="flex items-center gap-2 px-3 py-2 rounded-md bg-muted border border-border text-[11px] uppercase tracking-[0.18em] text-muted-foreground font-heading">
        <span className="h-4 w-1.5 rounded-sm bg-primary" />
        <span className="text-muted-foreground">{label}</span>
        <span className="text-foreground font-semibold ml-auto tracking-normal">{value}</span>
    </div>
);

const ConsistencyGauge = ({ score }) => {
    const clamped = Math.max(0, Math.min(100, Math.round(score ?? 0)));
    const numSegments = 24;
    const minAngle = -100;
    const maxAngle = 100;
    const angleStep = (maxAngle - minAngle) / (numSegments - 1);
    const activeIndex = Math.round((clamped / 100) * (numSegments - 1));
    const band =
        clamped <= 33 ? { label: 'Lenient', color: 'bg-emerald-500 text-emerald-900 dark:text-emerald-100', border: 'border-emerald-300 dark:border-emerald-500' } :
            clamped <= 66 ? { label: 'Standard', color: 'bg-amber-400 text-amber-900 dark:text-amber-950', border: 'border-amber-300 dark:border-amber-500' } :
                { label: 'Strict', color: 'bg-orange-500 text-orange-950 dark:text-orange-50', border: 'border-orange-300 dark:border-orange-500' };

    return (
        <div className="relative mt-2 flex flex-col items-center select-none">
            <div className="relative w-full max-w-[340px] h-52 flex justify-center items-end pb-6 overflow-hidden">
                {Array.from({ length: numSegments }).map((_, i) => {
                    const angle = minAngle + i * angleStep;
                    const pct = i / (numSegments - 1);
                    let color = '#22c55e';
                    if (pct > 0.66) color = '#ef4444';
                    else if (pct > 0.33) color = '#eab308';
                    const isActive = i <= activeIndex;
                    return (
                        <div
                            key={i}
                            className="absolute bottom-0 left-1/2 origin-bottom w-[5px] h-[150px] -ml-[2.5px]"
                            style={{ transform: `rotate(${angle}deg)` }}
                        >
                            <div
                                className={`w-full h-[18px] rounded-sm transition-all duration-200 ${isActive ? 'opacity-100' : 'opacity-25 bg-slate-500/60'}`}
                                style={{
                                    backgroundColor: isActive ? color : undefined,
                                    boxShadow: isActive ? `0 0 8px ${color}` : 'none'
                                }}
                            />
                        </div>
                    );
                })}
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none translate-y-12 z-10">
                    <div className="flex items-baseline gap-1 drop-shadow-[0_6px_14px_rgba(0,0,0,0.35)]">
                        <span className="text-6xl font-heading font-bold text-foreground">{clamped}</span>
                        <span className="text-lg text-muted-foreground">%</span>
                    </div>
                    <span className={`mt-4 px-4 py-1.5 rounded-md border text-xs font-semibold uppercase tracking-[0.22em] shadow-[0_0_14px_rgba(245,158,11,0.25)] ${band.color} ${band.border}`}>
                        {band.label}
                    </span>
                </div>
            </div>
            <div className="mt-3 flex w-full max-w-[340px] justify-between px-4 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
                <span>Lenient</span>
                <span>Strict</span>
            </div>
        </div>
    );
};

const RegulationCard = ({ reg }) => (
    <div className="rounded-lg border border-border bg-card dark:bg-slate-900/60 dark:border-slate-800 p-4 shadow">
        <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold uppercase tracking-[0.2em] text-primary">Article {reg.article}</span>
        </div>
        <p className="text-sm text-foreground mb-2">{reg.description}</p>
        <p className="text-xs text-muted-foreground">{reg.relevance}</p>
    </div>
);

const PrecedentCard = ({ item }) => {
    const match = Math.min(100, Math.max(0, Math.round(item.similarity_score ?? 0)));
    const matchLabel =
        match >= 67 ? 'High overlap' :
            match >= 34 ? 'Moderate overlap' : 'Low overlap';
    const lightCount = 5;
    const activeLights = Math.max(1, Math.round((match / 100) * lightCount));
    return (
        <div className="relative rounded-xl border border-border bg-card dark:bg-slate-950/70 p-5 shadow overflow-hidden">
            <div className="relative z-10 space-y-4">
                <div className="flex items-start justify-between gap-3">
                    <div className="space-y-1">
                        <p className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground flex items-center gap-1">
                            <Flag className="h-3.5 w-3.5 text-primary" /> {item.year} {item.race}
                        </p>
                        <h4 className="font-heading font-semibold text-foreground text-lg tracking-tight">{item.driver}</h4>
                    </div>
                    <div className="flex flex-col items-end gap-1 text-xs">
                        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-muted border border-border text-foreground font-semibold dark:bg-slate-900 dark:border-slate-700">
                            <span>{matchLabel}</span>
                            <div className="flex items-center gap-1">
                                {[...Array(lightCount)].map((_, i) => (
                                    <span
                                        key={i}
                                        className={`h-2.5 w-2.5 rounded-sm ${i < activeLights ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.7)]' : 'bg-slate-300 dark:bg-slate-700'}`}
                                    />
                                ))}
                            </div>
                        </div>
                    </div>
                </div>
                <p className="text-sm text-foreground leading-relaxed">{item.incident}</p>
                <div className="border-t border-dashed border-border pt-3 flex flex-wrap items-center gap-3">
                    <div className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground">Outcome</div>
                    <span className="px-3 py-1.5 rounded-md border font-semibold text-xs uppercase tracking-[0.08em] bg-rose-100 text-rose-800 border-rose-200 dark:bg-rose-900/60 dark:text-rose-100 dark:border-rose-700">
                        {item.penalty}
                    </span>
                </div>
            </div>
        </div>
    );
};

export default function AnalysisDashboard({ result }) {
    const severityStyle = severityStyles[result.penalty_severity] || severityStyles['No Action'];
    const consistencyScore = Math.max(0, Math.min(100, Math.round(result.fairness_rating ?? 0)));

    return (
        <div className="space-y-8">
            <div className="rounded-2xl border border-border bg-card p-6 md:p-8 shadow-2xl relative overflow-hidden">
                <div className="absolute top-0 left-0 right-0 h-1.5 bg-primary" />
                <div className="relative z-10 flex flex-col gap-5">
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
                        <div className="rounded-xl bg-card border border-border dark:bg-slate-950/70 dark:border-slate-800 p-4">
                            <div className="flex items-center gap-2 text-muted-foreground uppercase tracking-[0.2em] text-xs mb-2">
                                <ShieldAlert className="h-4 w-4 text-primary" /> Verdict
                            </div>
                            <p className="text-sm text-foreground leading-relaxed">{result.technical_verdict}</p>
                        </div>
                        <div className="rounded-xl bg-card border border-border dark:bg-slate-950/70 dark:border-slate-800 p-4">
                            <div className="flex items-center gap-2 text-muted-foreground uppercase tracking-[0.2em] text-xs mb-2">
                                <Gauge className="h-4 w-4 text-primary" /> Consistency
                            </div>
                            <ConsistencyGauge score={consistencyScore} />
                        </div>
                        <div className="rounded-xl bg-card border border-border dark:bg-slate-950/70 dark:border-slate-800 p-4">
                            <div className="flex items-center gap-2 text-muted-foreground uppercase tracking-[0.2em] text-xs mb-2">
                                <FileText className="h-4 w-4 text-primary" /> Key Factors
                            </div>
                            <ul className="text-sm text-foreground space-y-2">
                                {result.key_factors.map((factor, idx) => (
                                    <li key={idx} className="flex items-center justify-between gap-3">
                                        <div className="flex items-center gap-2">
                                            <span className="h-2 w-2 rounded-full bg-primary" />
                                            <span>{factor}</span>
                                        </div>
                                        <span className="text-[10px] uppercase tracking-[0.12em] text-slate-400">Signal {idx + 1}</span>
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
