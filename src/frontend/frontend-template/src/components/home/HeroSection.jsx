'use client';

import { Button } from '@/components/ui/button';
import Link from 'next/link';

export default function HeroSection() {
    return (
        <section className="relative py-20 px-4 sm:px-6 lg:px-8 overflow-hidden">
            <div className="absolute inset-0 pointer-events-none opacity-10 [--check:rgba(15,23,42,0.12)] dark:[--check:rgba(255,255,255,0.12)] [background-image:linear-gradient(45deg,var(--check)_25%,transparent_25%),linear-gradient(-45deg,var(--check)_25%,transparent_25%),linear-gradient(45deg,transparent_75%,var(--check)_75%),linear-gradient(-45deg,transparent_75%,var(--check)_75%)] [background-size:24px_24px] [background-position:0_0,0_12px,12px_-12px,-12px_0]" />
            <div className="absolute left-0 top-0 h-2 w-full bg-gradient-to-r from-primary via-primary/70 to-transparent" />
            <div className="max-w-5xl mx-auto text-center relative z-10">
                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-background/80 border border-border shadow-lg mb-6">
                    <span className="h-2 w-2 rounded-full bg-primary animate-pulse" />
                    <span className="text-xs uppercase tracking-[0.35em] text-muted-foreground">Lights out analytics</span>
                </div>
                <h1 className="text-4xl sm:text-5xl font-heading font-bold tracking-tight mb-6">
                    Deconstruct the FIA's Decisions
                </h1>
                <p className="text-lg text-muted-foreground max-w-3xl mx-auto mb-10">
                    Upload a penalty document or chat with our AI to get clear explanations of F1 penalties, backed by regulations and historical data.
                </p>
                <div className="flex flex-wrap justify-center gap-4">
                    <Link href="/analyze">
                        <Button size="lg" className="relative overflow-hidden">
                            <span className="absolute inset-0 bg-gradient-to-r from-primary/30 via-transparent to-transparent animate-[pulse_2s_ease-in-out_infinite]" />
                            <span className="relative">Analyze a Penalty</span>
                        </Button>
                    </Link>
                    <Link href="/chat">
                        <Button size="lg" variant="outline" className="border-primary/60 text-foreground hover:border-primary hover:text-primary">
                            Start Chat
                        </Button>
                    </Link>
                </div>
                <div className="mt-10 flex flex-wrap justify-center gap-3 text-xs uppercase tracking-[0.25em] text-muted-foreground font-heading">
                    <span className="px-3 py-1 rounded-full border border-border bg-background/70">Regulations</span>
                    <span className="px-3 py-1 rounded-full border border-border bg-background/70">Steward Insights</span>
                    <span className="px-3 py-1 rounded-full border border-border bg-background/70">Historical Precedents</span>
                </div>
            </div>
        </section>
    );
}
