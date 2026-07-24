import type {
    CompanyResearchReport,
    EvidenceReference,
} from "../../types";

import {
    Card,
} from "../ui";


/* --------------------------------------------------------------------------
 * Props
 * -------------------------------------------------------------------------- */

interface EvidenceListProps {
    evidence: CompanyResearchReport["evidence"];
}


/* --------------------------------------------------------------------------
 * Helpers
 * -------------------------------------------------------------------------- */

function formatSourceType(
    sourceType: EvidenceReference["source_type"],
): string {
    return sourceType
        .replaceAll("_", " ")
        .replace(
            /\b\w/g,
            (character) =>
                character.toUpperCase(),
        );
}


/* --------------------------------------------------------------------------
 * Component
 * -------------------------------------------------------------------------- */

export default function EvidenceList({
    evidence,
}: EvidenceListProps) {
    if (evidence.length === 0) {
        return null;
    }

    return (
        <Card
            title="Supporting Evidence"
            subtitle="Sources and claims used to generate the research report."
        >
            <div className="space-y-4">
                {evidence.map(
                    (reference, index) => (
                        <article
                            key={[
                                reference.source_type,
                                reference.title,
                                reference.source_date,
                                index,
                            ].join("-")}
                            className="
                                rounded-lg
                                border
                                border-slate-200
                                bg-white
                                p-4
                            "
                        >
                            <div
                                className="
                                    flex
                                    flex-wrap
                                    items-start
                                    justify-between
                                    gap-3
                                "
                            >
                                <div>
                                    <h3
                                        className="
                                            font-semibold
                                            text-slate-900
                                        "
                                    >
                                        {reference.title}
                                    </h3>

                                    <div
                                        className="
                                            mt-1
                                            flex
                                            flex-wrap
                                            items-center
                                            gap-x-2
                                            gap-y-1
                                            text-sm
                                            text-slate-500
                                        "
                                    >
                                        {reference.ticker && (
                                            <span>
                                                {reference.ticker}
                                            </span>
                                        )}

                                        {reference.ticker &&
                                            reference.source_date && (
                                                <span
                                                    aria-hidden="true"
                                                >
                                                    •
                                                </span>
                                            )}

                                        {reference.source_date && (
                                            <span>
                                                {
                                                    reference.source_date
                                                }
                                            </span>
                                        )}
                                    </div>
                                </div>

                                <span
                                    className="
                                        rounded-full
                                        bg-slate-100
                                        px-3
                                        py-1
                                        text-xs
                                        font-medium
                                        text-slate-700
                                    "
                                >
                                    {formatSourceType(
                                        reference.source_type,
                                    )}
                                </span>
                            </div>

                            <div className="mt-4">
                                <p
                                    className="
                                        text-xs
                                        font-medium
                                        uppercase
                                        tracking-wide
                                        text-slate-500
                                    "
                                >
                                    Claim Supported
                                </p>

                                <p
                                    className="
                                        mt-1
                                        leading-7
                                        text-slate-700
                                    "
                                >
                                    {reference.claim_supported}
                                </p>
                            </div>

                            {reference.url && (
                                <a
                                    href={reference.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="
                                        mt-4
                                        inline-flex
                                        text-sm
                                        font-medium
                                        text-blue-600
                                        hover:text-blue-700
                                        hover:underline
                                    "
                                >
                                    View source
                                </a>
                            )}
                        </article>
                    ),
                )}
            </div>
        </Card>
    );
}