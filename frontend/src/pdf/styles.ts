import {
    StyleSheet,
} from "@react-pdf/renderer";


export const colors = {
    ink: "#0f172a",
    body: "#334155",
    muted: "#64748b",

    border: "#cbd5e1",
    borderDark: "#94a3b8",

    panel: "#f8fafc",
    panelStrong: "#f1f5f9",

    primary: "#1d4ed8",
    primarySoft: "#dbeafe",

    success: "#166534",
    successSoft: "#dcfce7",

    warning: "#854d0e",
    warningSoft: "#fef9c3",

    danger: "#991b1b",
    dangerSoft: "#fee2e2",

    white: "#ffffff",
};


export const styles = StyleSheet.create({

    /* ----------------------------------------------------------------------
     * Page
     * ---------------------------------------------------------------------- */

    page: {
        paddingTop: 48,
        paddingRight: 46,
        paddingBottom: 64,
        paddingLeft: 46,

        fontFamily: "Helvetica",
        fontSize: 9.5,
        lineHeight: 1.5,

        color: colors.ink,
        backgroundColor: colors.white,
    },


    /* ----------------------------------------------------------------------
     * Main Report Header
     * ---------------------------------------------------------------------- */

    header: {
        marginBottom: 22,
        paddingBottom: 15,

        borderBottomWidth: 2,
        borderBottomColor: colors.primary,
        borderBottomStyle: "solid",
    },

    eyebrow: {
        marginBottom: 6,

        fontSize: 8,
        fontWeight: 700,
        letterSpacing: 1.2,

        color: colors.primary,
        textTransform: "uppercase",
    },

    title: {
        marginBottom: 7,

        fontSize: 22,
        fontWeight: 700,
        lineHeight: 1.15,

        color: colors.ink,
    },

    subtitle: {
        fontSize: 9.5,
        lineHeight: 1.5,

        color: colors.muted,
    },


    /* ----------------------------------------------------------------------
     * Header Metadata
     * ---------------------------------------------------------------------- */

    metadataRow: {
        flexDirection: "row",

        marginTop: 14,
        gap: 8,
    },

    metadataCard: {
        flexGrow: 1,
        flexBasis: 0,

        paddingTop: 9,
        paddingRight: 9,
        paddingBottom: 9,
        paddingLeft: 9,

        backgroundColor: colors.panel,

        borderWidth: 0.75,
        borderColor: colors.border,
        borderStyle: "solid",
        borderRadius: 4,
    },

    metadataLabel: {
        marginBottom: 4,

        fontSize: 6.8,
        fontWeight: 700,
        letterSpacing: 0.7,

        color: colors.muted,
        textTransform: "uppercase",
    },

    metadataValue: {
        fontSize: 10,
        fontWeight: 700,

        color: colors.ink,
    },


    /* ----------------------------------------------------------------------
     * Sections
     * ---------------------------------------------------------------------- */

    section: {
        marginBottom: 16,
    },

    sectionTitle: {
        marginBottom: 7,
        paddingBottom: 4,

        fontSize: 12,
        fontWeight: 700,
        lineHeight: 1.2,

        color: colors.ink,

        borderBottomWidth: 0.6,
        borderBottomColor: colors.border,
        borderBottomStyle: "solid",
    },

    subsection: {
        marginBottom: 10,
    },

    subsectionTitle: {
        marginBottom: 4,

        fontSize: 9.5,
        fontWeight: 700,

        color: colors.primary,
    },

    paragraph: {
        lineHeight: 1.5,
        color: colors.body,
    },


    /* ----------------------------------------------------------------------
     * Bullet Lists
     * ---------------------------------------------------------------------- */

    bulletRow: {
        flexDirection: "row",

        marginBottom: 4,
        paddingRight: 2,
    },

    bullet: {
        width: 12,

        fontWeight: 700,
        color: colors.primary,
    },

    bulletText: {
        flexGrow: 1,
        flexBasis: 0,

        lineHeight: 1.5,
        color: colors.body,
    },


    /* ----------------------------------------------------------------------
     * Confidence Badges
     * ---------------------------------------------------------------------- */

    badge: {
        alignSelf: "flex-start",

        marginBottom: 7,

        paddingTop: 3,
        paddingRight: 8,
        paddingBottom: 3,
        paddingLeft: 8,

        borderRadius: 7,

        fontSize: 7.5,
        fontWeight: 700,

        textTransform: "uppercase",
    },

    tableConfidenceBadge: {
        alignSelf: "flex-end",

        paddingTop: 2.5,
        paddingRight: 6,
        paddingBottom: 2.5,
        paddingLeft: 6,

        borderRadius: 6,

        fontSize: 7,
        fontWeight: 700,

        textTransform: "uppercase",
    },


    /* ----------------------------------------------------------------------
     * Supporting Evidence
     * ---------------------------------------------------------------------- */

    evidenceCard: {
        marginBottom: 8,

        paddingTop: 9,
        paddingRight: 9,
        paddingBottom: 9,
        paddingLeft: 9,

        backgroundColor: colors.panel,

        borderWidth: 0.75,
        borderColor: colors.border,
        borderStyle: "solid",
        borderRadius: 4,
    },

    evidenceTitle: {
        marginBottom: 3,

        fontSize: 9,
        fontWeight: 700,
        lineHeight: 1.35,

        color: colors.ink,
    },

    evidenceMeta: {
        marginBottom: 4,

        fontSize: 7.5,
        color: colors.muted,
    },

    evidenceClaim: {
        marginBottom: 4,

        lineHeight: 1.45,
        color: colors.body,
    },

    link: {
        fontSize: 8,

        color: colors.primary,
        textDecoration: "none",
    },


    /* ----------------------------------------------------------------------
     * Holdings Table
     * ---------------------------------------------------------------------- */

    table: {
        width: "100%",
        marginTop: 3,

        borderWidth: 0.75,
        borderColor: colors.border,
        borderStyle: "solid",
        borderRadius: 4,
    },

    tableRowHeader: {
        flexDirection: "row",
        alignItems: "center",

        minHeight: 25,

        backgroundColor: colors.primarySoft,

        borderBottomWidth: 0.75,
        borderBottomColor: colors.borderDark,
        borderBottomStyle: "solid",
    },

    tableRow: {
        flexDirection: "row",
        alignItems: "center",

        minHeight: 26,

        borderBottomWidth: 0.5,
        borderBottomColor: colors.border,
        borderBottomStyle: "solid",
    },

    tableLastRow: {
        flexDirection: "row",
        alignItems: "center",

        minHeight: 26,
    },

    tableCellTicker: {
        flexGrow: 1,
        flexBasis: 0,
        minWidth: 0,

        paddingTop: 6,
        paddingRight: 6,
        paddingBottom: 6,
        paddingLeft: 6,

        fontWeight: 700,
    },

    tableCellCompany: {
        flexGrow: 3,
        flexBasis: 0,
        minWidth: 0,

        paddingTop: 6,
        paddingRight: 6,
        paddingBottom: 6,
        paddingLeft: 6,
    },

    tableCellWeight: {
        flexGrow: 1,
        flexBasis: 0,
        minWidth: 0,

        paddingTop: 6,
        paddingRight: 6,
        paddingBottom: 6,
        paddingLeft: 6,

        textAlign: "right",
    },

    tableCellConfidence: {
        flexGrow: 1.25,
        flexBasis: 0,
        minWidth: 0,

        paddingTop: 5,
        paddingRight: 6,
        paddingBottom: 5,
        paddingLeft: 6,

        alignItems: "flex-end",
    },


    /* ----------------------------------------------------------------------
     * Optional Holding List Cards
     * ---------------------------------------------------------------------- */

    holdingListItem: {
        marginBottom: 8,

        paddingTop: 8,
        paddingRight: 8,
        paddingBottom: 8,
        paddingLeft: 8,

        backgroundColor: colors.panel,

        borderWidth: 0.75,
        borderColor: colors.border,
        borderStyle: "solid",
        borderRadius: 4,
    },

    holdingListTitle: {
        marginBottom: 3,

        fontSize: 10,
        fontWeight: 700,
    },

    holdingListMeta: {
        fontSize: 9,
        color: colors.muted,
    },


    /* ----------------------------------------------------------------------
     * Individual Holding Header
     * ---------------------------------------------------------------------- */

    holdingHeader: {
        marginBottom: 18,

        paddingTop: 13,
        paddingRight: 13,
        paddingBottom: 13,
        paddingLeft: 13,

        backgroundColor: colors.panel,

        borderWidth: 0.75,
        borderColor: colors.border,
        borderStyle: "solid",
        borderRadius: 4,
    },

    holdingTitle: {
        marginBottom: 7,

        fontSize: 17,
        fontWeight: 700,
        lineHeight: 1.2,

        color: colors.ink,
    },

    holdingSubtitle: {
        fontSize: 9,
        lineHeight: 1.3,

        color: colors.muted,
    },


    /* ----------------------------------------------------------------------
     * Footer
     * ---------------------------------------------------------------------- */

    footer: {
        position: "absolute",

        top: 758,
        left: 46,
        right: 46,

        flexDirection: "row",
        justifyContent: "space-between",

        paddingTop: 6,

        borderTopWidth: 0.5,
        borderTopColor: colors.border,
        borderTopStyle: "solid",

        fontSize: 7.5,
        color: colors.muted,
    },
});