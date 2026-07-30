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
                border-slate-200
                bg-white
                px-6
                py-4
                shadow-sm
            "
        >
            <div>
                <h1 className="text-xl font-bold text-slate-900">
                    Financial Intelligence Platform
                </h1>

                <p className="text-sm text-slate-500">
                    AI-Powered Investment Research
                </p>
            </div>

            <nav className="flex gap-3">
                <Button
                    variant={
                        currentPage === "home"
                            ? "primary"
                            : "secondary"
                    }
                    onClick={() => onNavigate("home")}
                >
                    Home
                </Button>

                <Button
                    variant={
                        currentPage === "chat"
                            ? "primary"
                            : "secondary"
                    }
                    onClick={() => onNavigate("chat")}
                >
                    AI Chat
                </Button>

                <Button
                    variant={
                        currentPage === "company"
                            ? "primary"
                            : "secondary"
                    }
                    onClick={() => onNavigate("company")}
                >
                    Company Research
                </Button>

                <Button
                    variant={
                        currentPage === "portfolio"
                            ? "primary"
                            : "secondary"
                    }
                    onClick={() => onNavigate("portfolio")}
                >
                    Portfolio Research
                </Button>
            </nav>
        </header>
    );
}