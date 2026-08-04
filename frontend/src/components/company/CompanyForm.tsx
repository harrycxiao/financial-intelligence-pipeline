import { useState } from "react";

import { generateCompanyResearch } from "../../api";

import type {
    CompanyResearchRequest,
    CompanyResearchReport,
} from "../../types";

import {
    Button,
    Card,
    LoadingSpinner,
} from "../ui";

/* --------------------------------------------------------------------------
 * Props
 * -------------------------------------------------------------------------- */

interface CompanyFormProps {
    onReportGenerated: (
        report: CompanyResearchReport
    ) => void;
}

/* --------------------------------------------------------------------------
 * Helpers
 * -------------------------------------------------------------------------- */

function getTodayDate(): string {
    const today = new Date();

    const year = today.getFullYear();

    const month = String(
        today.getMonth() + 1
    ).padStart(2, "0");

    const day = String(
        today.getDate()
    ).padStart(2, "0");

    return `${year}-${month}-${day}`;
}

/* --------------------------------------------------------------------------
 * Component
 * -------------------------------------------------------------------------- */

export default function CompanyForm({
    onReportGenerated,
}: CompanyFormProps) {
    /* ----------------------------------------------------------------------
     * Research Inputs
     * ---------------------------------------------------------------------- */

    const [ticker, setTicker] =
        useState("");

    const [asOfDate, setAsOfDate] =
        useState(getTodayDate);

    /* ----------------------------------------------------------------------
     * Advanced Options
     * ---------------------------------------------------------------------- */

    const [
        includeFinancialHistory,
        setIncludeFinancialHistory,
    ] = useState(true);

    const [
        includeNews,
        setIncludeNews,
    ] = useState(true);

    const [
        includeFilings,
        setIncludeFilings,
    ] = useState(true);

    /* ----------------------------------------------------------------------
     * UI State
     * ---------------------------------------------------------------------- */

    const [
        showAdvanced,
        setShowAdvanced,
    ] = useState(false);

    const [
        loading,
        setLoading,
    ] = useState(false);

    const [
        error,
        setError,
    ] = useState("");

    /* ----------------------------------------------------------------------
     * Request Builder
     * ---------------------------------------------------------------------- */

    function buildRequest(): CompanyResearchRequest {
        return {
            ticker: ticker.trim().toUpperCase(),

            as_of_date: asOfDate,

            include_financial_history:
                includeFinancialHistory,

            financial_history_limit: 5,

            include_news: includeNews,

            news_days_back: 90,

            max_news_articles: 10,

            include_filings: includeFilings,

            filing_limit: 10,

            comparison_tickers: [],

            refresh_recent_data: true,
        };
    }

    /* ----------------------------------------------------------------------
     * Form Submission
     * ---------------------------------------------------------------------- */

    const handleSubmit = async (event: any) => {
        event.preventDefault();

        setError("");

        const normalizedTicker =
            ticker.trim().toUpperCase();

        if (normalizedTicker === "") {
            setError(
                "Please enter a company ticker."
            );

            return;
        }

        if (!asOfDate) {
            setError(
                "Please select a research date."
            );

            return;
        }

        if (asOfDate > getTodayDate()) {
            setError(
                "The research date cannot be in the future."
            );

            return;
        }

        try {
            setLoading(true);

            const request = buildRequest();

            const report =
                await generateCompanyResearch(
                    request
                );

            onReportGenerated(report);
        } catch (caughtError) {
            console.error(
                "Company report generation failed:",
                caughtError
            );

            if (
                caughtError instanceof Error &&
                caughtError.message
            ) {
                setError(caughtError.message);
            } else {
                setError(
                    "Failed to generate the company report. Please try again."
                );
            }
        } finally {
            setLoading(false);
        }
    };

    /* ----------------------------------------------------------------------
     * Render
     * ---------------------------------------------------------------------- */

    return (
        <Card
            title="Generate Company Report"
            subtitle="Generate an AI-powered research report for a public company."
        >
            <form
                onSubmit={handleSubmit}
                className="space-y-6"
            >
                {/* Ticker */}

                <div>
                    <label
                        htmlFor="company-ticker"
                        className="mb-2 block text-sm font-medium text-slate-700"
                    >
                        Ticker
                    </label>

                    <input
                        id="company-ticker"
                        name="ticker"
                        type="text"
                        value={ticker}
                        onChange={(event) =>
                            setTicker(
                                event.target.value
                            )
                        }
                        placeholder="NVDA"
                        autoComplete="off"
                        spellCheck={false}
                        disabled={loading}
                        className="
                            w-full
                            rounded-lg
                            border
                            border-slate-300
                            px-3
                            py-2
                            uppercase
                            outline-none
                            transition
                            placeholder:normal-case
                            placeholder:text-slate-400
                            focus:border-emerald-500
                            focus:ring-2
                            focus:ring-emerald-200
                            disabled:cursor-not-allowed
                            disabled:bg-slate-100
                        "
                    />

                    <p className="mt-1 text-xs text-slate-500">
                        Enter a publicly traded
                        company ticker, such as NVDA
                        or AAPL.
                    </p>
                </div>

                {/* Research Date */}

                <div>
                    <label
                        htmlFor="company-as-of-date"
                        className="mb-2 block text-sm font-medium text-slate-700"
                    >
                        Research Date
                    </label>

                    <input
                        id="company-as-of-date"
                        name="asOfDate"
                        type="date"
                        value={asOfDate}
                        max={getTodayDate()}
                        onChange={(event) =>
                            setAsOfDate(
                                event.target.value
                            )
                        }
                        disabled={loading}
                        className="
                            w-full
                            rounded-lg
                            border
                            border-slate-300
                            px-3
                            py-2
                            outline-none
                            transition
                            focus:border-emerald-500
                            focus:ring-2
                            focus:ring-emerald-200
                            disabled:cursor-not-allowed
                            disabled:bg-slate-100
                        "
                    />

                    <p className="mt-1 text-xs text-slate-500">
                        The report will use information
                        available as of this date.
                    </p>
                </div>

                {/* Advanced Settings Toggle */}

                <button
                    type="button"
                    onClick={() =>
                        setShowAdvanced(
                            (currentValue) =>
                                !currentValue
                        )
                    }
                    disabled={loading}
                    aria-expanded={showAdvanced}
                    aria-controls="company-advanced-settings"
                    className="
                        text-sm
                        font-medium
                        text-emerald-700
                        transition
                        hover:text-emerald-900
                        disabled:cursor-not-allowed
                        disabled:opacity-50
                    "
                >
                    {showAdvanced
                        ? "Hide Advanced Settings"
                        : "Show Advanced Settings"}
                </button>

                {/* Advanced Settings */}

                {showAdvanced && (
                    <div
                        id="company-advanced-settings"
                        className="
                            space-y-4
                            rounded-lg
                            border
                            border-[#d5e0dc]
                            bg-[#edf3f1]
                            p-4
                        "
                    >
                        <label className="flex cursor-pointer items-center gap-3">
                            <input
                                type="checkbox"
                                checked={
                                    includeFinancialHistory
                                }
                                onChange={(event) =>
                                    setIncludeFinancialHistory(
                                        event.target
                                            .checked
                                    )
                                }
                                disabled={loading}
                                className="
                                    h-4
                                    w-4
                                    rounded
                                    border-slate-300
                                    text-emerald-700
                                    focus:ring-emerald-500
                                "
                            />

                            <span className="text-sm text-slate-700">
                                Include financial
                                history
                            </span>
                        </label>

                        <label className="flex cursor-pointer items-center gap-3">
                            <input
                                type="checkbox"
                                checked={includeNews}
                                onChange={(event) =>
                                    setIncludeNews(
                                        event.target
                                            .checked
                                    )
                                }
                                disabled={loading}
                                className="
                                    h-4
                                    w-4
                                    rounded
                                    border-slate-300
                                    text-emerald-700
                                    focus:ring-emerald-500
                                "
                            />

                            <span className="text-sm text-slate-700">
                                Include recent news
                            </span>
                        </label>

                        <label className="flex cursor-pointer items-center gap-3">
                            <input
                                type="checkbox"
                                checked={
                                    includeFilings
                                }
                                onChange={(event) =>
                                    setIncludeFilings(
                                        event.target
                                            .checked
                                    )
                                }
                                disabled={loading}
                                className="
                                    h-4
                                    w-4
                                    rounded
                                    border-slate-300
                                    text-emerald-700
                                    focus:ring-emerald-500
                                "
                            />

                            <span className="text-sm text-slate-700">
                                Include SEC filings
                            </span>
                        </label>
                    </div>
                )}

                {/* Error Message */}

                {error && (
                    <div
                        role="alert"
                        className="
                            rounded-lg
                            border
                            border-red-200
                            bg-red-50
                            px-4
                            py-3
                            text-sm
                            text-red-700
                        "
                    >
                        {error}
                    </div>
                )}

                {/* Submit Button */}
                
                {loading ? (

                    <LoadingSpinner
                        message="Generating company report..."
                        size="large"
                    />

                ) : (

                    <Button
                        type="submit"
                        size="large"
                        className="w-full"
                    >
                        Generate Report
                    </Button>

                )}
            </form>
        </Card>
    );
}
