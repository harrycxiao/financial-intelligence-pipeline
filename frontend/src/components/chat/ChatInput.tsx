/*
|--------------------------------------------------------------------------
| Chat Input
|--------------------------------------------------------------------------
|
| Input area for composing and sending messages to the AI assistant.
|
| This component owns only the text currently being typed.
| It delegates message handling to its parent component.
|
*/

import { useState } from "react";

import Button from "../ui/Button";

interface ChatInputProps {
    onSend: (message: string) => void;
    disabled?: boolean;
}

export default function ChatInput({
    onSend,
    disabled = false,
}: ChatInputProps) {
    const [message, setMessage] = useState("");

    function handleSend() {
        const trimmed = message.trim();

        if (!trimmed || disabled) {
            return;
        }

        onSend(trimmed);

        setMessage("");
    }

    function handleKeyDown(
        event: React.KeyboardEvent<HTMLTextAreaElement>
    ) {
        if (
            event.key === "Enter" &&
            !event.shiftKey
        ) {
            event.preventDefault();

            handleSend();
        }
    }

    return (
        <section
            className="
                rounded-xl
                border
                border-slate-200
                bg-white
                p-4
                shadow-sm
            "
        >
            <div className="flex gap-4 items-end">
                <textarea
                    className="
                        flex-1
                        resize-none
                        rounded-lg
                        border
                        border-slate-300
                        p-3
                        focus:outline-none
                        focus:ring-2
                        focus:ring-blue-500
                    "
                    rows={3}
                    placeholder="Ask about a company, financial statements, news, SEC filings..."
                    value={message}
                    disabled={disabled}
                    onChange={(event) =>
                        setMessage(event.target.value)
                    }
                    onKeyDown={handleKeyDown}
                />

                <Button
                    onClick={handleSend}
                    disabled={
                        disabled ||
                        message.trim().length === 0
                    }
                >
                    Send
                </Button>
            </div>
        </section>
    );
}