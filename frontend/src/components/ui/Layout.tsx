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
                bg-[#1c302f]
                px-6
                py-10
            "
        >
            <div
                className="
                    mx-auto
                    flex
                    max-w-7xl
                    flex-col
                    gap-10
                "
            >
                {children}
            </div>
        </main>
    );
}
