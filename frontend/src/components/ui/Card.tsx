import type {
    HTMLAttributes,
    ReactNode,
} from "react";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
    children: ReactNode;
    title?: string;
    subtitle?: string;
    padding?: "small" | "medium" | "large";
}

export default function Card({
    children,
    title,
    subtitle,
    padding = "medium",
    className = "",
    ...props
}: CardProps) {
    const paddingClasses = {
        small: "p-4",
        medium: "p-6",
        large: "p-8",
    };

    return (
        <section
            className={`
                rounded-xl
                border
                border-slate-200
                bg-white
                shadow-sm
                ${paddingClasses[padding]}
                ${className}
            `}
            {...props}
        >
            {(title || subtitle) && (
                <header className="mb-5">
                    {title && (
                        <h2 className="text-lg font-semibold text-slate-900">
                            {title}
                        </h2>
                    )}

                    {subtitle && (
                        <p className="mt-1 text-sm text-slate-500">
                            {subtitle}
                        </p>
                    )}
                </header>
            )}

            {children}
        </section>
    );
}