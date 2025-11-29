'use client';

import { useState, useEffect } from 'react';
import ChatHistorySidebar from './ChatHistorySidebar';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import { getChatHistory, getChat, startF1Chat, continueF1Chat } from '@/lib/DataService';

export default function ChatPage() {
    const [history, setHistory] = useState([]);
    const [activeChatId, setActiveChatId] = useState(null);
    const [activeChat, setActiveChat] = useState(null);
    const [isTyping, setIsTyping] = useState(false);

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
        if (activeChatId) {
            const loadChat = async () => {
                const chat = await getChat(activeChatId);
                setActiveChat(chat);
            };
            loadChat();
        }
    }, [activeChatId]);

    const handleNewChat = () => {
        setActiveChat(null);
        setActiveChatId(null);
    };

    const handleSelectChat = (chatId) => {
        setActiveChatId(chatId);
    };

    const handleSendMessage = async (message) => {
        setIsTyping(true);
        if (activeChat) {
            const updatedChat = await continueF1Chat(activeChat.chat_id, message);
            setActiveChat(updatedChat);
        } else {
            const newChat = await startF1Chat(message);
            setActiveChat(newChat);
            setActiveChatId(newChat.chat_id);
            const chatHistory = await getChatHistory();
            setHistory(chatHistory);
        }
        setIsTyping(false);
    };

    return (
        <div className="flex h-[calc(100vh-4rem)]">
            <ChatHistorySidebar
                history={history}
                activeChatId={activeChatId}
                onSelectChat={handleSelectChat}
                onNewChat={handleNewChat}
            />
            <div className="flex flex-col flex-grow">
                <ChatMessage chat={activeChat} isTyping={isTyping} />
                <ChatInput onSendMessage={handleSendMessage} isTyping={isTyping} />
            </div>
        </div>
    );
}