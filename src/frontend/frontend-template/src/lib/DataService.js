// src/lib/DataService.js
import axios from 'axios';
import { BASE_API_URL, MOCK_SERVICE, uuid } from './Common';

// Mock data (for when MOCK_SERVICE is true)
let mock_chats = [
    {
        chat_id: '1',
        title: 'What is a black and white flag?',
        messages: [
            { message_id: '1', role: 'user', content: 'What is a black and white flag?', timestamp: new Date().toISOString() },
            { message_id: '2', role: 'assistant', content: 'A black and white flag is shown for unsportsmanlike behaviour.', timestamp: new Date().toISOString() },
        ],
    },
];

// In-memory store for chat history when not mocking
let chats = [];

const apiClient = axios.create({
    baseURL: BASE_API_URL,
});

async function getRealAssistantResponse(prompt) {
    try {
        const response = await apiClient.get('/query/', { params: { prompt } });
        return {
            message_id: uuid(),
            role: 'assistant',
            content: response.data.response,
            timestamp: new Date().toISOString(),
        };
    } catch (error) {
        console.error("Error fetching from API", error);
        const errorMessage = error.response?.data?.error || 'Sorry, I encountered an error. Please try again.';
        return {
            message_id: uuid(),
            role: 'assistant',
            content: errorMessage,
            timestamp: new Date().toISOString(),
        };
    }
}

const mockStartF1Chat = async (message) => {
    const newChat = {
        chat_id: String(mock_chats.length + 1),
        title: message.content.substring(0, 30) + '...',
        messages: [{ ...message, message_id: '1', timestamp: new Date().toISOString() }],
    };
    // Simulate assistant response
    const assistantResponse = {
        message_id: String(newChat.messages.length + 1),
        role: 'assistant',
        content: `This is a mock response to "${message.content}"`,
        timestamp: new Date().toISOString(),
    };
    newChat.messages.push(assistantResponse);
    mock_chats.push(newChat);
    return newChat;
};

const realStartF1Chat = async (message) => {
    const userMessage = {
        ...message,
        message_id: uuid(),
        timestamp: new Date().toISOString(),
    };

    const assistantResponse = await getRealAssistantResponse(message.content);

    const newChat = {
        chat_id: uuid(),
        title: message.content.substring(0, 30) + '...',
        messages: [userMessage, assistantResponse],
    };

    chats.push(newChat);
    return newChat;
};

const mockContinueF1Chat = async (chat_id, message) => {
    const chat = mock_chats.find((c) => c.chat_id === chat_id);
    if (chat) {
        const newMessage = {
            ...message,
            message_id: String(chat.messages.length + 1),
            timestamp: new Date().toISOString(),
        };
        chat.messages.push(newMessage);
        // Simulate assistant response
        const assistantResponse = {
            message_id: String(chat.messages.length + 1),
            role: 'assistant',
            content: `This is a mock response to "${message.content}"`,
            timestamp: new Date().toISOString(),
        };
        chat.messages.push(assistantResponse);
        return chat;
    }
    return null;
};

const realContinueF1Chat = async (chat_id, message) => {
    const chat = chats.find((c) => c.chat_id === chat_id);
    if (chat) {
        const newMessage = {
            ...message,
            message_id: uuid(),
            timestamp: new Date().toISOString(),
        };
        chat.messages.push(newMessage);

        const assistantResponse = await getRealAssistantResponse(message.content);
        chat.messages.push(assistantResponse);

        return chat;
    }
    return null;
};

const mockGetChatHistory = async () => {
    return [...mock_chats].reverse();
};

const realGetChatHistory = async () => {
    return [...chats].reverse();
};

const mockGetChat = async (chat_id) => {
    return mock_chats.find((c) => c.chat_id === chat_id) || null;
};

const realGetChat = async (chat_id) => {
    return chats.find((c) => c.chat_id === chat_id) || null;
};

export const startF1Chat = MOCK_SERVICE ? mockStartF1Chat : realStartF1Chat;
export const continueF1Chat = MOCK_SERVICE ? mockContinueF1Chat : realContinueF1Chat;
export const getChatHistory = MOCK_SERVICE ? mockGetChatHistory : realGetChatHistory;
export const getChat = MOCK_SERVICE ? mockGetChat : realGetChat;

// --- Penalty Analysis ---
const classifySeverity = (text) => {
    const lowered = text.toLowerCase();
    if (lowered.includes('disqual')) return 'Disqualification';
    if (lowered.includes('grid')) return 'Grid Drop';
    if (lowered.includes('drive-through') || lowered.includes('stop-go')) return 'Time Penalty';
    if (lowered.includes('warning') || lowered.includes('reprimand')) return 'Warning';
    return 'No Action';
};

const scoreFromText = (text) => {
    if (!text) return 50;
    const total = [...text].reduce((acc, ch, idx) => acc + ch.charCodeAt(0) * (idx + 1), 0);
    return Math.min(95, Math.max(25, total % 101));
};

const extractRegulations = (text) => {
    const matches = [...text.matchAll(/article\s+([\d\.]+)/gi)];
    if (matches.length) {
        return matches.slice(0, 3).map((match, idx) => ({
            article: match[1],
            description: `Referenced Article ${match[1]}`,
            relevance: 'Cited in the steward reasoning.',
            id: `${match[1]}-${idx}`,
        }));
    }
    return [
        {
            article: '10.2',
            description: 'No specific article detected in the response.',
            relevance: 'Default reference while awaiting richer backend output.',
            id: 'default-article',
        },
    ];
};

const extractPrecedents = (text) => {
    const lines = text.split('\n').filter((l) => l.trim().length > 0);
    const precedents = lines.slice(0, 3).map((line, idx) => ({
        driver: `Driver ${idx + 1}`,
        year: '2024',
        race: 'Grand Prix',
        incident: line.slice(0, 140),
        penalty: 'Assessment',
        similarity_score: 60 + ((idx + 1) * 8) % 30,
        id: `precedent-${idx}`,
    }));
    return precedents.length ? precedents : [];
};

export const analyzePenalty = async (incidentText) => {
    try {
        const prompt = incidentText?.trim() || 'Analyze this Formula 1 penalty incident.';
        const response = await apiClient.get('/query/', { params: { prompt } });
        const raw = response.data?.response || '';

        const penaltySeverity = classifySeverity(raw);
        const fairnessRating = scoreFromText(raw);

        return {
            title: prompt.slice(0, 80),
            fan_summary: raw || 'Awaiting analysis response.',
            technical_verdict: raw || 'No technical verdict returned.',
            penalty_severity: penaltySeverity,
            fairness_rating: fairnessRating,
            regulations_breached: extractRegulations(raw),
            historical_precedents: extractPrecedents(raw),
            key_factors: ['Race conditions', 'Car positioning', 'Previous rulings'].slice(0, 3),
            raw_response: raw,
        };
    } catch (error) {
        console.error('Error analyzing penalty', error);
        throw error;
    }
};
