'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function RegulationViewer({ regulation }) {
    return (
        <Card>
            <CardHeader>
                <CardTitle>Article {regulation.article}: {regulation.title}</CardTitle>
            </CardHeader>
            <CardContent>
                <p className="text-muted-foreground">{regulation.text}</p>
            </CardContent>
        </Card>
    );
}