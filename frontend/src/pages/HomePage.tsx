/*
|--------------------------------------------------------------------------
| Home Page
|--------------------------------------------------------------------------
|
| Landing page for the Financial Intelligence Platform.
|
| This page provides a brief overview of the application's capabilities.
|
*/

export default function HomePage() {
    return (
        <main
            className="
                flex
                flex-1
                items-center
                justify-center
                px-6
                py-12
            "
        >
            <div
                className="
                    w-full
                    rounded-2xl
                    border
                    border-slate-200
                    bg-white
                    p-10
                    shadow-sm
                "
            >
                <div className="space-y-6">
                    <div>
                        <h1
                            className="
                                text-4xl
                                font-bold
                                text-slate-900
                            "
                        >
                            Financial Intelligence Platform
                        </h1>

                        <p
                            className="
                                mt-3
                                text-lg
                                text-slate-600
                            "
                        >
                            An AI-powered platform for company research,
                            portfolio analysis, and financial intelligence.
                        </p>
                    </div>

                    <div className="space-y-4 text-slate-700 leading-relaxed">
                        <p>
                            Combine deterministic financial data pipelines
                            with large language models to generate
                            evidence-based investment research.
                        </p>

                        <p>
                            Explore individual companies, analyze
                            investment portfolios, and interact with an AI
                            financial assistant through natural language.
                        </p>
                    </div>

                    <div
                        className="
                            grid
                            gap-4
                            pt-4
                            md:grid-cols-3
                        "
                    >
                        <div
                            className="
                                rounded-xl
                                border
                                border-slate-200
                                bg-slate-50
                                p-5
                            "
                        >
                            <h2
                                className="
                                    text-lg
                                    font-semibold
                                    text-slate-900
                                "
                            >
                                AI Chat
                            </h2>

                            <p className="mt-2 text-sm text-slate-600">
                                Ask questions about companies, financial
                                statements, SEC filings, market news, and
                                investment research.
                            </p>
                        </div>

                        <div
                            className="
                                rounded-xl
                                border
                                border-slate-200
                                bg-slate-50
                                p-5
                            "
                        >
                            <h2
                                className="
                                    text-lg
                                    font-semibold
                                    text-slate-900
                                "
                            >
                                Company Research
                            </h2>

                            <p className="mt-2 text-sm text-slate-600">
                                Generate comprehensive AI research reports
                                for publicly traded companies using
                                deterministic financial evidence.
                            </p>
                        </div>

                        <div
                            className="
                                rounded-xl
                                border
                                border-slate-200
                                bg-slate-50
                                p-5
                            "
                        >
                            <h2
                                className="
                                    text-lg
                                    font-semibold
                                    text-slate-900
                                "
                            >
                                Portfolio Research
                            </h2>

                            <p className="mt-2 text-sm text-slate-600">
                                Analyze diversified portfolios with
                                quantitative models, company research,
                                financial metrics, news, and SEC filings.
                            </p>
                        </div>
                    </div>

                    <div
                        className="
                            pt-4
                            text-sm
                            text-slate-500
                        "
                    >
                        Version 1 focuses on AI-assisted investment
                        research built on deterministic financial data
                        pipelines.
                    </div>
                </div>
            </div>
        </main>
    );
}