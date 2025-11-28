import { useState } from 'react'
import { Folder, FolderOpen, File, ChevronRight, ChevronDown, Trash2 } from 'lucide-react'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { Document } from '../types'
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

interface FolderExplorerViewProps {
    documents: Document[]
    selectedDocId?: string
    onSelect: (doc: Document) => void
    onDelete: (id: string) => void
}

export function FolderExplorerView({
    documents,
    selectedDocId,
    onSelect,
    onDelete
}: FolderExplorerViewProps) {
    const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set())
    const [expandedUncategorized, setExpandedUncategorized] = useState(false)

    // Group documents by folder
    const folderGroups: Record<string, Document[]> = {}
    const uncategorized: Document[] = []

    documents.forEach(doc => {
        if (doc.folder) {
            if (!folderGroups[doc.folder]) {
                folderGroups[doc.folder] = []
            }
            folderGroups[doc.folder].push(doc)
        } else {
            uncategorized.push(doc)
        }
    })

    const folders = Object.keys(folderGroups).sort()

    const toggleFolder = (folder: string) => {
        const newExpanded = new Set(expandedFolders)
        if (newExpanded.has(folder)) {
            newExpanded.delete(folder)
        } else {
            newExpanded.add(folder)
        }
        setExpandedFolders(newExpanded)
    }

    const toggleUncategorized = () => {
        setExpandedUncategorized(!expandedUncategorized)
    }

    return (
        <div className="flex-1 flex flex-col overflow-hidden">
            {/* Section Header */}
            <div className="px-3 py-2 border-b border-slate-200 bg-slate-50">
                <h3 className="text-xs font-bold text-slate-600 uppercase tracking-wider">
                    FOLDERS
                </h3>
            </div>

            {/* Tree Structure */}
            <div className="flex-1 overflow-y-auto">
                <div className="p-2">
                    {/* Folders with nested files */}
                    {folders.map((folder) => {
                        const isExpanded = expandedFolders.has(folder)
                        const folderDocs = folderGroups[folder]

                        return (
                            <div key={folder} className="mb-1">
                                {/* Folder Row */}
                                <div
                                    onClick={() => toggleFolder(folder)}
                                    className={cn(
                                        "flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer transition-colors group",
                                        "hover:bg-slate-100"
                                    )}
                                >
                                    {isExpanded ? (
                                        <ChevronDown className="w-3 h-3 shrink-0 text-slate-500" />
                                    ) : (
                                        <ChevronRight className="w-3 h-3 shrink-0 text-slate-500" />
                                    )}
                                    {isExpanded ? (
                                        <FolderOpen className="w-3.5 h-3.5 text-blue-500 shrink-0" />
                                    ) : (
                                        <Folder className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                                    )}
                                    <span className="text-xs font-medium flex-1 truncate" title={folder}>
                                        {folder}
                                    </span>
                                    <span className="text-xs text-slate-400 shrink-0">{folderDocs.length}</span>
                                </div>

                                {/* Files under folder - shown when expanded */}
                                {isExpanded && (
                                    <div className="ml-6 mt-0.5 space-y-0.5">
                                        {folderDocs.map((doc) => {
                                            const isSelected = selectedDocId === doc.id
                                            return (
                                                <div
                                                    key={doc.id}
                                                    onClick={(e) => {
                                                        e.stopPropagation()
                                                        onSelect(doc)
                                                    }}
                                                    className={cn(
                                                        "flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer transition-colors group",
                                                        isSelected
                                                            ? "bg-blue-50 text-blue-700"
                                                            : "hover:bg-slate-50"
                                                    )}
                                                >
                                                    <File className={cn(
                                                        "w-3.5 h-3.5 shrink-0",
                                                        isSelected ? "text-blue-600" : "text-slate-500"
                                                    )} />
                                                    <span 
                                                        className="text-xs flex-1 truncate" 
                                                        title={doc.filename}
                                                    >
                                                        {extractFilename(doc.filename)}
                                                    </span>
                                                    <span className="px-1 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600 uppercase shrink-0">
                                                        {getFileType(doc.filename)}
                                                    </span>
                                                    <button
                                                        onClick={(e) => {
                                                            e.stopPropagation()
                                                            if (window.confirm("Delete this document?")) {
                                                                onDelete(doc.id)
                                                            }
                                                        }}
                                                        className="p-1 rounded text-slate-400 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all shrink-0"
                                                        aria-label="Delete document"
                                                    >
                                                        <Trash2 className="w-3 h-3" />
                                                    </button>
                                                </div>
                                            )
                                        })}
                                    </div>
                                )}
                            </div>
                        )
                    })}

                    {/* Uncategorized Section */}
                    {uncategorized.length > 0 && (
                        <div className="mb-1">
                            {/* Divider */}
                            {folders.length > 0 && (
                                <div className="h-px bg-slate-200 my-2"></div>
                            )}
                            
                            {/* Uncategorized Folder Row */}
                            <div
                                onClick={toggleUncategorized}
                                className={cn(
                                    "flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer transition-colors group",
                                    "hover:bg-slate-100"
                                )}
                            >
                                {expandedUncategorized ? (
                                    <ChevronDown className="w-3 h-3 shrink-0 text-slate-500" />
                                ) : (
                                    <ChevronRight className="w-3 h-3 shrink-0 text-slate-500" />
                                )}
                                <File className="w-3.5 h-3.5 shrink-0 text-slate-500" />
                                <span className="text-xs font-medium flex-1 truncate" title="Uncategorized">
                                    Uncategorized
                                </span>
                                <span className="text-xs text-slate-400 shrink-0">{uncategorized.length}</span>
                            </div>

                            {/* Files under uncategorized - shown when expanded */}
                            {expandedUncategorized && (
                                <div className="ml-6 mt-0.5 space-y-0.5">
                                    {uncategorized.map((doc) => {
                                        const isSelected = selectedDocId === doc.id
                                        return (
                                            <div
                                                key={doc.id}
                                                onClick={(e) => {
                                                    e.stopPropagation()
                                                    onSelect(doc)
                                                }}
                                                className={cn(
                                                    "flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer transition-colors group",
                                                    isSelected
                                                        ? "bg-indigo-50 text-indigo-700"
                                                        : "hover:bg-slate-50"
                                                )}
                                            >
                                                <File className={cn(
                                                    "w-3.5 h-3.5 shrink-0",
                                                    isSelected ? "text-indigo-600" : "text-slate-500"
                                                )} />
                                                <span 
                                                    className="text-xs flex-1 truncate" 
                                                    title={doc.filename}
                                                >
                                                    {extractFilename(doc.filename)}
                                                </span>
                                                <span className="px-1 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600 uppercase shrink-0">
                                                    {getFileType(doc.filename)}
                                                </span>
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation()
                                                        if (window.confirm("Delete this document?")) {
                                                            onDelete(doc.id)
                                                        }
                                                    }}
                                                    className="p-1 rounded text-slate-400 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all shrink-0"
                                                    aria-label="Delete document"
                                                >
                                                    <Trash2 className="w-3 h-3" />
                                                </button>
                                            </div>
                                        )
                                    })}
                                </div>
                            )}
                        </div>
                    )}

                    {/* Empty State */}
                    {folders.length === 0 && uncategorized.length === 0 && (
                        <div className="px-3 py-8 text-center text-slate-400 text-xs">
                            No folders yet
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}

