import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

function cn(...inputs: (string | undefined | null | false)[]) {
    return twMerge(clsx(inputs))
}

interface ProgressBarProps {
    status: 'uploading' | 'processing' | 'completed' | 'failed'
    progress?: number  // 0-100 for uploading, undefined for processing
    showLabel?: boolean
    size?: 'small' | 'medium' | 'large'  // Size variant: small (24px), medium (32px), large (40px)
}

export function ProgressBar({ status, progress, showLabel = true, size = 'medium' }: ProgressBarProps) {
    // Size configuration
    const sizeConfig = {
        small: {
            container: 'w-6 h-6',  // 24px
            svg: 'w-6 h-6',
            radius: 10,
            strokeWidth: 2,
            textSize: 'text-[8px]',
            checkmarkSize: 'w-3 h-3'
        },
        medium: {
            container: 'w-8 h-8',  // 32px
            svg: 'w-8 h-8',
            radius: 13,
            strokeWidth: 2.5,
            textSize: 'text-[9px]',
            checkmarkSize: 'w-4 h-4'
        },
        large: {
            container: 'w-10 h-10',  // 40px
            svg: 'w-10 h-10',
            radius: 16,
            strokeWidth: 3,
            textSize: 'text-[10px]',
            checkmarkSize: 'w-5 h-5'
        }
    }
    
    const config = sizeConfig[size]
    
    const getStatusColor = () => {
        switch (status) {
            case 'uploading':
                return 'text-red-500'
            case 'processing':
                return 'text-orange-500'
            case 'completed':
                return 'text-blue-600'  // Project theme blue
            case 'failed':
                return 'text-red-500'
            default:
                return 'text-slate-400'
        }
    }

    const getCircleColor = () => {
        switch (status) {
            case 'uploading':
                return 'text-red-500'
            case 'processing':
                return 'text-orange-500'
            case 'completed':
                return 'text-blue-600'  // Project theme blue
            case 'failed':
                return 'text-red-500'
            default:
                return 'text-slate-400'
        }
    }

    const getStatusLabel = () => {
        switch (status) {
            case 'uploading':
                return progress !== undefined ? `Uploading ${progress}%` : 'Uploading...'
            case 'processing':
                return 'Processing...'
            case 'completed':
                return 'Completed'
            case 'failed':
                return 'Failed'
            default:
                return ''
        }
    }

    // Calculate circle progress (for uploading with percentage)
    const radius = config.radius
    const circumference = 2 * Math.PI * radius
    const progressValue = status === 'uploading' && progress !== undefined ? Math.max(0, Math.min(100, progress)) : (status === 'processing' ? 0 : 100)
    // Calculate strokeDashoffset: when progress is 0%, offset should be full circumference (empty)
    // when progress is 100%, offset should be 0 (full circle)
    const strokeDashoffset = circumference - (progressValue / 100) * circumference

    return (
        <div className="flex items-center gap-2">
            {/* Circular Progress */}
            <div className={cn("relative flex items-center justify-center shrink-0", config.container)}>
                <svg
                    className={cn("transform -rotate-90", config.svg)}
                    viewBox="0 0 36 36"
                >
                    {/* Background circle */}
                    <circle
                        cx="18"
                        cy="18"
                        r={radius}
                        stroke="currentColor"
                        strokeWidth={config.strokeWidth}
                        fill="none"
                        className="text-slate-200"
                    />
                    {/* Progress circle */}
                    {status === 'processing' ? (
                        // Spinning circle for processing (orange)
                        <circle
                            cx="18"
                            cy="18"
                            r={radius}
                            stroke="currentColor"
                            strokeWidth={config.strokeWidth}
                            fill="none"
                            strokeDasharray={`${circumference * 0.3} ${circumference * 0.7}`}
                            strokeLinecap="round"
                            className={cn(
                                getCircleColor(),
                                "animate-spin"
                            )}
                            style={{
                                transformOrigin: '18px 18px',
                                animation: 'spin 1s linear infinite'
                            }}
                        />
                    ) : status === 'uploading' ? (
                        // Progress circle for uploading (red)
                        <circle
                            cx="18"
                            cy="18"
                            r={radius}
                            stroke="currentColor"
                            strokeWidth={config.strokeWidth}
                            fill="none"
                            strokeDasharray={circumference}
                            strokeDashoffset={strokeDashoffset}
                            strokeLinecap="round"
                            className={cn(
                                getCircleColor(),
                                "transition-all duration-300 ease-out"
                            )}
                        />
                    ) : status === 'completed' ? (
                        // Full circle for completed (blue)
                        <circle
                            cx="18"
                            cy="18"
                            r={radius}
                            stroke="currentColor"
                            strokeWidth={config.strokeWidth}
                            fill="none"
                            strokeDasharray={circumference}
                            strokeDashoffset="0"
                            strokeLinecap="round"
                            className={getCircleColor()}
                        />
                    ) : null}
                </svg>
                {/* Center text for percentage (only show for uploading with progress) */}
                {status === 'uploading' && progress !== undefined && (
                    <span className={cn("absolute font-semibold text-red-600 pointer-events-none", config.textSize)}>
                        {progress}%
                    </span>
                )}
                {/* Checkmark for completed */}
                {status === 'completed' && (
                    <svg className={cn("absolute text-blue-600", config.checkmarkSize)} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                )}
            </div>

            {/* Status Label - Always show */}
            <span className={cn(
                "text-xs font-medium whitespace-nowrap capitalize",
                getStatusColor()
            )}>
                {status === 'uploading' && progress !== undefined
                    ? `Uploading ${progress}%`
                    : status === 'uploading'
                        ? 'Uploading...'
                        : status === 'processing'
                            ? 'Processing...'
                            : status === 'completed'
                                ? 'Completed'
                                : status === 'failed'
                                    ? 'Failed'
                                    : getStatusLabel()}
            </span>
        </div>
    )
}
