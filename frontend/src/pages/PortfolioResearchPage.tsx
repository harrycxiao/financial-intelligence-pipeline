import { useState } from "react";

import type {
    QuarterlyPortfolioReport,
} from "../types";

import {PortfolioForm} from "../components";
import {PortfolioResults} from "../components";


/* --------------------------------------------------------------------------
 * Component
 * -------------------------------------------------------------------------- */

export default function PortfolioResearchPage() {
    const [
        report,
        setReport,
    ] = useState<QuarterlyPortfolioReport | null>(
        null,
    );

    return (
        <section
            className="
                grid
                gap-8
                lg:grid-cols-[360px_1fr]
                xl:grid-cols-[380px_1fr]
            "
        >
            <PortfolioForm
                onReportGenerated={setReport}
            />

            <PortfolioResults
                report={report}
            />
        </section>
    );
}