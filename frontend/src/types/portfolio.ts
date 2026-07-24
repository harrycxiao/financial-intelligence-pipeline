/*
|--------------------------------------------------------------------------
| Portfolio Research Types
|--------------------------------------------------------------------------
|
| TypeScript interfaces corresponding to the portfolio research request and
| response schemas defined in the backend AI layer.
|
*/

import type {
    EvidenceReference,
    ResearchConfidence,
} from "./shared";

/* --------------------------------------------------------------------------
 * Shared Literal Types
 * -------------------------------------------------------------------------- */

export type PortfolioMethod =
    | "equal_weight"
    | "top_n_equal_weight"
    | "score_weighted"
    | "risk_adjusted_score_weighted"
    | "minimum_variance"
    | "maximum_sharpe"
    | "mean_variance"
    | "risk_parity"
    | "hierarchical_risk_parity";

export type PeriodMode =
    | "quarterly"
    | "annual"
    | "raw";

/* --------------------------------------------------------------------------
 * Quarterly Portfolio Research Request
 * -------------------------------------------------------------------------- */

export interface QuarterlyResearchRequest {
    as_of_date: string;

    universe_tickers?: string[];

    portfolio_method: PortfolioMethod;

    period_mode: PeriodMode;

    top_screen_n: number;

    final_portfolio_n: number;

    include_news: boolean;

    news_days_back: number;

    max_news_articles_per_ticker: number;

    include_filings: boolean;

    filing_limit_per_ticker: number;

    refresh_quantitative_inputs: boolean;

    refresh_recent_data: boolean;

    use_cache: boolean;
}

/* --------------------------------------------------------------------------
 * Holding Report
 * -------------------------------------------------------------------------- */

export interface HoldingReport {
    ticker: string;

    company_name: string;

    portfolio_weight: number;

    summary: string;

    investment_thesis: string;

    selection_rationale: string;

    quantitative_strengths: string[];

    quantitative_weaknesses: string[];

    catalysts: string[];

    risks: string[];

    recent_developments: string[];

    monitoring_items: string[];

    evidence: EvidenceReference[];

    confidence: ResearchConfidence;

    confidence_explanation: string;
}

/* --------------------------------------------------------------------------
 * Portfolio Risk Report
 * -------------------------------------------------------------------------- */

export interface PortfolioRiskReport {
    concentration_risks: string[];

    sector_risks: string[];

    factor_exposures: string[];

    correlation_risks: string[];

    event_risks: string[];

    liquidity_or_data_warnings: string[];

    overall_risk_summary: string;
}

/* --------------------------------------------------------------------------
 * Quarterly Portfolio Report
 * -------------------------------------------------------------------------- */

export interface QuarterlyPortfolioReport {
    as_of_date: string;

    portfolio_method: PortfolioMethod;

    executive_summary: string;

    selected_tickers: string[];

    holdings: HoldingReport[];

    allocation_summary: string;

    portfolio_risk_analysis: PortfolioRiskReport;

    key_portfolio_catalysts: string[];

    monitoring_priorities: string[];

    methodology_notes: string[];

    limitations: string[];
}