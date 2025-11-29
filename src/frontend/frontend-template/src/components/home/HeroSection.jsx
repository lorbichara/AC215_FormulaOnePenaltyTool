'use client';

import { Button } from '@/components/ui/button';
import Link from 'next/link';

export default function HeroSection() {
    return (
        <section className="relative py-20 px-4 sm:px-6 lg:px-8">
            <div className="max-w-4xl mx-auto text-center">
                <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-6">
                    Deconstruct the FIA's Decisions
                </h1>
                <p className="text-lg text-muted-foreground max-w-2xl mx-auto mb-8">
                    Upload a penalty document or chat with our AI to get clear explanations of F1 penalties, backed by regulations and historical data.
                </p>
                <div className="flex flex-wrap justify-center gap-4">
                    <Link href="/analyze">
                        <Button size="lg">
                            Analyze a Penalty
                        </Button>
                    </Link>
                    <Link href="/chat">
                        <Button size="lg" variant="outline">
                            Start Chat
                        </Button>
                    </Link>
                </div>
            </div>
        </section>
    );
}