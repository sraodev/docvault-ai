/**
 * Extracts just the filename from a path, removing any folder structure
 * @param filePath - The file path (e.g., "OutMark/Sri/Essential.pdf" or "Essential.pdf")
 * @returns Just the filename portion (e.g., "Essential.pdf")
 */
export function extractFilename(filePath: string): string {
    if (!filePath) return ''
    // Normalize path separators: replace backslashes with forward slashes
    const normalizedPath = filePath.replace(/\\/g, '/')
    // Extract the last segment after the final separator
    return normalizedPath.split('/').pop() || filePath
}

