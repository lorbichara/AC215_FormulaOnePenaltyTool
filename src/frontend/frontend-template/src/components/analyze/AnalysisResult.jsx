'use client';

import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import PenaltyOverviewCard from './PenaltyOverviewCard';
import RegulationViewer from './RegulationViewer';

export default function AnalysisResult({ result, onReset }) {
    return (
        <div>
            <div className="flex justify-end mb-4">
                <Button onClick={onReset}>Analyze Another Document</Button>
            </div>
            <Tabs defaultValue="overview">
                <TabsList>
                    <TabsTrigger value="overview">Overview</TabsTrigger>
                    <TabsTrigger value="explanation">Explanation</TabsTrigger>
                    <TabsTrigger value="regulations">Regulations</TabsTrigger>
                    <TabsTrigger value="history">Historical Precedents</TabsTrigger>
                </TabsList>
                <TabsContent value="overview" className="mt-4">
                    <PenaltyOverviewCard overview={result.overview} />
                </TabsContent>
                <TabsContent value="explanation" className="mt-4">
                    <p>{result.explanation}</p>
                </TabsContent>
                <TabsContent value="regulations" className="mt-4 space-y-4">
                    {result.regulations.map((reg) => (
                        <RegulationViewer key={reg.article} regulation={reg} />
                    ))}
                </TabsContent>
                <TabsContent value="history" className="mt-4">
                    <ul>
                        {result.history.map((item, index) => (
                            <li key={index} className="mb-2">
                                <strong>{item.race}:</strong> {item.driver} - {item.infringement} ({item.penalty})
                            </li>
                        ))}
                    </ul>
                </TabsContent>
            </Tabs>
        </div>
    );
}