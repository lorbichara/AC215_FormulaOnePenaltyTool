'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { UploadCloud, Sparkles } from 'lucide-react';

const samplePrompt = 'Analyze the penalty for Car 55 at the 2024 Abu Dhabi GP for unsafe release. Was the time penalty consistent with precedents?';

export default function IncidentInput({ onAnalyze, isAnalyzing }) {
    const [text, setText] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!text.trim()) return;
        onAnalyze(text.trim());
    };

    const useSample = () => setText(samplePrompt);

    return (
        <div className="relative overflow-hidden rounded-2xl border border-border bg-card dark:bg-[#0b1120] shadow-2xl px-6 py-8 md:px-10 md:py-12">
            <div className="absolute inset-0 pointer-events-none opacity-10 [--check:rgba(15,23,42,0.14)] dark:[--check:rgba(255,255,255,0.14)] [background-image:linear-gradient(45deg,var(--check)_25%,transparent_25%),linear-gradient(-45deg,var(--check)_25%,transparent_25%),linear-gradient(45deg,transparent_75%,var(--check)_75%),linear-gradient(-45deg,transparent_75%,var(--check)_75%)] [background-size:18px_18px] [background-position:0_0,0_9px,9px_-9px,-9px_0]" />
            <div className="relative flex flex-col gap-6 z-10">
                <div>
                    <p className="text-sm uppercase tracking-[0.3em] text-primary font-heading mb-2 flex items-center gap-2">
                        <span className="h-2 w-2 rounded-full bg-primary animate-pulse" />
                        Steward Console
                    </p>
                    <h2 className="text-3xl md:text-4xl font-heading font-bold text-foreground">
                        Upload the incident for analysis
                    </h2>
                    <p className="text-muted-foreground mt-2 max-w-3xl">
                        Paste incident notes or a summary of the penalty. We’ll cross-check with the regs and historical precedents and return a steward-style decision.
                    </p>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <Textarea
                        value={text}
                        onChange={(e) => setText(e.target.value)}
                        placeholder="Example: Lap 42, Car 16 left the track at Turn 5 and gained an advantage while overtaking..."
                        className="min-h-[140px] bg-black/30 border-slate-800 focus-visible:ring-primary text-base"
                        disabled={isAnalyzing}
                    />
                    <div className="flex flex-wrap items-center gap-3">
                        <Button type="submit" disabled={!text.trim() || isAnalyzing} size="lg">
                            <UploadCloud className="mr-2 h-4 w-4" />
                            Analyze Incident
                        </Button>
                        <Button type="button" variant="secondary" onClick={useSample} disabled={isAnalyzing}>
                            <Sparkles className="mr-2 h-4 w-4" />
                            Try sample prompt
                        </Button>
                        {isAnalyzing && (
                            <span className="text-sm text-muted-foreground animate-pulse">Running lights-out sequence…</span>
                        )}
                    </div>
                </form>
            </div>
        </div>
    );
}
