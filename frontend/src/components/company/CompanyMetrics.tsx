import type {
    CompanyResearchReport,
} from "../../types";

import {
    Card,
} from "../ui";


/* --------------------------------------------------------------------------
 * Props
 * -------------------------------------------------------------------------- */

interface CompanyMetricsProps {
    report: CompanyResearchReport;
}


/* --------------------------------------------------------------------------
 * Helpers
 * -------------------------------------------------------------------------- */

function formatConfidence(
    confidence: CompanyResearchReport["confidence"],
): string {
    return String(confidence)
        .replaceAll("_", " ")
        .replace(/\b\w/g, (character) => character.toUpperCase());
}


/* --------------------------------------------------------------------------
 * Component
 * -------------------------------------------------------------------------- */

export default function CompanyMetrics({
    report,
}: CompanyMetricsProps) {
    const evidenceCount = report.evidence.length;

    return (
        <Card
            title="Report Details"
            subtitle="Coverage, confidence, and research limitations."
        >
            <div className="space-y-6">

                <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">

                    <div className="rounded-lg border border-[#d5e0dc] bg-[#edf3f1] p-4">
                        <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                            Ticker
                        </dt>

                        <dd className="mt-2 text-lg font-semibold text-slate-900">
                            {report.ticker}
                        </dd>
                    </div>

                    <div className="rounded-lg border border-[#d5e0dc] bg-[#edf3f1] p-4">
                        <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                            As of Date
                        </dt>

                        <dd className="mt-2 text-lg font-semibold text-slate-900">
                            {report.as_of_date}
                        </dd>
                    </div>

                    <div className="rounded-lg border border-[#d5e0dc] bg-[#edf3f1] p-4">
                        <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                            Confidence
                        </dt>

                        <dd className="mt-2 text-lg font-semibold text-slate-900">
                            {formatConfidence(report.confidence)}
                        </dd>
                    </div>

                    <div className="rounded-lg border border-[#d5e0dc] bg-[#edf3f1] p-4">
                        <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                            Evidence Sources
                        </dt>

                        <dd className="mt-2 text-lg font-semibold text-slate-900">
                            {evidenceCount}
                        </dd>
                    </div>

                </dl>

                {report.confidence_explanation.trim() !== "" && (
                    <div>
                        <h3 className="text-sm font-semibold text-slate-900">
                            Confidence Explanation
                        </h3>

                        <p className="mt-2 whitespace-pre-wrap leading-7 text-slate-700">
                            {report.confidence_explanation}
                        </p>
                    </div>
                )}

                {report.limitations.length > 0 && (
                    <div>
                        <h3 className="text-sm font-semibold text-slate-900">
                            Limitations
                        </h3>

                        <ul className="mt-3 list-disc space-y-2 pl-5">
                            {report.limitations.map((limitation, index) => (
                                <li
                                    key={`${index}-${limitation}`}
                                    className="text-slate-700"
                                >
                                    {limitation}
                                </li>
                            ))}
                        </ul>
                    </div>
                )}

            </div>
        </Card>
    );
}
