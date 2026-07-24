import type { ReactNode } from "react";

interface LayoutProps {
    children: ReactNode;
}

export default function Layout({
    children,
}: LayoutProps) {
    return (
        <main
            className="
                min-h-screen
                bg-slate-100
                px-8
                py-8
            "
        >
            <div
                className="
                    mx-auto
                    flex
                    max-w-7xl
                    flex-col
                    gap-8
                "
            >
                {children}
            </div>
        </main>
    );
}