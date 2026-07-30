import {
    useState,
    type FormEvent,
} from "react";

import {
    generatePortfolioResearch,
} from "../../api";

import type {
    PortfolioMethod,
    QuarterlyPortfolioReport,
    QuarterlyResearchRequest,
} from "../../types";

import {
    Button,
    Card,
    LoadingSpinner,
} from "../ui";


/* --------------------------------------------------------------------------
 * Types
 * -------------------------------------------------------------------------- */

type Quarter = 1 | 2 | 3 | 4;

interface PortfolioFormProps {
    onReportGenerated: (
        report: QuarterlyPortfolioReport
    ) => void;
}

interface ResearchPeriod {
    year: number;
    quarter: Quarter;
}

interface PortfolioMethodOption {
    value: PortfolioMethod;
    label: string;
    description: string;
}


/* --------------------------------------------------------------------------
 * Constants
 * -------------------------------------------------------------------------- */

const PORTFOLIO_METHOD_OPTIONS: PortfolioMethodOption[] = [
    {
        value: "equal_weight",
        label: "Equal Weight",
        description:
            "Assigns the same weight to every selected holding.",
    },
    {
        value: "top_n_equal_weight",
        label: "Top-N Equal Weight",
        description:
            "Selects the three highest-ranked holdings and weights them equally.",
    },
    {
        value: "score_weighted",
        label: "Score Weighted",
        description:
            "Allocates more weight to holdings with stronger factor scores.",
    },
    {
        value: "risk_adjusted_score_weighted",
        label: "Risk-Adjusted Score Weighted",
        description:
            "Weights factor scores relative to each holding's estimated risk.",
    },
    {
        value: "minimum_variance",
        label: "Minimum Variance",
        description:
            "Builds a portfolio intended to minimize estimated volatility.",
    },
    {
        value: "maximum_sharpe",
        label: "Maximum Sharpe",
        description:
            "Balances expected excess return against estimated portfolio risk.",
    },
    {
        value: "mean_variance",
        label: "Mean Variance",
        description:
            "Combines expected return and covariance using a risk-aversion setting.",
    },
    {
        value: "risk_parity",
        label: "Risk Parity",
        description:
            "Attempts to distribute portfolio risk evenly across holdings.",
    },
    {
        value: "hierarchical_risk_parity",
        label: "Hierarchical Risk Parity",
        description:
            "Uses asset correlations and clustering to allocate portfolio risk.",
    },
];

const MINIMUM_RESEARCH_YEAR = 2010;


/* --------------------------------------------------------------------------
 * Date Helpers
 * -------------------------------------------------------------------------- */

function getCurrentResearchPeriod(): ResearchPeriod {
    const today = new Date();

    const quarter = (
        Math.floor(today.getMonth() / 3) + 1
    ) as Quarter;

    return {
        year: today.getFullYear(),
        quarter,
    };
}

function getQuarterStartMonth(
    quarter: Quarter,
): string {
    const monthByQuarter: Record<Quarter, string> = {
        1: "01",
        2: "04",
        3: "07",
        4: "10",
    };

    return monthByQuarter[quarter];
}

function buildQuarterStartDate(
    year: number,
    quarter: Quarter,
): string {
    const month = getQuarterStartMonth(quarter);

    return `${year}-${month}-01`;
}

function isFutureResearchPeriod(
    year: number,
    quarter: Quarter,
): boolean {
    const currentPeriod = getCurrentResearchPeriod();

    if (year > currentPeriod.year) {
        return true;
    }

    return (
        year === currentPeriod.year
        && quarter > currentPeriod.quarter
    );
}


/* --------------------------------------------------------------------------
 * Formatting Helpers
 * -------------------------------------------------------------------------- */

function getSelectedMethodDescription(
    method: PortfolioMethod,
): string {
    return (
        PORTFOLIO_METHOD_OPTIONS.find(
            (option) => option.value === method,
        )?.description
        ?? ""
    );
}


/* --------------------------------------------------------------------------
 * Component
 * -------------------------------------------------------------------------- */

export default function PortfolioForm({
    onReportGenerated,
}: PortfolioFormProps) {
    const currentPeriod = getCurrentResearchPeriod();

    /* ----------------------------------------------------------------------
     * Basic Research Inputs
     * ---------------------------------------------------------------------- */

    const [
        researchYear,
        setResearchYear,
    ] = useState(currentPeriod.year);

    const [
        researchQuarter,
        setResearchQuarter,
    ] = useState<Quarter>(
        currentPeriod.quarter,
    );

    const [
        portfolioMethod,
        setPortfolioMethod,
    ] = useState<PortfolioMethod>(
        "score_weighted",
    );

    /* ----------------------------------------------------------------------
     * Advanced Options
     * ---------------------------------------------------------------------- */

    const [
        includeNews,
        setIncludeNews,
    ] = useState(true);

    const [
        includeFilings,
        setIncludeFilings,
    ] = useState(true);

    const [
        refreshQuantitativeInputs,
        setRefreshQuantitativeInputs,
    ] = useState(true);

    const [
        refreshRecentData,
        setRefreshRecentData,
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
     * Derived Values
     * ---------------------------------------------------------------------- */

    const asOfDate = buildQuarterStartDate(
        researchYear,
        researchQuarter,
    );

    const selectedMethodDescription =
        getSelectedMethodDescription(
            portfolioMethod,
        );

    /* ----------------------------------------------------------------------
     * Request Builder
     * ---------------------------------------------------------------------- */

    function buildRequest(): QuarterlyResearchRequest {
        return {
            /*
             * universe_tickers is intentionally omitted.
             *
             * The backend Pydantic schema will use its default_factory
             * and retrieve the configured U.S. stock universe.
             */

            as_of_date: asOfDate,

            portfolio_method: portfolioMethod,

            period_mode: "quarterly",

            top_screen_n: 100,

            final_portfolio_n: 5,

            include_news: includeNews,

            news_days_back: 30,

            max_news_articles_per_ticker: 10,

            include_filings: includeFilings,

            filing_limit_per_ticker: 5,

            refresh_quantitative_inputs:
                refreshQuantitativeInputs,

            refresh_recent_data:
                refreshRecentData,

            use_cache: true,
        };
    }

    /* ----------------------------------------------------------------------
     * Validation
     * ---------------------------------------------------------------------- */

    function validateInputs(): string | null {
        if (
            !Number.isInteger(researchYear)
            || researchYear < MINIMUM_RESEARCH_YEAR
        ) {
            return (
                `Please enter a valid year of `
                + `${MINIMUM_RESEARCH_YEAR} or later.`
            );
        }

        if (
            researchQuarter < 1
            || researchQuarter > 4
        ) {
            return "Please select a valid research quarter.";
        }

        if (
            isFutureResearchPeriod(
                researchYear,
                researchQuarter,
            )
        ) {
            return (
                "The research quarter cannot be "
                + "later than the current quarter."
            );
        }

        return null;
    }

    /* ----------------------------------------------------------------------
     * Form Submission
     * ---------------------------------------------------------------------- */

    async function handleSubmit(
        event: FormEvent<HTMLFormElement>,
    ): Promise<void> {
        event.preventDefault();

        setError("");

        const validationError = validateInputs();

        if (validationError !== null) {
            setError(validationError);
            return;
        }

        try {
            setLoading(true);

            const request = buildRequest();

            const report =
                await generatePortfolioResearch(
                    request,
                );

            onReportGenerated(report);
        } catch (caughtError) {
            console.error(
                "Portfolio report generation failed:",
                caughtError,
            );

            if (
                caughtError instanceof Error
                && caughtError.message
            ) {
                setError(caughtError.message);
            } else {
                setError(
                    "Failed to generate the portfolio report. "
                    + "Please try again.",
                );
            }
        } finally {
            setLoading(false);
        }
    }

    /* ----------------------------------------------------------------------
     * Render
     * ---------------------------------------------------------------------- */

    return (
        <Card
            title="Generate Portfolio Report"
            subtitle="Construct a quarterly portfolio and generate an AI-powered research report."
        >
            <form
                onSubmit={handleSubmit}
                className="space-y-6"
            >
                {/* Research Year */}

                <div>
                    <label
                        htmlFor="portfolio-research-year"
                        className="
                            mb-2
                            block
                            text-sm
                            font-medium
                            text-slate-700
                        "
                    >
                        Research Year
                    </label>

                    <input
                        id="portfolio-research-year"
                        name="researchYear"
                        type="number"
                        min={MINIMUM_RESEARCH_YEAR}
                        max={currentPeriod.year}
                        step={1}
                        value={researchYear}
                        onChange={(event) => {
                            const parsedYear =
                                Number(event.target.value);

                            setResearchYear(parsedYear);
                        }}
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
                        Select the year of the quarterly
                        factor snapshot.
                    </p>
                </div>

                {/* Research Quarter */}

                <div>
                    <label
                        htmlFor="portfolio-research-quarter"
                        className="
                            mb-2
                            block
                            text-sm
                            font-medium
                            text-slate-700
                        "
                    >
                        Research Quarter
                    </label>

                    <select
                        id="portfolio-research-quarter"
                        name="researchQuarter"
                        value={researchQuarter}
                        onChange={(event) => {
                            setResearchQuarter(
                                Number(
                                    event.target.value,
                                ) as Quarter,
                            );
                        }}
                        disabled={loading}
                        className="
                            w-full
                            rounded-lg
                            border
                            border-slate-300
                            bg-white
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
                    >
                        <option value={1}>
                            Q1 — January 1
                        </option>

                        <option value={2}>
                            Q2 — April 1
                        </option>

                        <option value={3}>
                            Q3 — July 1
                        </option>

                        <option value={4}>
                            Q4 — October 1
                        </option>
                    </select>

                    <p className="mt-1 text-xs text-slate-500">
                        The selected quarter maps to an
                        as-of date of {asOfDate}.
                    </p>
                </div>

                {/* Portfolio Method */}

                <div>
                    <label
                        htmlFor="portfolio-method"
                        className="
                            mb-2
                            block
                            text-sm
                            font-medium
                            text-slate-700
                        "
                    >
                        Portfolio Method
                    </label>

                    <select
                        id="portfolio-method"
                        name="portfolioMethod"
                        value={portfolioMethod}
                        onChange={(event) => {
                            setPortfolioMethod(
                                event.target
                                    .value as PortfolioMethod,
                            );
                        }}
                        disabled={loading}
                        className="
                            w-full
                            rounded-lg
                            border
                            border-slate-300
                            bg-white
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
                    >
                        {PORTFOLIO_METHOD_OPTIONS.map(
                            (option) => (
                                <option
                                    key={option.value}
                                    value={option.value}
                                >
                                    {option.label}
                                </option>
                            ),
                        )}
                    </select>

                    {selectedMethodDescription !== "" && (
                        <p className="mt-1 text-xs text-slate-500">
                            {selectedMethodDescription}
                        </p>
                    )}
                </div>

                {/* Advanced Settings Toggle */}

                <button
                    type="button"
                    onClick={() => {
                        setShowAdvanced(
                            (currentValue) =>
                                !currentValue,
                        );
                    }}
                    disabled={loading}
                    aria-expanded={showAdvanced}
                    aria-controls="portfolio-advanced-settings"
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
                        id="portfolio-advanced-settings"
                        className="
                            space-y-5
                            rounded-lg
                            border
                            border-slate-200
                            bg-slate-50
                            p-4
                        "
                    >
                        <div>
                            <h3 className="text-sm font-semibold text-slate-900">
                                Data Refresh
                            </h3>

                            <p className="mt-1 text-xs leading-5 text-slate-500">
                                Control whether underlying
                                quantitative and recent
                                research data are refreshed
                                before generating the report.
                            </p>
                        </div>

                        <label className="flex cursor-pointer items-start gap-3">
                            <input
                                type="checkbox"
                                checked={
                                    refreshQuantitativeInputs
                                }
                                onChange={(event) => {
                                    setRefreshQuantitativeInputs(
                                        event.target.checked,
                                    );
                                }}
                                disabled={loading}
                                className="
                                    mt-0.5
                                    h-4
                                    w-4
                                    rounded
                                    border-slate-300
                                    text-emerald-700
                                    focus:ring-emerald-500
                                "
                            />

                            <span>
                                <span className="block text-sm font-medium text-slate-700">
                                    Refresh quantitative inputs
                                </span>

                                <span className="mt-1 block text-xs leading-5 text-slate-500">
                                    Refresh market and
                                    fundamental data before
                                    calculating factor snapshots,
                                    alpha signals, and portfolio
                                    weights. Disable this for
                                    historical quarters whose
                                    quantitative inputs are
                                    already stored.
                                </span>
                            </span>
                        </label>

                        <label className="flex cursor-pointer items-start gap-3">
                            <input
                                type="checkbox"
                                checked={refreshRecentData}
                                onChange={(event) => {
                                    setRefreshRecentData(
                                        event.target.checked,
                                    );
                                }}
                                disabled={loading}
                                className="
                                    mt-0.5
                                    h-4
                                    w-4
                                    rounded
                                    border-slate-300
                                    text-emerald-700
                                    focus:ring-emerald-500
                                "
                            />

                            <span>
                                <span className="block text-sm font-medium text-slate-700">
                                    Refresh recent research data
                                </span>

                                <span className="mt-1 block text-xs leading-5 text-slate-500">
                                    Refresh recent news and SEC
                                    filing data used after the
                                    portfolio holdings have been
                                    selected.
                                </span>
                            </span>
                        </label>

                        <div className="border-t border-slate-200 pt-5">
                            <h3 className="text-sm font-semibold text-slate-900">
                                Research Sources
                            </h3>

                            <p className="mt-1 text-xs leading-5 text-slate-500">
                                Choose which recent evidence
                                sources should be included in
                                the holding-level research.
                            </p>
                        </div>

                        <label className="flex cursor-pointer items-start gap-3">
                            <input
                                type="checkbox"
                                checked={includeNews}
                                onChange={(event) => {
                                    setIncludeNews(
                                        event.target.checked,
                                    );
                                }}
                                disabled={loading}
                                className="
                                    mt-0.5
                                    h-4
                                    w-4
                                    rounded
                                    border-slate-300
                                    text-emerald-700
                                    focus:ring-emerald-500
                                "
                            />

                            <span>
                                <span className="block text-sm font-medium text-slate-700">
                                    Include recent news
                                </span>

                                <span className="mt-1 block text-xs leading-5 text-slate-500">
                                    Include recent company news
                                    in holding research,
                                    catalysts, risks, and
                                    developments.
                                </span>
                            </span>
                        </label>

                        <label className="flex cursor-pointer items-start gap-3">
                            <input
                                type="checkbox"
                                checked={includeFilings}
                                onChange={(event) => {
                                    setIncludeFilings(
                                        event.target.checked,
                                    );
                                }}
                                disabled={loading}
                                className="
                                    mt-0.5
                                    h-4
                                    w-4
                                    rounded
                                    border-slate-300
                                    text-emerald-700
                                    focus:ring-emerald-500
                                "
                            />

                            <span>
                                <span className="block text-sm font-medium text-slate-700">
                                    Include SEC filings
                                </span>

                                <span className="mt-1 block text-xs leading-5 text-slate-500">
                                    Include recent filing
                                    evidence in holding-level
                                    research and risk analysis.
                                </span>
                            </span>
                        </label>
                    </div>
                )}

                {/* Error Message */}

                {error !== "" && (
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

                {/* Submit */}

                {loading ? (
                    <LoadingSpinner
                        message="Generating portfolio report..."
                        size="large"
                    />
                ) : (
                    <Button
                        type="submit"
                        size="large"
                        className="w-full"
                    >
                        Generate Portfolio Report
                    </Button>
                )}
            </form>
        </Card>
    );
}