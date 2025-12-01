export interface Document {
    id: string
    filename: string
    upload_date: string
    file_path: string
    status: 'uploading' | 'ready' | 'processing' | 'completed' | 'failed'
    summary?: string
    markdown_path?: string
    folder?: string  // Virtual folder/category for organization
    checksum?: string  // SHA-256 checksum for duplicate detection
    uploadProgress?: number  // 0-100 for upload progress
    size?: number  // File size in bytes
    modified_date?: string  // Last modified date
    tags?: string[]  // Tags extracted from document content
    document_category?: string  // Document classification (Invoice, Agreement, Resume, Code, Text, etc.)
    extracted_fields?: Record<string, any>  // Structured fields extracted by AI (e.g., invoice fields, resume fields)
}
