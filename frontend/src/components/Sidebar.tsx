import { useState } from 'react'
import { FileText, List, FolderKanban } from 'lucide-react'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { UploadArea } from './UploadArea'
import { DocumentList } from './DocumentList'
import { FolderExplorerView } from './FolderExplorerView'
import { Document } from '../types'

function cn(...inputs: (string | undefined | null | false)[]) {
    return twMerge(clsx(inputs))
}

interface SidebarProps {
    documents: Document[]
    selectedDocId?: string
    onSelect: (doc: Document) => void
    onDelete: (id: string) => void
    onUpload: (files: FileList, folder?: string) => Promise<void>
    isUploading: boolean
    uploadError: string | null
}

export function Sidebar({
    documents,
    selectedDocId,
    onSelect,
    onDelete,
    onUpload,
    isUploading,
    uploadError
}: SidebarProps) {
    const [viewMode, setViewMode] = useState<'list' | 'folders'>('list')

    return (
        <div className="w-80 bg-white border-r border-slate-200 flex flex-col">
            <div className="p-6 border-b border-slate-100">
                <div className="flex items-center justify-between mb-2">
                    <h1 className="text-xl font-bold flex items-center gap-2 text-indigo-600">
                        <FileText className="w-6 h-6" />
                        DocVault AI
                    </h1>
                    <div className="flex gap-1 bg-slate-100 p-1 rounded-lg">
                        <button
                            onClick={() => setViewMode('list')}
                            className={cn(
                                "px-2 py-1 rounded text-xs flex items-center gap-1 transition-colors",
                                viewMode === 'list'
                                    ? "bg-white text-indigo-600 shadow-sm"
                                    : "text-slate-600 hover:text-slate-800"
                            )}
                            title="List View"
                        >
                            <List className="w-3 h-3" />
                        </button>
                        <button
                            onClick={() => setViewMode('folders')}
                            className={cn(
                                "px-2 py-1 rounded text-xs flex items-center gap-1 transition-colors",
                                viewMode === 'folders'
                                    ? "bg-white text-indigo-600 shadow-sm"
                                    : "text-slate-600 hover:text-slate-800"
                            )}
                            title="Folder Explorer View"
                        >
                            <FolderKanban className="w-3 h-3" />
                        </button>
                    </div>
                </div>
                {documents.length > 0 && (
                    <p className="text-xs text-slate-500">
                        {documents.length} document{documents.length !== 1 ? 's' : ''}
                    </p>
                )}
            </div>

            <UploadArea
                onUpload={onUpload}
                isUploading={isUploading}
                error={uploadError}
            />

            {viewMode === 'list' ? (
                <DocumentList
                    documents={documents}
                    selectedDocId={selectedDocId}
                    onSelect={onSelect}
                    onDelete={onDelete}
                />
            ) : (
                <FolderExplorerView
                    documents={documents}
                    selectedDocId={selectedDocId}
                    onSelect={onSelect}
                    onDelete={onDelete}
                />
            )}
        </div>
    )
}
