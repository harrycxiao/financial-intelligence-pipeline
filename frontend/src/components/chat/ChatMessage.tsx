/*
|--------------------------------------------------------------------------
| Chat Message
|--------------------------------------------------------------------------
|
| Renders a single message within the chat conversation.
|
| Styling depends on whether the message originated from the user
| or the AI assistant.
|
*/

import type { ChatMessageData } from "../../types";

interface ChatMessageProps {
    message: ChatMessageData;
}

export default function ChatMessage({
    message,
}: ChatMessageProps) {
    const isUser = message.role === "user";

    return (
        <div
            className={`
                flex
                ${isUser ? "justify-end" : "justify-start"}
            `}
        >
            <div
                className={`
                    max-w-[80%]
                    rounded-2xl
                    px-4
                    py-3
                    whitespace-pre-wrap
                    break-words
                    shadow-sm
                    ${
                        isUser
                            ? "bg-blue-600 text-white"
                            : "bg-slate-100 text-slate-900"
                    }
                `}
            >
                {message.loading ? (
                    <div className="animate-pulse">
                        Thinking...
                    </div>
                ) : (
                    message.content
                )}
            </div>
        </div>
    );
}