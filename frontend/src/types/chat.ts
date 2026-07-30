/*
|--------------------------------------------------------------------------
| Chat Types
|--------------------------------------------------------------------------
|
| Frontend interfaces corresponding to the FastAPI chat schemas.
|
*/

export interface ChatRequest {
    message: string;
}

export interface ChatResponse {
    answer: string;
}

export interface ChatMessageData {
    id?: string;
    role: "user" | "assistant";
    content: string;
    loading?: boolean;
}