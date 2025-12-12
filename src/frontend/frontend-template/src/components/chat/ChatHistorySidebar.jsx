'use client';

import { Button } from '@/components/ui/button';
import { PlusCircle } from 'lucide-react';

export default function ChatHistorySidebar({ activeChatId, onSelectChat, onNewChat, history }) {
    return (
        <aside className="flex h-full w-full flex-col text-slate-900 dark:text-slate-100">
            <div className="flex items-center justify-between border-b border-slate-200 px-4 py-4 dark:border-white/10">
                <div>
                    <p className="text-[11px] uppercase tracking-[0.26em] text-red-600 dark:text-rose-100/80">Sessions</p>
                    <h2 className="text-lg font-semibold text-slate-900 dark:text-white">Chat History</h2>
                </div>
                <Button
                    variant="ghost"
                    size="icon"
                    onClick={onNewChat}
                    className="text-slate-900 hover:bg-slate-100 dark:text-slate-100 dark:hover:bg-white/10"
                >
                    <PlusCircle className="h-5 w-5" />
                </Button>
            </div>
            <div className="flex-grow overflow-y-auto">
                <nav className="space-y-2 px-3 py-3">
                    {history.map((chat) => (
                        <button
                            key={chat.chat_id}
                            onClick={() => onSelectChat(chat.chat_id)}
                            className={`w-full truncate rounded-xl border px-4 py-3 text-left text-sm transition-all duration-150 ${
                                activeChatId === chat.chat_id
                                    ? 'border-red-500/60 bg-red-50 text-red-900 shadow-md shadow-red-200 dark:border-rose-400/60 dark:bg-rose-500/20 dark:text-white dark:shadow-lg dark:shadow-rose-500/20'
                                    : 'border-slate-200 bg-slate-50 text-slate-900 hover:-translate-y-0.5 hover:border-slate-300 hover:bg-white dark:border-white/5 dark:bg-white/5 dark:text-slate-100 dark:hover:border-white/15 dark:hover:bg-white/10'
                            }`}
                        >
                            {chat.title}
                        </button>
                    ))}
                    {history.length === 0 && (
                        <div className="rounded-xl border border-dashed border-slate-200 bg-slate-50 px-4 py-6 text-sm text-slate-600 dark:border-white/10 dark:bg-white/5 dark:text-slate-200">
                            No sessions yet. Start a new incident review to see it here.
                        </div>
                    )}
                </nav>
            </div>
        </aside>
    );
}
