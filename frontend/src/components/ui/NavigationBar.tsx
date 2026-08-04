import Button from "./Button";

interface NavigationBarProps {
    currentPage:
        | "home"
        | "chat"
        | "company"
        | "portfolio";

    onNavigate: (
        page:
            | "home"
            | "chat"
            | "company"
            | "portfolio"
    ) => void;
}

export default function NavigationBar({
    currentPage,
    onNavigate,
}: NavigationBarProps) {
    return (
        <header
            className="
                flex
                items-center
                justify-between
                rounded-xl
                border
                border-[#d5e0dc]
                bg-[#f7f9f8]
                px-6
                py-4
                shadow-sm
            "
        >
            <div>
                <h1 className="text-xl font-semibold tracking-tight text-slate-900">
                    Financial Intelligence Platform
                </h1>

                <p className="text-sm text-slate-500">
                    AI-Powered Investment Research
                </p>
            </div>

            <nav className="flex flex-wrap items-center gap-3">
                <Button
                    variant={
                        currentPage === "home"
                            ? "primary"
                            : "secondary"
                    }
                    size="large"
                    className="rounded-xl"
                    onClick={() => onNavigate("home")}
                >
                    Home
                </Button>

                <Button
                    size="large"
                    variant={
                        currentPage === "chat"
                            ? "primary"
                            : "secondary"
                    }
                    className="rounded-xl"
                    onClick={() => onNavigate("chat")}
                >
                    AI Chat
                </Button>

                <Button
                    size="large"
                    variant={
                        currentPage === "company"
                            ? "primary"
                            : "secondary"
                    }
                    className="rounded-xl"
                    onClick={() => onNavigate("company")}
                >
                    Company Research
                </Button>

                <Button
                    size="large"
                    variant={
                        currentPage === "portfolio"
                            ? "primary"
                            : "secondary"
                    }
                    className="rounded-xl"
                    onClick={() => onNavigate("portfolio")}
                >
                    Portfolio Research
                </Button>
            </nav>
        </header>
    );
}
