'use client';

import { useRef, useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Send } from 'lucide-react';

const SAMPLE_PROMPTS = [
    {
        label: 'Austria 2024 — VER vs NOR',
        text: "2024 Austrian GP, Lap 64, Turn 3. Verstappen moved left under braking defending P1 vs Norris, contact caused punctures. Was the penalty fair?"
    },
    {
        label: 'Silverstone 2021 — HAM vs VER',
        text: "2021 British GP, Lap 1, Copse. Hamilton inside overtake, contact with Verstappen sent him into barriers. Was the 10s penalty consistent?"
    },
    {
        label: 'Vegas 2023 — VER vs LEC',
        text: "2023 Las Vegas GP, Lap 1, Turn 1. Verstappen forced Leclerc wide off-track at the start, gained advantage. Should he have yielded or taken a penalty?"
    }
];

export default function ChatInput({ onSendMessage, isTyping }) {
    const [message, setMessage] = useState('');
    const textareaRef = useRef(null);

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

    const handleSampleClick = (prompt) => {
        setMessage(prompt.text);
        // Place cursor at end and focus for immediate editing/sending
        requestAnimationFrame(() => {
            if (textareaRef.current) {
                const length = prompt.text.length;
                textareaRef.current.focus();
                textareaRef.current.setSelectionRange(length, length);
            }
        });
    };

    return (
        <div className="p-5">
            <form onSubmit={handleSubmit} className="relative">
                <Textarea
                    placeholder={"> INPUT REQUIRED: Provide incident telemetry & context...\n> FORMAT: [Year] [Grand Prix] | [Driver A] vs [Driver B] | [Lap #]\n> EXAMPLE: '2025 Abu Dhabi GP, Lap 23. Yuki forces Norris off track  while battling and was given a 5 seconds penalty. Was this penalty fair?"}
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyDown={handleKeyDown}
                    ref={textareaRef}
                    className="min-h-[120px] resize-y border-slate-200 bg-white pr-16 text-slate-900 placeholder:text-slate-400 shadow-inner shadow-black/5 focus-visible:ring-red-500/60 dark:border-white/15 dark:bg-white/5 dark:text-white dark:shadow-inner dark:shadow-white/5"
                    rows={4}
                />
                <Button
                    type="submit"
                    size="icon"
                    className="absolute top-1/2 right-3 -translate-y-1/2 bg-red-600 text-white shadow-lg shadow-red-500/30 hover:bg-red-700"
                    disabled={!message.trim() || isTyping}
                >
                    <Send className="h-5 w-5" />
                </Button>
            </form>
            <div className="mt-3 flex flex-wrap gap-2">
                {SAMPLE_PROMPTS.map((prompt) => (
                    <button
                        key={prompt.label}
                        type="button"
                        onClick={() => handleSampleClick(prompt)}
                        className="group flex items-center gap-2 rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-[11px] font-mono font-semibold uppercase tracking-tight text-slate-900 shadow-sm shadow-black/10 transition-all hover:-translate-y-0.5 hover:border-slate-300 hover:bg-white dark:border-white/10 dark:bg-white/5 dark:text-slate-100 dark:shadow-black/20 dark:hover:border-white/20 dark:hover:bg-white/10"
                    >
                        <span className="h-1.5 w-1.5 rounded-full bg-slate-400 transition-colors group-hover:bg-rose-400" />
                        {prompt.label}
                    </button>
                ))}
            </div>
        </div>
    );
}
