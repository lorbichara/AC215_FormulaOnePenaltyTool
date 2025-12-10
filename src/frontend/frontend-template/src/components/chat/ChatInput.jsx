'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Send } from 'lucide-react';

const SAMPLE_PROMPTS = [
    "2024 Austrian GP, Lap 64, Turn 3. Verstappen moved left under braking defending P1 vs Norris, contact caused punctures. Was the penalty fair?",
    "2021 British GP, Lap 1, Copse. Hamilton inside overtake, contact with Verstappen sent him into barriers. Was the 10s penalty consistent?",
    "2023 Las Vegas GP, Lap 1, Turn 1. Verstappen forced Leclerc wide off-track at the start, gained advantage. Should he have yielded or taken a penalty?"
];

export default function ChatInput({ onSendMessage, isTyping }) {
    const [message, setMessage] = useState('');

    const handleSubmit = (e) => {
        e.preventDefault();
        if (message.trim()) {
            onSendMessage({ content: message, role: 'user' });
            setMessage('');
        }
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit(e);
        }
    };

    return (
        <div className="p-4 bg-background/80 backdrop-blur-md">
            <form onSubmit={handleSubmit} className="relative">
                <Textarea
                    placeholder={"> INPUT REQUIRED: Provide incident telemetry & context...\n> FORMAT: [Year] [Grand Prix] | [Driver A] vs [Driver B] | [Lap #]\n> EXAMPLE: '2025 Abu Dhabi GP, Lap 23. Yuki forces Norris off track  while battling and was given a 5 seconds penalty. Was this penalty fair?"}
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyDown={handleKeyDown}
                    className="pr-16 resize-y min-h-[120px]"
                    rows={4}
                />
                <Button
                    type="submit"
                    size="icon"
                    className="absolute top-1/2 right-3 -translate-y-1/2"
                    disabled={!message.trim() || isTyping}
                >
                    <Send className="h-5 w-5" />
                </Button>
            </form>
            <div className="mt-3 flex flex-wrap gap-2">
                {SAMPLE_PROMPTS.map((prompt) => (
                    <button
                        key={prompt}
                        type="button"
                        onClick={() => setMessage(prompt)}
                        className="text-xs px-3 py-2 rounded-md border border-border bg-muted/60 hover:bg-muted transition-colors text-foreground"
                    >
                        {prompt}
                    </button>
                ))}
            </div>
        </div>
    );
}
