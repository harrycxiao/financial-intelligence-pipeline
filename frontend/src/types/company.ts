/*
|--------------------------------------------------------------------------
| Company Research Types
|--------------------------------------------------------------------------
|
| TypeScript interfaces corresponding to the company research request and
| response schemas defined in the backend AI layer.
|
*/

import type {
    EvidenceReference,
    ResearchConfidence,
} from "./shared";

/* --------------------------------------------------------------------------
 * Company Research Request
 * -------------------------------------------------------------------------- */

export interface CompanyResearchRequest {
    ticker: string;

    as_of_date: string;

    include_financial_history: boolean;

    financial_history_limit: number;

    include_news: boolean;

    news_days_back: number;

    max_news_articles: number;

    include_filings: boolean;

    filing_limit: number;

    comparison_tickers: string[];

    refresh_recent_data: boolean;
}

/* --------------------------------------------------------------------------
 * Company Research Report
 * -------------------------------------------------------------------------- */

export interface CompanyResearchReport {
    as_of_date: string;

    ticker: string;

    company_name: string;

    company_overview: string;

    investment_thesis: string;

    quantitative_assessment: string | null;

    factor_strengths: string[];

    factor_weaknesses: string[];

    financial_trends: string[];

    valuation_observations: string[];

    recent_developments: string[];

    catalysts: string[];

    risks: string[];

    monitoring_items: string[];

    evidence: EvidenceReference[];

    confidence: ResearchConfidence;

    confidence_explanation: string;

    limitations: string[];
}