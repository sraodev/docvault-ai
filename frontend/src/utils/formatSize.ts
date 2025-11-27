/**
 * Format file size in bytes to human-readable string
 * @param bytes - File size in bytes
 * @returns Formatted string (e.g., "1.5 KB", "2.3 MB", "1.2 GB")
 */
export function formatFileSize(bytes?: number): string {
    if (!bytes || bytes === 0) return '-'
    
    const units = ['B', 'KB', 'MB', 'GB', 'TB']
    let size = bytes
    let unitIndex = 0
    
    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024
        unitIndex++
    }
    
    // Format to 1 decimal place for KB, MB, GB, TB, but no decimals for bytes
    if (unitIndex === 0) {
        return `${Math.round(size)} ${units[unitIndex]}`
    }
    
    return `${size.toFixed(1)} ${units[unitIndex]}`
}

