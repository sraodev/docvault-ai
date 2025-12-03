/**
 * Supported file formats for upload and text extraction.
 * This list should match the backend TextExtractorFactory supported formats.
 */

// Document formats (with specialized extractors)
export const DOCUMENT_FORMATS = [
  '.pdf',
  '.docx',
  '.doc',
  '.rtf',
] as const

// Text and code formats (plain text extractors)
export const TEXT_FORMATS = [
  '.txt',
  '.md',
  '.markdown',
] as const

// Code file formats
export const CODE_FORMATS = [
  '.c',
  '.cpp',
  '.h',
  '.hpp',
  '.java',
  '.js',
  '.ts',
  '.py',
  '.rb',
  '.go',
  '.rs',
  '.php',
  '.swift',
  '.kt',
  '.scala',
  '.sh',
  '.bash',
  '.zsh',
] as const

// Web formats
export const WEB_FORMATS = [
  '.html',
  '.css',
  '.json',
  '.xml',
] as const

// Config and data formats
export const CONFIG_FORMATS = [
  '.yaml',
  '.yml',
  '.ini',
  '.conf',
  '.config',
  '.sql',
  '.csv',
  '.log',
] as const

// ZIP format (for bulk uploads)
export const ZIP_FORMAT = '.zip' as const

// All supported formats
export const SUPPORTED_FORMATS = [
  ...DOCUMENT_FORMATS,
  ...TEXT_FORMATS,
  ...CODE_FORMATS,
  ...WEB_FORMATS,
  ...CONFIG_FORMATS,
  ZIP_FORMAT,
] as const

// Set for fast lookup
export const SUPPORTED_FORMATS_SET = new Set(
  SUPPORTED_FORMATS.map(ext => ext.toLowerCase())
)

/**
 * Check if a file extension is supported.
 */
export function isFileFormatSupported(filename: string): boolean {
  const ext = filename.toLowerCase().substring(filename.lastIndexOf('.'))
  return SUPPORTED_FORMATS_SET.has(ext)
}

/**
 * Get unsupported files from a file list.
 */
export function getUnsupportedFiles(files: FileList | File[]): File[] {
  const fileArray = Array.from(files)
  return fileArray.filter(file => !isFileFormatSupported(file.name))
}

/**
 * Get supported files from a file list.
 */
export function getSupportedFiles(files: FileList | File[]): File[] {
  const fileArray = Array.from(files)
  return fileArray.filter(file => isFileFormatSupported(file.name))
}

/**
 * Format the list of supported formats for display.
 */
export function getSupportedFormatsDisplay(): string {
  const categories = [
    { name: 'Documents', formats: DOCUMENT_FORMATS },
    { name: 'Text', formats: TEXT_FORMATS },
    { name: 'Code', formats: CODE_FORMATS },
    { name: 'Web', formats: WEB_FORMATS },
    { name: 'Config/Data', formats: CONFIG_FORMATS },
    { name: 'Archive', formats: [ZIP_FORMAT] },
  ]
  
  return categories
    .map(cat => `${cat.name}: ${cat.formats.join(', ')}`)
    .join(' | ')
}

