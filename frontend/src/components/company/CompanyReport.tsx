import type {
    CompanyResearchReport,
} from "../../types";

import {
    Button,
    Card,
} from "../ui";

import CompanySummary from "./CompanySummary";
import CompanyMetrics from "./CompanyMetrics";
import EvidenceList from "./EvidenceList";

import {
    useState,
} from "react";

import {
    exportCompanyReportPdf,
} from "../../pdf";


/* --------------------------------------------------------------------------
 * Props
 * -------------------------------------------------------------------------- */

interface CompanyReportProps {
    report: CompanyResearchReport | null;
}


/* --------------------------------------------------------------------------
 * Component
 * -------------------------------------------------------------------------- */

export default function CompanyReport({
    report,
}: CompanyReportProps) {

    const [isExporting, setIsExporting] =
        useState(false);

    const handleExportPdf = async (): Promise<void> => {
        if (report === null) {
            return;
        }

        try {
            setIsExporting(true);

            await exportCompanyReportPdf(report);
        } catch (error) {
            console.error(
                "Failed to export company PDF:",
                error,
            );
        } finally {
            setIsExporting(false);
        }
    };

    if (report === null) {
        return (
            <Card
                title="Company Research Report"
                subtitle="Generate a report to view the research results."
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
                            No company report has been generated yet.
                        </p>
                        <p className="text-sm leading-6 text-slate-500">
                            Complete the company research form to review the generated analysis and evidence.
                        </p>
                    </div>
                </div>
            </Card>
        );
    }

    return (
        <section className="space-y-6">

            <div className="flex justify-end">

                <Button
                    type="button"
                    variant="secondary"
                    onClick={handleExportPdf}
                    disabled={isExporting}
                >

                    {
                        isExporting
                            ? "Exporting..."
                            : "Export PDF"
                    }

                </Button>

            </div>

            <CompanySummary
                report={report}
            />

            <CompanyMetrics
                report={report}
            />

            <EvidenceList
                evidence={report.evidence}
            />

        </section>
    );
}
