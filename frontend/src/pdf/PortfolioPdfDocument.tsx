import {
    Document,
    Page,
    Text,
    View,
} from "@react-pdf/renderer";

import type {
    HoldingReport,
    QuarterlyPortfolioReport,
    ResearchConfidence,
} from "../types";

import {
    ConfidenceSection,
    EvidenceSection,
    ListSection,
    PageFooter,
    ReportHeader,
    Section,
    TextSection,
} from "./components";

import {
    colors,
    styles,
} from "./styles";

import {
    formatLabel,
} from "./formatters";


/* --------------------------------------------------------------------------
 * Props
 * -------------------------------------------------------------------------- */

interface PortfolioPdfDocumentProps {
    report: QuarterlyPortfolioReport;
}


/* --------------------------------------------------------------------------
 * Formatting Helpers
 * -------------------------------------------------------------------------- */

function formatWeight(
    weight: number,
): string {
    return `${(weight * 100).toFixed(1)}%`;
}


function confidenceColors(
    confidence: ResearchConfidence,
) {
    switch (confidence) {
        case "high":
            return {
                backgroundColor: colors.successSoft,
                color: colors.success,
            };

        case "moderate":
            return {
                backgroundColor: colors.warningSoft,
                color: colors.warning,
            };

        case "low":
            return {
                backgroundColor: colors.dangerSoft,
                color: colors.danger,
            };
    }
}


/* --------------------------------------------------------------------------
 * Holdings Table
 * -------------------------------------------------------------------------- */

function HoldingsTable({
    holdings,
}: {
    holdings: HoldingReport[];
}) {
    if (holdings.length === 0) {
        return null;
    }

    return (
        <Section title="Portfolio Holdings">
            <View style={styles.table}>

                {/* Header */}

                <View
                    style={styles.tableRowHeader}
                    wrap={false}
                >
                    <Text style={styles.tableCellTicker}>
                        Ticker
                    </Text>

                    <Text style={styles.tableCellCompany}>
                        Company
                    </Text>

                    <Text style={styles.tableCellWeight}>
                        Weight
                    </Text>

                    <View style={styles.tableCellConfidence}>
                        <Text>
                            Confidence
                        </Text>
                    </View>
                </View>


                {/* Rows */}

                {holdings.map((holding, index) => (
                    <View
                        key={holding.ticker}
                        style={
                            index === holdings.length - 1
                                ? styles.tableLastRow
                                : styles.tableRow
                        }
                        wrap={false}
                    >
                        <Text style={styles.tableCellTicker}>
                            {holding.ticker}
                        </Text>

                        <Text style={styles.tableCellCompany}>
                            {holding.company_name}
                        </Text>

                        <Text style={styles.tableCellWeight}>
                            {formatWeight(
                                holding.portfolio_weight,
                            )}
                        </Text>

                        <View style={styles.tableCellConfidence}>
                            <Text
                                style={[
                                    styles.tableConfidenceBadge,
                                    confidenceColors(
                                        holding.confidence,
                                    ),
                                ]}
                            >
                                {formatLabel(
                                    holding.confidence,
                                )}
                            </Text>
                        </View>
                    </View>
                ))}

            </View>
        </Section>
    );
}


/* --------------------------------------------------------------------------
 * Portfolio Overview
 * -------------------------------------------------------------------------- */

function PortfolioOverview({
    report,
}: PortfolioPdfDocumentProps) {
    const risk =
        report.portfolio_risk_analysis;

    return (
        <>
            <ReportHeader
                eyebrow="Portfolio Research"
                title="Quarterly Portfolio Report"
                subtitle={report.executive_summary}
                metadata={[
                    {
                        label: "As of",
                        value: report.as_of_date,
                    },
                    {
                        label: "Method",
                        value: formatLabel(
                            report.portfolio_method,
                        ),
                    },
                    {
                        label: "Holdings",
                        value: String(
                            report.holdings.length,
                        ),
                    },
                ]}
            />

            {/*
             * Selected Tickers was intentionally removed because the same
             * information already appears immediately below in the holdings
             * table.
             */}

            <HoldingsTable
                holdings={report.holdings}
            />

            <TextSection
                title="Allocation Summary"
                content={report.allocation_summary}
            />

            <TextSection
                title="Overall Risk Summary"
                content={risk.overall_risk_summary}
            />

            <ListSection
                title="Concentration Risks"
                items={risk.concentration_risks}
            />

            <ListSection
                title="Sector Risks"
                items={risk.sector_risks}
            />

            <ListSection
                title="Factor Exposures"
                items={risk.factor_exposures}
            />

            <ListSection
                title="Correlation Risks"
                items={risk.correlation_risks}
            />

            <ListSection
                title="Event Risks"
                items={risk.event_risks}
            />

            <ListSection
                title="Liquidity or Data Warnings"
                items={risk.liquidity_or_data_warnings}
            />

            <ListSection
                title="Key Portfolio Catalysts"
                items={report.key_portfolio_catalysts}
            />

            <ListSection
                title="Monitoring Priorities"
                items={report.monitoring_priorities}
            />

            <ListSection
                title="Methodology Notes"
                items={report.methodology_notes}
            />

            <ListSection
                title="Limitations"
                items={report.limitations}
            />
        </>
    );
}


/* --------------------------------------------------------------------------
 * Individual Holding
 * -------------------------------------------------------------------------- */

function HoldingDetails({
    holding,
}: {
    holding: HoldingReport;
}) {
    return (
        <View>

            <View
                style={styles.holdingHeader}
                wrap={false}
            >
                <Text style={styles.eyebrow}>
                    Holding Analysis
                </Text>

                <Text style={styles.holdingTitle}>
                    {holding.company_name}
                </Text>

                <Text style={styles.holdingSubtitle}>
                    {holding.ticker}
                    {"  |  "}
                    {formatWeight(
                        holding.portfolio_weight,
                    )}
                    {" portfolio weight"}
                    {"  |  "}
                    {formatLabel(
                        holding.confidence,
                    )}
                    {" confidence"}
                </Text>
            </View>

            <TextSection
                title="Executive Summary"
                content={holding.summary}
            />

            <TextSection
                title="Investment Thesis"
                content={holding.investment_thesis}
            />

            <TextSection
                title="Selection Rationale"
                content={holding.selection_rationale}
            />

            <ListSection
                title="Quantitative Strengths"
                items={holding.quantitative_strengths}
            />

            <ListSection
                title="Quantitative Weaknesses"
                items={holding.quantitative_weaknesses}
            />

            <ListSection
                title="Catalysts"
                items={holding.catalysts}
            />

            <ListSection
                title="Risks"
                items={holding.risks}
            />

            <ListSection
                title="Recent Developments"
                items={holding.recent_developments}
            />

            <ListSection
                title="Monitoring Items"
                items={holding.monitoring_items}
            />

            <ConfidenceSection
                confidence={holding.confidence}
                explanation={
                    holding.confidence_explanation
                }
            />

            <EvidenceSection
                evidence={holding.evidence}
            />

        </View>
    );
}


/* --------------------------------------------------------------------------
 * Document
 * -------------------------------------------------------------------------- */

export default function PortfolioPdfDocument({
    report,
}: PortfolioPdfDocumentProps) {
    const footerLabel =
        `Portfolio Research | ${report.as_of_date}`;

    return (
        <Document
            title={`Portfolio Research - ${report.as_of_date}`}
            author="Financial Intelligence Pipeline"
            subject="Quarterly portfolio research report"
            keywords={
                "portfolio research, investment research, holdings"
            }
        >

            {/* --------------------------------------------------------------
             * Portfolio-Level Overview
             * -------------------------------------------------------------- */}

            <Page
                size="LETTER"
                style={styles.page}
                wrap
            >
                <PortfolioOverview
                    report={report}
                />

                <PageFooter
                    label={footerLabel}
                />
            </Page>


            {/* --------------------------------------------------------------
             * Individual Holding Reports
             * -------------------------------------------------------------- */}

            {report.holdings.map((holding) => (
                <Page
                    key={holding.ticker}
                    size="LETTER"
                    style={styles.page}
                    wrap
                >
                    <HoldingDetails
                        holding={holding}
                    />

                    <PageFooter
                        label={
                            `${holding.ticker} Holding Research | ` +
                            report.as_of_date
                        }
                    />
                </Page>
            ))}

        </Document>
    );
}