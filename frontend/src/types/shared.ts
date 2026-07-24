/*
|--------------------------------------------------------------------------
| Shared Research Types
|--------------------------------------------------------------------------
|
| Shared literal types and interfaces used by both company and portfolio
| research schemas.
|
*/

/* --------------------------------------------------------------------------
 * Shared Literal Types
 * -------------------------------------------------------------------------- */

export type EvidenceSourceType =
    | "quantitative"
    | "company_data"
    | "news"
    | "sec_filing";

export type ResearchConfidence =
    | "low"
    | "moderate"
    | "high";

/* --------------------------------------------------------------------------
 * Evidence Reference
 * -------------------------------------------------------------------------- */

export interface EvidenceReference {
    ticker: string | null;

    source_type: EvidenceSourceType;

    title: string;

    claim_supported: string;

    source_date: string | null;

    url: string | null;
}