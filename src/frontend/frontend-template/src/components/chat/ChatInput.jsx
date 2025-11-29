'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Send } from 'lucide-react';

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
                    placeholder="Ask about F1 rules, penalties, or incidents..."
                    value={message}
                    onChange={(e) => setMessage(e.target.value)}
                    onKeyDown={handleKeyDown}
                    className="pr-16 resize-none"
                    rows={1}
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
        </div>
    );
}