/*
|--------------------------------------------------------------------------
| Chat Page
|--------------------------------------------------------------------------
|
| Main page for the AI Financial Assistant.
|
| This component owns the conversation state and coordinates communication
| with the backend chat API.
|
*/

import { useState } from "react";

import { sendChatMessage } from "../api/ai";

import ChatInput from "../components/chat/ChatInput";
import ChatWindow from "../components/chat/ChatWindow";

import type { ChatMessageData } from "../types";

export default function ChatPage() {
    const [messages, setMessages] = useState<ChatMessageData[]>([]);
    const [loading, setLoading] = useState(false);

    async function handleSend(message: string) {
        const userMessage: ChatMessageData = {
            id: crypto.randomUUID(),
            role: "user",
            content: message,
        };

        const loadingId = crypto.randomUUID();

        const loadingMessage: ChatMessageData = {
            id: loadingId,
            role: "assistant",
            content: "Thinking...",
            loading: true,
        };

        setMessages((previousMessages) => [
            ...previousMessages,
            userMessage,
            loadingMessage,
        ]);

        setLoading(true);

        try {
            const response = await sendChatMessage({
                message,
            });

            setMessages((previousMessages) =>
                previousMessages.map((message) =>
                    message.id === loadingId
                        ? {
                              id: loadingId,
                              role: "assistant",
                              content: response.answer,
                          }
                        : message
                )
            );
        } catch (error) {
            console.error(error);

            setMessages((previousMessages) =>
                previousMessages.map((message) =>
                    message.id === loadingId
                        ? {
                              id: loadingId,
                              role: "assistant",
                              content:
                                  "Sorry, something went wrong while contacting the server.",
                          }
                        : message
                )
            );
        } finally {
            setLoading(false);
        }
    }

    return (
        <main
            className="
                flex
                flex-1
                min-h-0
                flex-col
                gap-6
            "
        >
            <ChatWindow
                messages={messages}
            />

            <ChatInput
                onSend={handleSend}
                disabled={loading}
            />
        </main>
    );
}