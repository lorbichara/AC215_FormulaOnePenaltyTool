'use client';

import { useState } from 'react';
import IncidentInput from './IncidentInput';
import LoadingLights from './LoadingLights';
import AnalysisDashboard from './AnalysisDashboard';
import { analyzePenalty } from '@/lib/DataService';
import { Button } from '@/components/ui/button';
import { AlertCircle } from 'lucide-react';

export default function AnalyzePage() {
    const [analysisResult, setAnalysisResult] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleAnalyze = async (incidentText) => {
        setIsLoading(true);
        setError(null);
        try {
            const result = await analyzePenalty(incidentText);
            setAnalysisResult(result);
        } catch (err) {
            setError('We could not reach the analysis service. Please try again.');
        } finally {
            setIsLoading(false);
        }
    };

    const handleReset = () => {
        setAnalysisResult(null);
    };

    return (
        <div className="min-h-screen bg-background">
            <div className="container mx-auto px-4 py-10 space-y-10">
                <div className="flex flex-col gap-2 text-center">
                    <p className="text-sm uppercase tracking-[0.35em] text-muted-foreground font-heading">Penalty Analyzer</p>
                    <h1 className="text-4xl md:text-5xl font-heading font-bold text-foreground">
                        Race Control Decision Desk
                    </h1>
                    <p className="text-muted-foreground max-w-3xl mx-auto">
                        Drop in a link to an official FIA PDF decision or paste the incident summary to generate a steward-style dashboard
                        with fairness, regulations cited, and similar precedents.
                    </p>
                </div>

                <IncidentInput onAnalyze={handleAnalyze} isAnalyzing={isLoading} />

                {error && (
                    <div className="flex items-center gap-3 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-destructive">
                        <AlertCircle className="h-5 w-5" />
                        <span>{error}</span>
                        <Button variant="ghost" size="sm" onClick={() => setError(null)} className="ml-auto text-destructive">
                            Dismiss
                        </Button>
                    </div>
                )}

                {isLoading && <LoadingLights />}

                {analysisResult && !isLoading && (
                    <div className="space-y-4">
                        <div className="flex justify-end">
                            <Button variant="outline" onClick={handleReset}>Analyze another incident</Button>
                        </div>
                        <AnalysisDashboard result={analysisResult} />
                    </div>
                )}
            </div>
        </div>
    );
}
