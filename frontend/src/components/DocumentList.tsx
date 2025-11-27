import { File, Trash2, Folder } from 'lucide-react'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { Document } from '../types'
import { ProgressBar } from './ProgressBar'
import { formatFileSize } from '../utils/formatSize'
import { extractFilename } from '../utils/filename'

function cn(...inputs: (string | undefined | null | false)[]) {
    return twMerge(clsx(inputs))
}

/**
 * Extracts file extension/type from filename
 * @param filename - The filename (e.g., "document.pdf" or "report.docx")
 * @returns The file extension in uppercase (e.g., "PDF", "DOCX")
 */
function getFileType(filename: string): string {
    if (!filename) return 'FILE'
    const parts = filename.split('.')
    if (parts.length < 2) return 'FILE'
    return parts[parts.length - 1].toUpperCase()
}

interface DocumentListProps {
    documents: Document[]
    selectedDocId?: string
    onSelect: (doc: Document) => void
    onDelete: (id: string) => void
    uploadProgress?: Map<string, number>
}

function getStatusBackgroundColor(status: string, isSelected: boolean): string {
    if (isSelected) return "bg-indigo-50 text-indigo-700"

    switch (status) {
        case 'uploading':
            return "bg-red-50 text-red-700 hover:bg-red-100"
        case 'processing':
            return "bg-orange-50 text-orange-700 hover:bg-orange-100"
        case 'completed':
            return "bg-blue-50 text-blue-700 hover:bg-blue-100"
        case 'failed':
            return "bg-red-50 text-red-700 hover:bg-red-100"
        default:
            return "hover:bg-slate-100 text-slate-700"
    }
}

export function DocumentList({ documents, selectedDocId, onSelect, onDelete, uploadProgress }: DocumentListProps) {
    return (
        <div className="flex-1 overflow-y-auto px-2">
            <h2 className="px-4 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">Documents</h2>
            <div className="space-y-1">
                {documents.map((doc) => {
                    const isSelected = selectedDocId === doc.id
                    return (
                        <button
                            key={doc.id}
                            onClick={() => onSelect(doc)}
                            className={cn(
                                "w-full text-left px-4 py-3 rounded-md flex items-center gap-3 transition-colors group",
                                getStatusBackgroundColor(doc.status, isSelected)
                            )}
                        >
                            <div className={cn(
                                "p-2 rounded-lg",
                                selectedDocId === doc.id ? "bg-indigo-100 text-indigo-600" : "bg-slate-100 text-slate-500"
                            )}>
                                <File className="w-5 h-5" />
                            </div>
                            <div className="flex-1 min-w-0">
                                <p
                                    className="text-sm font-medium break-words text-slate-900"
                                    title={doc.filename}
                                >
                                    {extractFilename(doc.filename)}
                                </p>
                                <div className="mt-2 space-y-1.5">
                                    {/* Progress Bar for uploading/processing states */}
                                    {(doc.status === 'uploading' || doc.status === 'processing') && (
                                        <ProgressBar
                                            status={doc.status}
                                            progress={doc.uploadProgress ?? uploadProgress?.get(doc.id) ?? uploadProgress?.get(doc.filename)}
                                            showLabel={true}
                                        />
                                    )}
                                    {/* Status indicators and metadata */}
                                    <div className="flex items-center gap-2 flex-wrap">
                                        {doc.status !== 'uploading' && doc.status !== 'processing' && (
                                            <>
                                                <span className={cn(
                                                    "w-2 h-2 rounded-full shrink-0",
                                                    doc.status === 'completed' ? "bg-green-500" :
                                                        doc.status === 'failed' ? "bg-red-500" : "bg-slate-400"
                                                )} />
                                                <span className="text-xs text-slate-400 capitalize shrink-0">{doc.status}</span>
                                            </>
                                        )}
                                        <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200 uppercase shrink-0">
                                            {getFileType(doc.filename)}
                                        </span>
                                        {doc.size && (
                                            <span className="text-xs text-slate-500 shrink-0">
                                                {formatFileSize(doc.size)}
                                            </span>
                                        )}
                                        {doc.folder && (
                                            <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-indigo-100 text-indigo-700 border border-indigo-200 flex items-center gap-1 shrink-0">
                                                <Folder className="w-3 h-3" />
                                                {doc.folder}
                                            </span>
                                        )}
                                    </div>
                                </div>
                            </div>
                            <div
                                onClick={(e) => { e.stopPropagation(); onDelete(doc.id); }}
                                className="p-1.5 rounded-md text-slate-400 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all"
                                title="Delete"
                            >
                                <Trash2 className="w-4 h-4" />
                            </div>
                        </button>
                    )
                })}
                {documents.length === 0 && (
                    <div className="px-4 py-8 text-center text-slate-400 text-sm">
                        No documents yet.
                    </div>
                )}
            </div>
        </div>
    )
}
