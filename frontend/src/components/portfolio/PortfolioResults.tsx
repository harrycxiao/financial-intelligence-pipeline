import type {
    QuarterlyPortfolioReport,
} from "../../types";

import {
    Button,
    Card,
} from "../ui";

import ReportTabs from "./ReportTabs";

import {
    useState,
} from "react";

import {
    exportPortfolioReportPdf,
} from "../../pdf";


/* --------------------------------------------------------------------------
 * Props
 * -------------------------------------------------------------------------- */

interface PortfolioResultsProps {
    report: QuarterlyPortfolioReport | null;
}


/* --------------------------------------------------------------------------
 * Component
 * -------------------------------------------------------------------------- */

export default function PortfolioResults({
    report,
}: PortfolioResultsProps) {

    const [isExporting, setIsExporting] =
        useState(false);

    const handleExportPdf = async (): Promise<void> => {
        if (report === null) {
            return;
        }

        try {
            setIsExporting(true);

            // Guard against a hanging export by racing with a timeout.
            const timeoutMs = 30_000; // 30 seconds
            await Promise.race([
                exportPortfolioReportPdf(report),
                new Promise((_res, rej) => setTimeout(() => rej(new Error("PDF export timed out")), timeoutMs)),
            ]);
        } catch (error) {
            console.error(
                "Failed to export portfolio PDF:",
                error,
            );
        } finally {
            setIsExporting(false);
        }
    };

    if (report === null) {
        return (
            <Card
                title="Portfolio Research Report"
                subtitle="Generate a report to view the portfolio research results."
            >
                <div
                    className="
                        min-h-[220px]
                        rounded-lg
                        border
                        border-dashed
                        border-slate-300
                        bg-slate-50
                        px-6
                        py-12
                        text-center
                        flex
                        items-center
                        justify-center
                    "
                >
                    <div className="space-y-3">
                        <p className="text-base font-semibold text-slate-900">
                            No portfolio report has been generated yet.
                        </p>
                        <p className="text-sm leading-6 text-slate-500">
                            Generate a portfolio report to compare holdings, risk, and research insights.
                        </p>
                    </div>
                </div>
            </Card>
        );
    }

    return (
        <section className="space-y-6">

            {/* ------------------------------------------------------------------
             * Report Actions
             * ------------------------------------------------------------------ */}

            <div className="flex justify-end">

                <Button
                    type="button"
                    variant="secondary"
                    onClick={handleExportPdf}
                    disabled={isExporting}
                    loading={isExporting}
                >
                    {
                        isExporting
                            ? "Exporting..."
                            : "Export PDF"
                    }
                </Button>

            </div>

            {/* ------------------------------------------------------------------
             * Report Content
             * ------------------------------------------------------------------ */}

            <ReportTabs
                report={report}
            />

        </section>
    );
}
