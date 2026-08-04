import type {
    QuarterlyPortfolioReport,
    PortfolioMethod,
} from "../../types";

import {
    Card,
} from "../ui";

import HoldingsTable from "./HoldingsTable";


/* --------------------------------------------------------------------------
 * Props
 * -------------------------------------------------------------------------- */

interface PortfolioSummaryProps {
    report: QuarterlyPortfolioReport;
}


/* --------------------------------------------------------------------------
 * Helpers
 * -------------------------------------------------------------------------- */

function formatPortfolioMethod(
    method: PortfolioMethod,
): string {
    return method
        .replaceAll("_", " ")
        .replace(
            /\b\w/g,
            (character) =>
                character.toUpperCase(),
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

export default function PortfolioSummary({
    report,
}: PortfolioSummaryProps) {

    const holdingsCount =
        report.holdings.length;

    return (

        <section className="space-y-6">

            {/* ------------------------------------------------------------------
             * Portfolio Overview
             * ------------------------------------------------------------------ */}

            <Card
                title="Portfolio Research Report"
                subtitle={`${report.as_of_date} • ${formatPortfolioMethod(
                    report.portfolio_method,
                )}`}
            >

                <div className="space-y-6">

                    <p className="whitespace-pre-wrap leading-7 text-slate-700">
                        {report.executive_summary}
                    </p>

                    <dl className="grid gap-4 sm:grid-cols-3">

                        <div className="rounded-lg border border-[#d5e0dc] bg-[#edf3f1] p-4">

                            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                                Holdings
                            </dt>

                            <dd className="mt-2 text-lg font-semibold text-slate-900">
                                {holdingsCount}
                            </dd>

                        </div>

                        <div className="rounded-lg border border-[#d5e0dc] bg-[#edf3f1] p-4">

                            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                                Portfolio Method
                            </dt>

                            <dd className="mt-2 text-lg font-semibold text-slate-900">
                                {formatPortfolioMethod(
                                    report.portfolio_method,
                                )}
                            </dd>

                        </div>

                        <div className="rounded-lg border border-[#d5e0dc] bg-[#edf3f1] p-4">

                            <dt className="text-xs font-medium uppercase tracking-wide text-slate-500">
                                Research Date
                            </dt>

                            <dd className="mt-2 text-lg font-semibold text-slate-900">
                                {report.as_of_date}
                            </dd>

                        </div>

                    </dl>

                </div>

            </Card>

            {/* ------------------------------------------------------------------
             * Holdings
             * ------------------------------------------------------------------ */}

            <Card
                title="Portfolio Holdings"
                subtitle="Selected holdings and portfolio allocations."
            >

                <HoldingsTable
                    holdings={report.holdings}
                />

            </Card>

            {/* ------------------------------------------------------------------
             * Allocation Summary
             * ------------------------------------------------------------------ */}

            <Card
                title="Allocation Summary"
            >

                <p className="whitespace-pre-wrap leading-7 text-slate-700">
                    {report.allocation_summary}
                </p>

            </Card>

            {/* ------------------------------------------------------------------
             * Portfolio Risk Analysis
             * ------------------------------------------------------------------ */}

            <Card
                title="Portfolio Risk Analysis"
            >

                <div className="space-y-6">

                    <ListSection
                        title="Concentration Risks"
                        items={
                            report
                                .portfolio_risk_analysis
                                .concentration_risks
                        }
                    />

                    <ListSection
                        title="Sector Risks"
                        items={
                            report
                                .portfolio_risk_analysis
                                .sector_risks
                        }
                    />

                    <ListSection
                        title="Factor Exposures"
                        items={
                            report
                                .portfolio_risk_analysis
                                .factor_exposures
                        }
                    />

                    <ListSection
                        title="Correlation Risks"
                        items={
                            report
                                .portfolio_risk_analysis
                                .correlation_risks
                        }
                    />

                    <ListSection
                        title="Event Risks"
                        items={
                            report
                                .portfolio_risk_analysis
                                .event_risks
                        }
                    />

                    <ListSection
                        title="Liquidity & Data Warnings"
                        items={
                            report
                                .portfolio_risk_analysis
                                .liquidity_or_data_warnings
                        }
                    />

                    <Card
                        title="Overall Risk Summary"
                    >

                        <p className="whitespace-pre-wrap leading-7 text-slate-700">
                            {
                                report
                                    .portfolio_risk_analysis
                                    .overall_risk_summary
                            }
                        </p>

                    </Card>

                </div>

            </Card>

            <ListSection
                title="Key Portfolio Catalysts"
                items={
                    report.key_portfolio_catalysts
                }
            />

            <ListSection
                title="Monitoring Priorities"
                items={
                    report.monitoring_priorities
                }
            />

            <ListSection
                title="Methodology Notes"
                items={
                    report.methodology_notes
                }
            />

            <ListSection
                title="Limitations"
                items={
                    report.limitations
                }
            />

        </section>

    );
}
