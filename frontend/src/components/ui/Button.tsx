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
            "bg-blue-600 hover:bg-blue-700 text-white",

        secondary:
            "bg-gray-200 hover:bg-gray-300 text-gray-900",

        danger:
            "bg-red-600 hover:bg-red-700 text-white",
    };

    const sizeClasses = {
        small:
            "px-3 py-1.5 text-sm",

        medium:
            "px-4 py-2",

        large:
            "px-6 py-3 text-lg",
    };

    return (
        <button
            className={`
                rounded-lg
                font-medium
                transition-colors
                duration-200
                focus:outline-none
                focus:ring-2
                focus:ring-blue-400
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