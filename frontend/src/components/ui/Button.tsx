import type { ButtonHTMLAttributes, ReactNode } from "react";

type ButtonVariant =
    | "primary"
    | "secondary"
    | "danger";

type ButtonSize =
    | "small"
    | "medium"
    | "large";

interface ButtonProps
    extends ButtonHTMLAttributes<HTMLButtonElement> {

    children: ReactNode;

    variant?: ButtonVariant;

    size?: ButtonSize;

    loading?: boolean;
}

export default function Button({
    children,
    variant = "primary",
    size = "medium",
    loading = false,
    disabled = false,
    className = "",
    ...props
}: ButtonProps) {

    const variantClasses = {
        primary:
            "bg-[#087f68] hover:bg-[#066b58] text-white ring-1 ring-inset ring-[#34b99a]",

        secondary:
            "bg-[#e8efed] hover:bg-[#dbe7e3] text-slate-900",

        danger:
            "bg-red-600 hover:bg-red-700 text-white",
    };

    const sizeClasses = {
        small:
            "px-3 py-2 text-sm",

        medium:
            "px-5 py-2.5 text-base",

        large:
            "px-6 py-3 text-base",
    };

    return (
        <button
            className={`
                rounded-lg
                font-medium
                transition
                duration-200
                focus:outline-none
                focus:ring-2
                focus:ring-emerald-300
                disabled:opacity-50
                disabled:cursor-not-allowed
                ${variantClasses[variant]}
                ${sizeClasses[size]}
                ${className}
            `}
            disabled={disabled || loading}
            {...props}
        >
            {loading ? "Loading..." : children}
        </button>
    );
}
