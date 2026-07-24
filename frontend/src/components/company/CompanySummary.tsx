import type {
    CompanyResearchReport,
} from "../../types";

import {
    Card,
} from "../ui";


/* --------------------------------------------------------------------------
 * Props
 * -------------------------------------------------------------------------- */

interface CompanySummaryProps {
    report: CompanyResearchReport;
}


/* --------------------------------------------------------------------------
 * Helper Components
 * -------------------------------------------------------------------------- */

interface SectionProps {
    title: string;
    content: string | null;
}

function TextSection({
    title,
    content,
}: SectionProps) {
    if (!content || content.trim() === "") {
        return null;
    }

    return (
        <Card title={title}>
            <p className="whitespace-pre-wrap leading-7 text-slate-700">
                {content}
            </p>
        </Card>
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
                {items.map((item) => (
                    <li
                        key={item}
                        className="text-slate-700"
                    >
                        {item}
                    </li>
                ))}
            </ul>
        </Card>
    );
}


/* --------------------------------------------------------------------------
 * Component
 * -------------------------------------------------------------------------- */

export default function CompanySummary({
    report,
}: CompanySummaryProps) {

    return (
        <div className="space-y-6">

            <Card
                title={report.company_name}
                subtitle={`${report.ticker} • ${report.as_of_date}`}
            >
                <p className="whitespace-pre-wrap leading-7 text-slate-700">
                    {report.company_overview}
                </p>
            </Card>

            <TextSection
                title="Investment Thesis"
                content={report.investment_thesis}
            />

            <TextSection
                title="Quantitative Assessment"
                content={report.quantitative_assessment}
            />

            <ListSection
                title="Factor Strengths"
                items={report.factor_strengths}
            />

            <ListSection
                title="Factor Weaknesses"
                items={report.factor_weaknesses}
            />

            <ListSection
                title="Financial Trends"
                items={report.financial_trends}
            />

            <ListSection
                title="Valuation Observations"
                items={report.valuation_observations}
            />

            <ListSection
                title="Recent Developments"
                items={report.recent_developments}
            />

            <ListSection
                title="Catalysts"
                items={report.catalysts}
            />

            <ListSection
                title="Risks"
                items={report.risks}
            />

            <ListSection
                title="Monitoring Items"
                items={report.monitoring_items}
            />

        </div>
    );
}