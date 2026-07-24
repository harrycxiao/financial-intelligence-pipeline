interface LoadingSpinnerProps {
    message?: string;
    size?: "small" | "medium" | "large";
}

export default function LoadingSpinner({
    message = "Loading...",
    size = "medium",
}: LoadingSpinnerProps) {
    const sizeClasses = {
        small: "h-5 w-5 border-2",
        medium: "h-8 w-8 border-4",
        large: "h-12 w-12 border-4",
    };

    return (
        <div className="flex flex-col items-center justify-center gap-4 py-6">
            <div
                className={`
                    animate-spin
                    rounded-full
                    border-slate-300
                    border-t-blue-600
                    ${sizeClasses[size]}
                `}
            />

            <p className="text-sm text-slate-600">
                {message}
            </p>
        </div>
    );
}