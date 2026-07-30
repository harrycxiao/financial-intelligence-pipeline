import { useState } from "react";

import {
    CompanyForm,
    CompanyReport,
} from "../components/company";

import type {
    CompanyResearchReport,
} from "../types";

export default function CompanyResearchPage() {
    const [report, setReport] =
        useState<CompanyResearchReport | null>(
            null
        );

    return (
        <div
            className="
                grid
                gap-8
                lg:grid-cols-3
                lg:items-stretch
            "
        >
            <div className="h-full">
                <CompanyForm
                    onReportGenerated={
                        setReport
                    }
                />
            </div>

            <div className="lg:col-span-2 h-full">
                <CompanyReport
                    report={report}
                />
            </div>
        </div>
    );
}