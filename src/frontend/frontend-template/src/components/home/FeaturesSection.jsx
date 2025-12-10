'use client';

import { Card } from '@/components/ui/card';
import { FileCheck, MessageSquare } from 'lucide-react';

const features = [
    {
        icon: <FileCheck className="h-8 w-8" />,
        title: 'In-Depth Document Analysis',
        description: 'Upload an official FIA penalty document in PDF format. Our AI will extract key information, explain the infringement in plain English, and cite the specific regulations involved.',
    },
    {
        icon: <MessageSquare className="h-8 w-8" />,
        title: 'Ask the Expert',
        description: 'Use our chat interface to ask questions about F1 rules, historical penalties, or specific incidents. Get clear, context-aware answers from our knowledgeable AI assistant.',
    },
];

export default function FeaturesSection() {
    return (
        <section className="py-16 px-4 sm:px-6 lg:px-8">
            <div className="max-w-4xl mx-auto">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                    {features.map((feature) => (
                        <Card key={feature.title} className="p-8">
                            <div className="flex items-center gap-4 mb-4">
                                {feature.icon}
                                <h3 className="text-xl font-bold">{feature.title}</h3>
                            </div>
                            <p className="text-muted-foreground">{feature.description}</p>
                        </Card>
                    ))}
                </div>
            </div>
        </section>
    );
}
