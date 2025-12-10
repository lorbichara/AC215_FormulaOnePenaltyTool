'use client';

import { useEffect, useState } from 'react';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { User, Bot } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function RaceLights({ active }) {
    const [phase, setPhase] = useState(0); // 0 idle, 1-5 lights on, 6 lights out

    useEffect(() => {
        if (!active) {
            setPhase(0);
            return;
        }
        let step = 1;
        setPhase(step);
        const interval = setInterval(() => {
            step = step >= 6 ? 1 : step + 1;
            setPhase(step);
        }, 400);
        return () => clearInterval(interval);
    }, [active]);

    return (
        <div className="flex items-center gap-2">
            {[1, 2, 3, 4, 5].map((light) => {
                const isOn = phase >= light && phase <= 5;
                const isOut = phase === 6;
                return (
                    <span
                        key={light}
                        className="h-3 w-3 rounded-full border border-red-500 transition-all duration-200"
                        style={{
                            backgroundColor: isOn ? '#ff0000' : isOut ? '#0f172a' : '#1f2937',
                            boxShadow: isOn ? '0 0 14px rgba(255,0,0,0.7)' : 'none',
                        }}
                        aria-hidden
                    />
                );
            })}
            <span className="text-xs uppercase tracking-wide text-muted-foreground">
                {phase === 6 ? 'Lights out!' : 'On the grid'}
            </span>
        </div>
    );
}

export default function ChatMessage({ chat, isTyping }) {
    return (
        <div className="flex-grow p-6 overflow-y-auto space-y-6">
            {chat?.messages.map((message) => (
                <div
                    key={message.message_id}
                    className={`flex items-start gap-4 ${
                        message.role === 'user' ? 'justify-end' : ''
                    }`}
                >
                    {message.role === 'assistant' && (
                        <Avatar>
                            <AvatarFallback><Bot /></AvatarFallback>
                        </Avatar>
                    )}
                    <div
                        className={`max-w-lg p-3 rounded-lg ${
                            message.role === 'user'
                                ? 'bg-primary text-primary-foreground'
                                : 'bg-muted'
                        }`}
                    >
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {message.content}
                        </ReactMarkdown>
                    </div>
                    {message.role === 'user' && (
                        <Avatar>
                            <AvatarFallback><User /></AvatarFallback>
                        </Avatar>
                    )}
                </div>
            ))}
            {isTyping && (
                <div className="flex items-start gap-4">
                    <Avatar>
                        <AvatarFallback><Bot /></AvatarFallback>
                    </Avatar>
                    <div className="max-w-lg p-3 rounded-lg bg-muted">
                        <RaceLights active />
                    </div>
                </div>
            )}
        </div>
    );
}
