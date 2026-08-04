import {
    useState,
} from "react";

import type {
    HoldingReport as HoldingReportType,
    QuarterlyPortfolioReport,
} from "../../types";

import PortfolioSummary from "./PortfolioSummary";
import HoldingReport from "./HoldingReport";


/* --------------------------------------------------------------------------
 * Props
 * -------------------------------------------------------------------------- */

interface ReportTabsProps {
    report: QuarterlyPortfolioReport;
}


/* --------------------------------------------------------------------------
 * Constants
 * -------------------------------------------------------------------------- */

const SUMMARY_TAB = "summary";


/* --------------------------------------------------------------------------
 * Component
 * -------------------------------------------------------------------------- */

export default function ReportTabs({
    report,
}: ReportTabsProps) {

    const [
        activeTab,
        setActiveTab,
    ] = useState<string>(
        SUMMARY_TAB,
    );

    /* ----------------------------------------------------------------------
     * Helpers
     * ---------------------------------------------------------------------- */

    const selectedHolding =
        report.holdings.find(
            (holding) =>
                holding.ticker === activeTab,
        ) ?? null;

    function renderTabContent() {

        if (
            activeTab === SUMMARY_TAB
        ) {
            return (
                <PortfolioSummary
                    report={report}
                />
            );
        }

        if (
            selectedHolding !== null
        ) {
            return (
                <HoldingReport
                    holding={selectedHolding}
                />
            );
        }

        return null;
    }

    /* ----------------------------------------------------------------------
     * Render
     * ---------------------------------------------------------------------- */

    return (
        <section className="space-y-6">

            {/* ------------------------------------------------------------------
             * Tab Navigation
             * ------------------------------------------------------------------ */}

            <div
                className="
                    flex
                    flex-wrap
                    gap-2
                    border-b
                    border-slate-200
                    pb-3
                "
            >

                {/* Portfolio Summary */}

                <button
                    type="button"
                    onClick={() =>
                        setActiveTab(
                            SUMMARY_TAB,
                        )
                    }
                    className={`
                        rounded-lg
                        px-4
                        py-2
                        text-sm
                        font-medium
                        transition

                        ${
                            activeTab === SUMMARY_TAB
                                ? `
                                    bg-[#087f68]
                                    text-white
                                `
                                : `
                                    bg-[#e8efed]
                                    text-slate-700
                                    hover:bg-[#dbe7e3]
                                `
                        }
                    `}
                >
                    Portfolio Summary
                </button>

                {/* Holding Tabs */}

                {report.holdings.map(
                    (
                        holding:
                            HoldingReportType,
                    ) => (
                        <button
                            key={
                                holding.ticker
                            }
                            type="button"
                            onClick={() =>
                                setActiveTab(
                                    holding.ticker,
                                )
                            }
                            className={`
                                rounded-lg
                                px-4
                                py-2
                                text-sm
                                font-medium
                                transition

                                ${
                                    activeTab ===
                                    holding.ticker

                                        ? `
                                            bg-[#087f68]
                                            text-white
                                          `

                                        : `
                                            bg-[#e8efed]
                                            text-slate-700
                                            hover:bg-[#dbe7e3]
                                          `
                                }
                            `}
                        >
                            {
                                holding.ticker
                            }
                        </button>
                    ),
                )}

            </div>

            {/* ------------------------------------------------------------------
             * Active Report
             * ------------------------------------------------------------------ */}

            {renderTabContent()}

        </section>
    );
}
