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
        }, 600);
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
            <span className="text-xs uppercase tracking-wide text-slate-700 dark:text-slate-200">
                {phase === 6 ? 'Lights out!' : 'On the grid'}
            </span>
        </div>
    );
}

export default function ChatMessage({ chat, isTyping }) {
    return (
        <div className="flex-1 min-h-0 overflow-y-auto px-6 py-6">
            <div className="mx-auto flex w-full max-w-4xl flex-col gap-6">
                {chat?.messages.map((message) => (
                    <div
                        key={message.message_id}
                        className={`flex items-start gap-4 ${
                            message.role === 'user' ? 'justify-end' : ''
                        }`}
                    >
                        {message.role === 'assistant' && (
                            <Avatar>
                                <AvatarImage src="/assets/logo.jpeg" alt="F1 Steward" />
                                <AvatarFallback><Bot /></AvatarFallback>
                            </Avatar>
                        )}
                        <div
                            className={`max-w-2xl rounded-2xl border p-4 text-[15px] leading-relaxed shadow-lg transition-all ${
                                message.role === 'user'
                                    ? 'border-red-500/60 bg-red-600 text-white shadow-red-500/30 dark:border-red-500/50 dark:bg-red-600 dark:text-white'
                                    : 'border-slate-200 bg-slate-50 text-slate-900 shadow-black/5 dark:border-white/10 dark:bg-[#11131a] dark:text-slate-50 dark:shadow-black/20'
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
                            <AvatarImage src="/assets/logo.jpeg" alt="F1 Steward" />
                            <AvatarFallback><Bot /></AvatarFallback>
                        </Avatar>
                        <div className="max-w-2xl rounded-2xl border border-white/10 bg-white/10 p-4 shadow-lg shadow-black/20 backdrop-blur">
                            <RaceLights active />
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
