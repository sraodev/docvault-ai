export interface Document {
    id: string
    filename: string
    upload_date: string
    status: 'processing' | 'completed' | 'failed'
    summary?: string
    markdown_path?: string
}
