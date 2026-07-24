import {
    Document,
    Page,
} from "@react-pdf/renderer";

import type {
    CompanyResearchReport,
} from "../types";

import {
    ConfidenceSection,
    EvidenceSection,
    ListSection,
    PageFooter,
    ReportHeader,
    TextSection,
} from "./components";
import { styles } from "./styles";

interface CompanyPdfDocumentProps {
    report: CompanyResearchReport;
}

export default function CompanyPdfDocument({
    report,
}: CompanyPdfDocumentProps) {
    return (
        <Document
            title={`${report.company_name} Company Research`}
            author="Financial Intelligence Pipeline"
            subject={`Company research report for ${report.ticker}`}
            keywords={`${report.ticker}, company research, investment research`}
        >
            <Page
                size="LETTER"
                style={styles.page}
                wrap
            >
                <ReportHeader
                    eyebrow="Company Research"
                    title={report.company_name}
                    subtitle={report.company_overview}
                    metadata={[
                        {
                            label: "Ticker",
                            value: report.ticker,
                        },
                        {
                            label: "As of",
                            value: report.as_of_date,
                        },
                        {
                            label: "Confidence",
                            value: report.confidence.toUpperCase(),
                        },
                    ]}
                />

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
                <ConfidenceSection
                    confidence={report.confidence}
                    explanation={report.confidence_explanation}
                />
                <ListSection
                    title="Limitations"
                    items={report.limitations}
                />
                <EvidenceSection evidence={report.evidence} />

                <PageFooter
                    label={`${report.ticker} Company Research | ${report.as_of_date}`}
                />
            </Page>
        </Document>
    );
}
