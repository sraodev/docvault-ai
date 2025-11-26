export interface Document {
    id: string
    filename: string
    upload_date: string
    file_path: string
    status: 'processing' | 'completed' | 'failed'
    summary?: string
    markdown_path?: string
    folder?: string  // Virtual folder/category for organization
}
