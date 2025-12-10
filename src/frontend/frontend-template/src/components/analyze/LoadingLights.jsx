'use client';

import { useEffect, useState } from 'react';

export default function LoadingLights() {
    const [lights, setLights] = useState(0);
    const [extinguished, setExtinguished] = useState(false);

    useEffect(() => {
        setLights(0);
        setExtinguished(false);

        const lightInterval = 600;
        const interval = setInterval(() => {
            setLights((prev) => {
                if (prev < 5) return prev + 1;
                if (prev === 5 && !extinguished) {
                    setTimeout(() => {
                        setLights(0);
                        setExtinguished(true);
                        setTimeout(() => setExtinguished(false), 800);
                    }, 700);
                }
                return prev;
            });
        }, lightInterval);

        return () => clearInterval(interval);
    }, [extinguished]);

    return (
        <div className="flex flex-col items-center justify-center py-12 w-full">
            <div className="bg-card dark:bg-[#0a0f1d] border border-blue-900/40 shadow-2xl rounded-2xl px-6 py-8 relative overflow-hidden">
                <div className="absolute inset-0 pointer-events-none opacity-10 [--check:rgba(15,23,42,0.12)] dark:[--check:rgba(255,255,255,0.12)] [background-image:linear-gradient(45deg,var(--check)_25%,transparent_25%),linear-gradient(-45deg,var(--check)_25%,transparent_25%),linear-gradient(45deg,transparent_75%,var(--check)_75%),linear-gradient(-45deg,transparent_75%,var(--check)_75%)] [background-size:18px_18px] [background-position:0_0,0_9px,9px_-9px,-9px_0]" />
                <div className="relative flex gap-4 z-10">
                    {[1, 2, 3, 4, 5].map((i) => (
                        <div key={i} className="flex flex-col items-center gap-2">
                            <div className="relative w-12 h-12 md:w-14 md:h-14 bg-black rounded-full border-4 border-slate-800 shadow-[inset_0_2px_8px_rgba(0,0,0,0.8)]">
                                <div
                                    className={`absolute inset-1 rounded-full transition-all duration-150 ${
                                        i <= lights && lights > 0
                                            ? 'bg-[#FF1801] shadow-[0_0_25px_#FF1801] opacity-100'
                                            : 'bg-[#330000] opacity-40'
                                    }`}
                                >
                                    <div className="absolute top-1 right-2 w-3 h-3 bg-white opacity-40 rounded-full blur-[1px]" />
                                </div>
                            </div>
                        </div>
                    ))}
                </div>
            </div>
            <div className="mt-6 flex items-center gap-3 text-muted-foreground">
                <div className="h-2 w-2 rounded-full bg-primary animate-ping" />
                <p className="font-heading font-semibold uppercase tracking-[0.25em] text-sm">
                    The AI powered penalty analyzer is underway... Waiting for lights out...
                </p>
            </div>
        </div>
    );
}
