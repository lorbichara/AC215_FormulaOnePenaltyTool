'use client';

import { useState } from 'react';
import PenaltyUploader from './PenaltyUploader';
import AnalysisResult from './AnalysisResult';
import { analyzePenalty } from '@/lib/DataService';
import { Progress } from '@/components/ui/progress';

export default function AnalyzePage() {
    const [analysisResult, setAnalysisResult] = useState(null);
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleAnalyze = async (file) => {
        setIsLoading(true);
        setError(null);
        try {
            const result = await analyzePenalty(file);
            setAnalysisResult(result);
        } catch (err) {
            setError('An error occurred during analysis.');
        } finally {
            setIsLoading(false);
        }
    };

    const handleReset = () => {
        setAnalysisResult(null);
    };

    return (
        <div className="container mx-auto px-4 py-8">
            {!analysisResult && !isLoading && (
                <PenaltyUploader onAnalyze={handleAnalyze} isLoading={isLoading} />
            )}
            {isLoading && (
                <div className="flex flex-col items-center justify-center">
                    <p className="mb-4">Analyzing document...</p>
                    <Progress value={null} className="w-1/2" />
                </div>
            )}
            {error && <p className="text-destructive">{error}</p>}
            {analysisResult && !isLoading && (
                <AnalysisResult result={analysisResult} onReset={handleReset} />
            )}
        </div>
    );
}