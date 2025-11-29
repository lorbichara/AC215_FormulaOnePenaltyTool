'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function PenaltyOverviewCard({ overview }) {
    return (
        <Card>
            <CardHeader>
                <CardTitle>{overview.driver} - {overview.infringement}</CardTitle>
            </CardHeader>
            <CardContent>
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <p className="font-medium">Team</p>
                        <p className="text-muted-foreground">{overview.team}</p>
                    </div>
                    <div>
                        <p className="font-medium">Race</p>
                        <p className="text-muted-foreground">{overview.race}</p>
                    </div>
                    <div>
                        <p className="font-medium">Penalty</p>
                        <p className="text-muted-foreground">{overview.penalty}</p>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
}