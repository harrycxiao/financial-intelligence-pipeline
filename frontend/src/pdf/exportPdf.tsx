import {
    createElement,
    type ReactElement,
} from "react";
import type {
    DocumentProps,
} from "@react-pdf/renderer";

import type {
    CompanyResearchReport,
    QuarterlyPortfolioReport,
} from "../types";

function downloadBlob(
    blob: Blob | null,
    filename: string,
): void {
    if (!blob) {
        throw new Error("Unable to generate PDF blob.");
    }

    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");

    anchor.href = url;
    anchor.download = filename;
    anchor.target = "_blank";
    anchor.rel = "noreferrer";
    anchor.style.display = "none";

    document.body.appendChild(anchor);

    const clickEvent = new MouseEvent("click", {
        view: window,
        bubbles: true,
        cancelable: true,
    });

    const clicked = anchor.dispatchEvent(clickEvent);

    if (!clicked) {
        console.warn(
            "PDF download click event was canceled; opening PDF in new tab.",
        );
        window.open(url, "_blank");
    }

    window.setTimeout(() => {
        anchor.remove();
        URL.revokeObjectURL(url);
    }, 100);
}

export async function exportCompanyReportPdf(
    report: CompanyResearchReport,
): Promise<void> {
    const [
        { pdf },
        { default: CompanyPdfDocument },
    ] = await Promise.all([
        import("@react-pdf/renderer"),
        import("./CompanyPdfDocument"),
    ]);

    const blob = await pdf(
        createElement(CompanyPdfDocument, {
            report,
        }) as unknown as ReactElement<DocumentProps>,
    ).toBlob();

    downloadBlob(
        blob,
        `${report.ticker}-company-research-${report.as_of_date}.pdf`,
    );
}

export async function exportPortfolioReportPdf(
    report: QuarterlyPortfolioReport,
): Promise<void> {
    const [
        { pdf },
        { default: PortfolioPdfDocument },
    ] = await Promise.all([
        import("@react-pdf/renderer"),
        import("./PortfolioPdfDocument"),
    ]);

    try {
        const blob = await pdf(
            createElement(PortfolioPdfDocument, {
                report,
            }) as unknown as ReactElement<DocumentProps>,
        ).toBlob();

        downloadBlob(
            blob,
            `portfolio-research-${report.as_of_date}.pdf`,
        );
    } catch (error) {
        console.error("Portfolio PDF export failed:", error);
        throw error;
    }
}
