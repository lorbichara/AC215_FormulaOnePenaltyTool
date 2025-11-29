'use client';

import { Button } from '@/components/ui/button';
import { PlusCircle } from 'lucide-react';

export default function ChatHistorySidebar({ activeChatId, onSelectChat, onNewChat, history }) {
    return (
        <aside className="w-full md:w-80 flex flex-col h-full bg-muted/40">
            <div className="p-4 border-b flex justify-between items-center">
                <h2 className="text-lg font-semibold">Chat History</h2>
                <Button variant="ghost" size="icon" onClick={onNewChat}>
                    <PlusCircle className="h-5 w-5" />
                </Button>
            </div>
            <div className="flex-grow overflow-y-auto">
                <nav className="p-2 space-y-1">
                    {history.map((chat) => (
                        <button
                            key={chat.chat_id}
                            onClick={() => onSelectChat(chat.chat_id)}
                            className={`w-full text-left px-3 py-2 rounded-md text-sm truncate ${
                                activeChatId === chat.chat_id
                                    ? 'bg-accent text-accent-foreground'
                                    : 'hover:bg-accent'
                            }`}
                        >
                            {chat.title}
                        </button>
                    ))}
                </nav>
            </div>
        </aside>
    );
}