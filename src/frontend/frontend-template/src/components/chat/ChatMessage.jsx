'use client';

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { User, Bot } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

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
                        <div className="flex items-center gap-2">
                            <span className="h-2 w-2 bg-foreground rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                            <span className="h-2 w-2 bg-foreground rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                            <span className="h-2 w-2 bg-foreground rounded-full animate-bounce"></span>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}