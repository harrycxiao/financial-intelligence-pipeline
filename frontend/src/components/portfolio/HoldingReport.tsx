import type {
    EvidenceReference,
    HoldingReport as HoldingReportType,
    ResearchConfidence,
} from "../../types";

import {
    Card,
} from "../ui";

import EvidenceList from "../company/EvidenceList";


/* --------------------------------------------------------------------------
 * Props
 * -------------------------------------------------------------------------- */

interface HoldingReportProps {
    holding: HoldingReportType;
}


/* --------------------------------------------------------------------------
 * Helpers
 * -------------------------------------------------------------------------- */

function formatWeight(
    weight: number,
): string {
    return `${(weight * 100).toFixed(1)}%`;
}

function confidenceBadgeClass(
    confidence: ResearchConfidence,
): string {

    switch (confidence) {

        case "high":
            return "bg-green-100 text-green-800";

        case "moderate":
            return "bg-yellow-100 text-yellow-800";

        case "low":
            return "bg-red-100 text-red-800";

        default:
            return "bg-slate-100 text-slate-700";

    }

}

function formatConfidence(
    confidence: ResearchConfidence,
): string {

    return (
        confidence.charAt(0).toUpperCase()
        + confidence.slice(1)
    );

}

interface ListSectionProps {
    title: string;
    items: string[];
}

function ListSection({
    title,
    items,
}: ListSectionProps) {

    if (items.length === 0) {
        return null;
    }

    return (

        <Card title={title}>

            <ul className="list-disc space-y-2 pl-5">

                {items.map(
                    (item) => (

                        <li
                            key={item}
                            className="text-slate-700"
                        >
                            {item}
                        </li>

                    ),
                )}

            </ul>

        </Card>

    );

}


/* --------------------------------------------------------------------------
 * Component
 * -------------------------------------------------------------------------- */

export default function HoldingReport({
    holding,
}: HoldingReportProps) {

    return (

        <section className="space-y-6">

            {/* --------------------------------------------------------------
             * Header
             * -------------------------------------------------------------- */}

            <Card
                title={holding.company_name}
                subtitle={holding.ticker}
            >

                <div className="grid gap-4 sm:grid-cols-2">

                    <div
                        className="
                            rounded-lg
                            border
                            border-slate-200
                            bg-slate-50
                            p-4
                        "
                    >

                        <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                            Portfolio Weight
                        </div>

                        <div className="mt-2 text-2xl font-semibold text-slate-900">
                            {formatWeight(
                                holding.portfolio_weight,
                            )}
                        </div>

                    </div>

                    <div
                        className="
                            rounded-lg
                            border
                            border-slate-200
                            bg-slate-50
                            p-4
                        "
                    >

                        <div className="text-xs font-medium uppercase tracking-wide text-slate-500">
                            Research Confidence
                        </div>

                        <div className="mt-3">

                            <span
                                className={`
                                    inline-flex
                                    rounded-full
                                    px-3
                                    py-1
                                    text-sm
                                    font-medium

                                    ${confidenceBadgeClass(
                                        holding.confidence,
                                    )}
                                `}
                            >
                                {formatConfidence(
                                    holding.confidence,
                                )}
                            </span>

                        </div>

                    </div>

                </div>

            </Card>

            {/* --------------------------------------------------------------
             * Executive Summary
             * -------------------------------------------------------------- */}

            <Card title="Executive Summary">

                <p className="whitespace-pre-wrap leading-7 text-slate-700">
                    {holding.summary}
                </p>

            </Card>

            {/* --------------------------------------------------------------
             * Investment Thesis
             * -------------------------------------------------------------- */}

            <Card title="Investment Thesis">

                <p className="whitespace-pre-wrap leading-7 text-slate-700">
                    {holding.investment_thesis}
                </p>

            </Card>

            {/* --------------------------------------------------------------
             * Selection Rationale
             * -------------------------------------------------------------- */}

            <Card title="Selection Rationale">

                <p className="whitespace-pre-wrap leading-7 text-slate-700">
                    {holding.selection_rationale}
                </p>

            </Card>

            {/* --------------------------------------------------------------
             * Quantitative Strengths
             * -------------------------------------------------------------- */}

            <ListSection
                title="Quantitative Strengths"
                items={
                    holding.quantitative_strengths
                }
            />

            {/* --------------------------------------------------------------
             * Quantitative Weaknesses
             * -------------------------------------------------------------- */}

            <ListSection
                title="Quantitative Weaknesses"
                items={
                    holding.quantitative_weaknesses
                }
            />

            {/* --------------------------------------------------------------
             * Catalysts
             * -------------------------------------------------------------- */}

            <ListSection
                title="Key Catalysts"
                items={
                    holding.catalysts
                }
            />

            {/* --------------------------------------------------------------
             * Risks
             * -------------------------------------------------------------- */}

            <ListSection
                title="Key Risks"
                items={
                    holding.risks
                }
            />

            {/* --------------------------------------------------------------
             * Recent Developments
             * -------------------------------------------------------------- */}

            <ListSection
                title="Recent Developments"
                items={
                    holding.recent_developments
                }
            />

            {/* --------------------------------------------------------------
             * Monitoring Items
             * -------------------------------------------------------------- */}

            <ListSection
                title="Monitoring Priorities"
                items={
                    holding.monitoring_items
                }
            />

            {/* --------------------------------------------------------------
             * Confidence
             * -------------------------------------------------------------- */}

            <Card title="Research Confidence">

                <div className="space-y-4">

                    <div>

                        <span
                            className={`
                                inline-flex
                                rounded-full
                                px-3
                                py-1
                                text-sm
                                font-medium

                                ${confidenceBadgeClass(
                                    holding.confidence,
                                )}
                            `}
                        >
                            {formatConfidence(
                                holding.confidence,
                            )}
                        </span>

                    </div>

                    <p className="whitespace-pre-wrap leading-7 text-slate-700">
                        {
                            holding.confidence_explanation
                        }
                    </p>

                </div>

            </Card>

            {/* --------------------------------------------------------------
             * Evidence
             * -------------------------------------------------------------- */}

            <Card title="Supporting Evidence">

                <EvidenceList
                    evidence={
                        holding.evidence as EvidenceReference[]
                    }
                />

            </Card>

        </section>

    );

}