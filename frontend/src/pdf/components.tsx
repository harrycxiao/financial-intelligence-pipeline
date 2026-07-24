import type {
    ReactNode,
} from "react";

import {
    Link,
    Text,
    View,
} from "@react-pdf/renderer";

import type {
    EvidenceReference,
    ResearchConfidence,
} from "../types";

import {
    colors,
    styles,
} from "./styles";

import {
    formatLabel,
} from "./formatters";


/* --------------------------------------------------------------------------
 * Report Header
 * -------------------------------------------------------------------------- */

interface ReportHeaderProps {
    eyebrow: string;

    title: string;

    subtitle: string;

    metadata: Array<{
        label: string;
        value: string;
    }>;
}


export function ReportHeader({
    eyebrow,
    title,
    subtitle,
    metadata,
}: ReportHeaderProps) {
    return (
        <View style={styles.header}>

            <Text style={styles.eyebrow}>
                {eyebrow}
            </Text>

            <Text style={styles.title}>
                {title}
            </Text>

            <Text style={styles.subtitle}>
                {subtitle}
            </Text>

            <View style={styles.metadataRow}>
                {metadata.map((item) => (
                    <View
                        key={item.label}
                        style={styles.metadataCard}
                        wrap={false}
                    >
                        <Text style={styles.metadataLabel}>
                            {item.label}
                        </Text>

                        <Text style={styles.metadataValue}>
                            {item.value}
                        </Text>
                    </View>
                ))}
            </View>

        </View>
    );
}


/* --------------------------------------------------------------------------
 * Generic Section
 * -------------------------------------------------------------------------- */

interface SectionProps {
    title: string;

    children: ReactNode;
}


export function Section({
    title,
    children,
}: SectionProps) {
    return (
        <View
            style={styles.section}
            minPresenceAhead={30}
        >
            <Text style={styles.sectionTitle}>
                {title}
            </Text>

            {children}
        </View>
    );
}


/* --------------------------------------------------------------------------
 * Text Section
 * -------------------------------------------------------------------------- */

interface TextSectionProps {
    title: string;

    content: string | null;
}


export function TextSection({
    title,
    content,
}: TextSectionProps) {
    if (!content?.trim()) {
        return null;
    }

    return (
        <Section title={title}>
            <Text style={styles.paragraph}>
                {content}
            </Text>
        </Section>
    );
}


/* --------------------------------------------------------------------------
 * List Section
 * -------------------------------------------------------------------------- */

interface ListSectionProps {
    title: string;

    items: string[];
}


export function ListSection({
    title,
    items,
}: ListSectionProps) {
    if (items.length === 0) {
        return null;
    }

    return (
        <Section title={title}>
            {items.map((item, index) => (
                <View
                    key={`${index}-${item}`}
                    style={styles.bulletRow}
                >
                    <Text style={styles.bullet}>
                        {"\u2022"}
                    </Text>

                    <Text style={styles.bulletText}>
                        {item}
                    </Text>
                </View>
            ))}
        </Section>
    );
}


/* --------------------------------------------------------------------------
 * Confidence
 * -------------------------------------------------------------------------- */

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


interface ConfidenceSectionProps {
    confidence: ResearchConfidence;

    explanation: string;
}


export function ConfidenceSection({
    confidence,
    explanation,
}: ConfidenceSectionProps) {
    return (
        <Section title="Research Confidence">

            <Text
                style={[
                    styles.badge,
                    confidenceColors(confidence),
                ]}
            >
                {formatLabel(confidence)}
            </Text>

            <Text style={styles.paragraph}>
                {explanation}
            </Text>

        </Section>
    );
}


/* --------------------------------------------------------------------------
 * Evidence
 * -------------------------------------------------------------------------- */

interface EvidenceSectionProps {
    evidence: EvidenceReference[];
}


export function EvidenceSection({
    evidence,
}: EvidenceSectionProps) {
    if (evidence.length === 0) {
        return null;
    }

    return (
        <Section title="Supporting Evidence">

            {evidence.map((item, index) => {
                const metadata = [
                    formatLabel(item.source_type),
                    item.ticker,
                    item.source_date,
                ]
                    .filter(Boolean)
                    .join("  |  ");

                return (
                    <View
                        key={`${index}-${item.title}`}
                        style={styles.evidenceCard}
                    >
                        <Text style={styles.evidenceTitle}>
                            {item.title}
                        </Text>

                        <Text style={styles.evidenceMeta}>
                            {metadata}
                        </Text>

                        <Text style={styles.evidenceClaim}>
                            {item.claim_supported}
                        </Text>

                        {item.url ? (
                            <Link
                                src={item.url}
                                style={styles.link}
                            >
                                View source
                            </Link>
                        ) : null}
                    </View>
                );
            })}

        </Section>
    );
}


/* --------------------------------------------------------------------------
 * Page Footer
 * -------------------------------------------------------------------------- */

interface PageFooterProps {
    label: string;
}


export function PageFooter({
    label,
}: PageFooterProps) {
    return (
        <View
            style={styles.footer}
            fixed
        >
            <Text>
                {label}
            </Text>

            <Text
                render={({
                    pageNumber,
                    totalPages,
                }) =>
                    `Page ${pageNumber} of ${totalPages}`
                }
            />
        </View>
    );
}