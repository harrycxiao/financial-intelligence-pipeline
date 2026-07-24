/*
|--------------------------------------------------------------------------
| HTTP Client
|--------------------------------------------------------------------------
|
| Generic HTTP helper used by the frontend to communicate with the
| FastAPI backend.
|
| All networking details should remain inside this file.
|
*/

const API_BASE_URL =
    import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(
    endpoint: string,
    options: RequestInit = {}
): Promise<T> {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        headers: {
            "Content-Type": "application/json",
            ...(options.headers ?? {}),
        },
        ...options,
    });

    if (!response.ok) {
        const message = await response.text();

        throw new Error(
            `API Error ${response.status}: ${
                message || response.statusText
            }`
        );
    }

    return (await response.json()) as T;
}

export async function get<T>(endpoint: string): Promise<T> {
    return request<T>(endpoint, {
        method: "GET",
    });
}

export async function post<TRequest, TResponse>(
    endpoint: string,
    body: TRequest
): Promise<TResponse> {
    return request<TResponse>(endpoint, {
        method: "POST",
        body: JSON.stringify(body),
    });
}