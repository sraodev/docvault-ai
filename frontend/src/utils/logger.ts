/**
 * Centralized Logging Utility for Frontend
 * 
 * Provides structured logging with different log levels.
 * Logs can be sent to console, localStorage, or backend API.
 */

export enum LogLevel {
    DEBUG = 0,
    INFO = 1,
    WARN = 2,
    ERROR = 3,
}

interface LogEntry {
    timestamp: string
    level: LogLevel
    message: string
    context?: string
    data?: any
    error?: {
        name: string
        message: string
        stack?: string
    }
}

class Logger {
    private logLevel: LogLevel
    private enableConsole: boolean
    private enableStorage: boolean
    private enableBackend: boolean
    private maxStorageLogs: number = 100
    private storageKey: string = 'app_logs'

    constructor() {
        // Get log level from environment or default to INFO
        const envLogLevel = (import.meta as any).env?.VITE_LOG_LEVEL?.toUpperCase() || 'INFO'
        this.logLevel = LogLevel[envLogLevel as keyof typeof LogLevel] ?? LogLevel.INFO

        // Enable console logging in development, disable in production
        this.enableConsole = (import.meta as any).env?.DEV || (import.meta as any).env?.VITE_ENABLE_CONSOLE_LOG === 'true'

        // Enable localStorage logging (optional)
        this.enableStorage = (import.meta as any).env?.VITE_ENABLE_STORAGE_LOG === 'true'

        // Enable backend logging (optional)
        this.enableBackend = (import.meta as any).env?.VITE_ENABLE_BACKEND_LOG === 'true'
    }

    private shouldLog(level: LogLevel): boolean {
        return level >= this.logLevel
    }

    private formatMessage(level: string, message: string, context?: string): string {
        const timestamp = new Date().toISOString()
        const contextStr = context ? `[${context}]` : ''
        return `${timestamp} [${level}] ${contextStr} ${message}`
    }

    private async log(level: LogLevel, levelName: string, message: string, context?: string, data?: any, error?: Error): Promise<void> {
        if (!this.shouldLog(level)) {
            return
        }

        const logEntry: LogEntry = {
            timestamp: new Date().toISOString(),
            level,
            message,
            context,
            data,
            error: error ? {
                name: error.name,
                message: error.message,
                stack: error.stack,
            } : undefined,
        }

        // Console logging
        if (this.enableConsole) {
            const formattedMessage = this.formatMessage(levelName, message, context)
            const logData = data ? [formattedMessage, data] : [formattedMessage]

            switch (level) {
                case LogLevel.DEBUG:
                    console.debug(...logData)
                    break
                case LogLevel.INFO:
                    console.info(...logData)
                    break
                case LogLevel.WARN:
                    console.warn(...logData)
                    break
                case LogLevel.ERROR:
                    console.error(...logData, error || '')
                    break
            }
        }

        // LocalStorage logging (for debugging)
        if (this.enableStorage && typeof window !== 'undefined') {
            try {
                const logs = this.getStoredLogs()
                logs.push(logEntry)

                // Keep only last N logs
                if (logs.length > this.maxStorageLogs) {
                    logs.shift()
                }

                localStorage.setItem(this.storageKey, JSON.stringify(logs))
            } catch (e) {
                // Storage might be full or disabled
                if (this.enableConsole) {
                    console.warn('Failed to store log:', e)
                }
            }
        }

        // Backend logging (optional - only for warnings and errors)
        if (this.enableBackend && level >= LogLevel.WARN) {
            try {
                // Only send warnings and errors to backend to avoid spam
                await this.sendToBackend(logEntry)
            } catch (e) {
                // Silently fail - don't break the app if logging fails
                if (this.enableConsole) {
                    console.warn('Failed to send log to backend:', e)
                }
            }
        }
    }

    private getStoredLogs(): LogEntry[] {
        if (typeof window === 'undefined') {
            return []
        }

        try {
            const stored = localStorage.getItem(this.storageKey)
            return stored ? JSON.parse(stored) : []
        } catch {
            return []
        }
    }

    private async sendToBackend(entry: LogEntry): Promise<void> {
        const API_URL = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000'

        try {
            await fetch(`${API_URL}/api/logs`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(entry),
                // Don't wait for response - fire and forget
            }).catch(() => {
                // Ignore errors - logging shouldn't break the app
            })
        } catch {
            // Ignore errors
        }
    }

    debug(message: string, context?: string, data?: any): void {
        this.log(LogLevel.DEBUG, 'DEBUG', message, context, data)
    }

    info(message: string, context?: string, data?: any): void {
        this.log(LogLevel.INFO, 'INFO', message, context, data)
    }

    warn(message: string, context?: string, data?: any): void {
        this.log(LogLevel.WARN, 'WARN', message, context, data)
    }

    error(message: string, context?: string, error?: Error, data?: any): void {
        this.log(LogLevel.ERROR, 'ERROR', message, context, data, error)
    }

    /**
     * Get stored logs from localStorage
     */
    getLogs(): LogEntry[] {
        return this.getStoredLogs()
    }

    /**
     * Clear stored logs
     */
    clearLogs(): void {
        if (typeof window !== 'undefined') {
            localStorage.removeItem(this.storageKey)
        }
    }

    /**
     * Export logs as JSON
     */
    exportLogs(): string {
        return JSON.stringify(this.getStoredLogs(), null, 2)
    }

    /**
     * Download logs as file
     */
    downloadLogs(): void {
        const logs = this.exportLogs()
        const blob = new Blob([logs], { type: 'application/json' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `app-logs-${new Date().toISOString()}.json`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
    }
}

// Export singleton instance
export const logger = new Logger()

// Export convenience functions
export const logDebug = (message: string, context?: string, data?: any) => logger.debug(message, context, data)
export const logInfo = (message: string, context?: string, data?: any) => logger.info(message, context, data)
export const logWarn = (message: string, context?: string, data?: any) => logger.warn(message, context, data)
export const logError = (message: string, context?: string, error?: Error, data?: any) => logger.error(message, context, error, data)
