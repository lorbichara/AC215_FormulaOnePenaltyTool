'use client';

import { Card, CardContent } from '@/components/ui/card';
import { UploadCloud } from 'lucide-react';

export default function PenaltyUploader({ onAnalyze, isLoading }) {
    const handleFileChange = (e) => {
        const file = e.target.files[0];
        if (file) {
            onAnalyze(file);
        }
    };

    return (
        <Card>
            <CardContent className="p-6">
                <div className="flex flex-col items-center justify-center p-12 border-2 border-dashed rounded-lg">
                    <UploadCloud className="h-12 w-12 text-muted-foreground" />
                    <p className="mt-4 text-muted-foreground">
                        Drag & drop your PDF here, or{' '}
                        <label className="text-primary font-medium cursor-pointer">
                            click to browse
                            <input
                                type="file"
                                className="hidden"
                                onChange={handleFileChange}
                                accept=".pdf"
                                disabled={isLoading}
                            />
                        </label>
                    </p>
                </div>
            </CardContent>
        </Card>
    );
}