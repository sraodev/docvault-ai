import { File, Trash2 } from 'lucide-react'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { Document } from '../types'

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
}

export function DocumentList({ documents, selectedDocId, onSelect, onDelete }: DocumentListProps) {
    return (
        <div className="flex-1 overflow-y-auto px-2">
            <h2 className="px-4 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">Documents</h2>
            <div className="space-y-1">
                {documents.map((doc) => (
                    <button
                        key={doc.id}
                        onClick={() => onSelect(doc)}
                        className={cn(
                            "w-full text-left px-4 py-3 rounded-md flex items-center gap-3 transition-colors group",
                            selectedDocId === doc.id ? "bg-indigo-50 text-indigo-700" : "hover:bg-slate-100 text-slate-700"
                        )}
                    >
                        <div className={cn(
                            "p-2 rounded-lg",
                            selectedDocId === doc.id ? "bg-indigo-100 text-indigo-600" : "bg-slate-100 text-slate-500"
                        )}>
                            <File className="w-5 h-5" />
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">{doc.filename}</p>
                            <div className="flex items-center gap-2 mt-1 flex-wrap">
                                <span className={cn(
                                    "w-2 h-2 rounded-full shrink-0",
                                    doc.status === 'completed' ? "bg-green-500" :
                                        doc.status === 'processing' ? "bg-yellow-500" : "bg-red-500"
                                )} />
                                <span className="text-xs text-slate-400 capitalize shrink-0">{doc.status}</span>
                                <span className="px-1.5 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200 uppercase shrink-0">
                                    {getFileType(doc.filename)}
                                </span>
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
                ))}
                {documents.length === 0 && (
                    <div className="px-4 py-8 text-center text-slate-400 text-sm">
                        No documents yet.
                    </div>
                )}
            </div>
        </div>
    )
}
