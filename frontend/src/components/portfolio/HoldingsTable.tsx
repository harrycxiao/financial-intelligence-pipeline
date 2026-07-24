import type {
    HoldingReport,
    ResearchConfidence,
} from "../../types";


/* --------------------------------------------------------------------------
 * Props
 * -------------------------------------------------------------------------- */

interface HoldingsTableProps {
    holdings: HoldingReport[];
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
            return `
                bg-green-100
                text-green-800
            `;

        case "moderate":
            return `
                bg-yellow-100
                text-yellow-800
            `;

        case "low":
            return `
                bg-red-100
                text-red-800
            `;

        default:
            return `
                bg-slate-100
                text-slate-700
            `;
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


/* --------------------------------------------------------------------------
 * Component
 * -------------------------------------------------------------------------- */

export default function HoldingsTable({
    holdings,
}: HoldingsTableProps) {

    return (

        <div className="overflow-x-auto">

            <table
                className="
                    min-w-full
                    border-collapse
                "
            >

                <thead>

                    <tr
                        className="
                            border-b
                            border-slate-200
                            text-left
                        "
                    >

                        <th
                            className="
                                px-4
                                py-3
                                text-xs
                                font-semibold
                                uppercase
                                tracking-wide
                                text-slate-500
                            "
                        >
                            Ticker
                        </th>

                        <th
                            className="
                                px-4
                                py-3
                                text-xs
                                font-semibold
                                uppercase
                                tracking-wide
                                text-slate-500
                            "
                        >
                            Company
                        </th>

                        <th
                            className="
                                px-4
                                py-3
                                text-right
                                text-xs
                                font-semibold
                                uppercase
                                tracking-wide
                                text-slate-500
                            "
                        >
                            Weight
                        </th>

                        <th
                            className="
                                px-4
                                py-3
                                text-center
                                text-xs
                                font-semibold
                                uppercase
                                tracking-wide
                                text-slate-500
                            "
                        >
                            Confidence
                        </th>

                    </tr>

                </thead>

                <tbody>

                    {holdings.map(
                        (holding) => (

                            <tr
                                key={holding.ticker}
                                className="
                                    border-b
                                    border-slate-100
                                    transition
                                    hover:bg-slate-50
                                "
                            >

                                {/* Ticker */}

                                <td
                                    className="
                                        whitespace-nowrap
                                        px-4
                                        py-4
                                        font-semibold
                                        text-slate-900
                                    "
                                >
                                    {holding.ticker}
                                </td>

                                {/* Company */}

                                <td
                                    className="
                                        px-4
                                        py-4
                                        text-slate-700
                                    "
                                >
                                    {holding.company_name}
                                </td>

                                {/* Weight */}

                                <td
                                    className="
                                        whitespace-nowrap
                                        px-4
                                        py-4
                                        text-right
                                        font-medium
                                        text-slate-900
                                    "
                                >
                                    {formatWeight(
                                        holding.portfolio_weight,
                                    )}
                                </td>

                                {/* Confidence */}

                                <td
                                    className="
                                        px-4
                                        py-4
                                        text-center
                                    "
                                >

                                    <span
                                        className={`
                                            inline-flex
                                            rounded-full
                                            px-3
                                            py-1
                                            text-xs
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

                                </td>

                            </tr>

                        ),
                    )}

                </tbody>

            </table>

        </div>

    );

}