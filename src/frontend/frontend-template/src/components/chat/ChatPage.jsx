'use client';

import { useState, useEffect } from 'react';
import ChatHistorySidebar from './ChatHistorySidebar';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import { getChatHistory, getChat, startF1Chat, continueF1Chat } from '@/lib/DataService';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"

export default function ChatPage() {
    const [history, setHistory] = useState([]);
    const [activeChatId, setActiveChatId] = useState(null);
    const [activeChat, setActiveChat] = useState(null);
    const [isTyping, setIsTyping] = useState(false);
    const [model, setModel] = useState('gemini-default');

    useEffect(() => {
        const loadHistory = async () => {
            const chatHistory = await getChatHistory();
            setHistory(chatHistory);
            if (chatHistory.length > 0) {
                setActiveChatId(chatHistory[0].chat_id);
            }
        };
        loadHistory();
    }, []);

    useEffect(() => {
        if (!activeChatId || activeChatId === 'temp') return;
        const loadChat = async () => {
            const chat = await getChat(activeChatId);
            setActiveChat(chat);
        };
        loadChat();
    }, [activeChatId]);

    const handleNewChat = () => {
        setActiveChat(null);
        setActiveChatId(null);
    };

    const handleSelectChat = (chatId) => {
        setActiveChatId(chatId);
    };

    const handleSendMessage = async (message) => {
        const userMessage = {
            ...message,
            message_id: `temp-${Date.now()}`,
        };

        setIsTyping(true);

        // Optimistically render the user message
        setActiveChat((prev) => {
            if (prev) {
                return {
                    ...prev,
                    messages: [...(prev.messages || []), userMessage],
                };
            }
            return {
                chat_id: activeChatId || 'temp',
                title: 'New incident review',
                messages: [userMessage],
            };
        });
        if (!activeChatId) {
            setActiveChatId('temp');
        }

        if (activeChat) {
            const updatedChat = await continueF1Chat(activeChat.chat_id, message, model);
            setActiveChat(updatedChat);
        } else {
            const newChat = await startF1Chat(message, model);
            setActiveChat(newChat);
            setActiveChatId(newChat.chat_id);
            const chatHistory = await getChatHistory();
            setHistory(chatHistory);
        }
        setIsTyping(false);
    };

    return (
        <div className="relative h-[calc(100vh-4rem)] overflow-hidden bg-white text-slate-900 dark:bg-[#0b0c0f] dark:text-slate-100">
            <div className="relative z-10 flex h-full flex-col gap-5 px-6 py-6">
                <header className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-xl shadow-black/10 dark:border-white/10 dark:bg-[#11131a] dark:shadow-2xl dark:shadow-black/40 md:flex-row md:items-center md:justify-between">
                    <div className="space-y-2">
                        <p className="text-[11px] font-semibold uppercase tracking-[0.32em] text-red-600 dark:text-red-200/80">
                            Race Control Console
                        </p>
                        <div className="flex flex-col gap-1">
                            <h1 className="text-2xl font-bold text-slate-900 dark:text-white">Formula One Penalty Desk</h1>
                            <p className="text-sm text-slate-600 dark:text-slate-200">
                                Review incidents, compare precedent, and let the stewarding copilot craft
                                the right call.
                            </p>
                        </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-3">
                        <div className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-[11px] font-semibold uppercase tracking-wide text-slate-900 shadow-inner shadow-white/50 dark:border-white/10 dark:bg-[#0c0e13] dark:text-slate-100 dark:shadow-inner dark:shadow-white/5">
                            Model Selector
                        </div>
                        <Select value={model} onValueChange={setModel}>
                            <SelectTrigger className="w-[190px] border-slate-200 bg-white text-slate-900 shadow-md shadow-black/10 hover:border-red-500/60 focus:ring-1 focus:ring-red-500/60 dark:border-white/10 dark:bg-[#0c0e13] dark:text-white dark:shadow-black/20">
                                <SelectValue placeholder="Select Model" />
                            </SelectTrigger>
                            <SelectContent>
                                <SelectItem value="gemini-finetuned">Gemini Finetuned</SelectItem>
                                <SelectItem value="gemini-default">Gemini Naive</SelectItem>
                            </SelectContent>
                        </Select>
                    </div>
                </header>

                <div className="grid flex-1 gap-5 overflow-hidden lg:grid-cols-[320px_1fr]">
                    <div className="h-full rounded-2xl border border-slate-200 bg-white shadow-xl shadow-black/10 dark:border-white/10 dark:bg-[#0f1117] dark:shadow-2xl dark:shadow-black/30">
                        <ChatHistorySidebar
                            history={history}
                            activeChatId={activeChatId}
                            onSelectChat={handleSelectChat}
                            onNewChat={handleNewChat}
                        />
                    </div>
                    <div className="flex h-full min-h-0 flex-col rounded-2xl border border-slate-200 bg-white shadow-xl shadow-black/10 dark:border-white/10 dark:bg-[#0f1117] dark:shadow-2xl dark:shadow-black/30">
                        <ChatMessage chat={activeChat} isTyping={isTyping} />
                        <div className="border-t border-slate-200 bg-slate-50 dark:border-white/10 dark:bg-[#0c0e13]">
                            <ChatInput onSendMessage={handleSendMessage} isTyping={isTyping} />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}
