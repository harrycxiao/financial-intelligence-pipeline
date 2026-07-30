/*
|--------------------------------------------------------------------------
| AI API
|--------------------------------------------------------------------------
|
| High-level frontend functions corresponding to the FastAPI AI routes.
|
*/

import { post } from "./client";

import type {
    ChatRequest,
    ChatResponse,
    CompanyResearchRequest,
    CompanyResearchReport,
    QuarterlyResearchRequest,
    QuarterlyPortfolioReport,
} from "../types";

/* --------------------------------------------------------------------------
 * Company Research
 * -------------------------------------------------------------------------- */

export async function generateCompanyResearch(
    request: CompanyResearchRequest
): Promise<CompanyResearchReport> {
    return post<
        CompanyResearchRequest,
        CompanyResearchReport
    >(
        "/api/ai/company-report",
        request
    );
}

/* --------------------------------------------------------------------------
 * Portfolio Research
 * -------------------------------------------------------------------------- */

export async function generatePortfolioResearch(
    request: QuarterlyResearchRequest
): Promise<QuarterlyPortfolioReport> {
    return post<
        QuarterlyResearchRequest,
        QuarterlyPortfolioReport
    >(
        "/api/ai/portfolio-report",
        request
    );
}

/* --------------------------------------------------------------------------
 * Financial Chat
 * -------------------------------------------------------------------------- */

export async function sendChatMessage(
    request: ChatRequest
): Promise<ChatResponse> {
    return post<
        ChatRequest,
        ChatResponse
    >(
        "/api/ai/chat",
        request
    );
}