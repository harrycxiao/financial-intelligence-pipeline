/*
|--------------------------------------------------------------------------
| Chat Window
|--------------------------------------------------------------------------
|
| Displays the conversation between the user and the AI assistant.
|
| This component is responsible only for rendering messages.
| It owns no chat state itself.
|
*/

import ChatMessage from "./ChatMessage";

import type { ChatMessageData } from "../../types";

interface ChatWindowProps {
    messages: ChatMessageData[];
}

export default function ChatWindow({
    messages,
}: ChatWindowProps) {
    return (
        <section
            className="
                flex-1
                overflow-y-auto
                rounded-xl
                border
                border-slate-200
                bg-white
                shadow-sm
                p-6
            "
        >
            {messages.length === 0 ? (
                <div
                    className="
                        flex
                        min-h-[240px]
                        items-center
                        justify-center
                        text-center
                        text-slate-500
                    "
                >
                    <div className="space-y-4 px-4">
                        <h2 className="text-2xl font-semibold tracking-tight text-slate-900">
                            Financial AI Assistant
                        </h2>

                        <p className="max-w-xl mx-auto text-sm leading-6 text-slate-600">
                            Ask about companies, financial statements, SEC filings, news, or investment research.
                        </p>
                    </div>
                </div>
            ) : (
                <div className="flex flex-col gap-4">
                    {messages.map((message) => (
                        <ChatMessage
                            key={message.id}
                            message={message}
                        />
                    ))}
                </div>
            )}
        </section>
    );
}