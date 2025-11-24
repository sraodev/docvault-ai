import { FileText } from 'lucide-react'
import { UploadArea } from './UploadArea'
import { DocumentList } from './DocumentList'
import { Document } from '../types'

interface SidebarProps {
    documents: Document[]
    selectedDocId?: string
    onSelect: (doc: Document) => void
    onDelete: (id: string) => void
    onUpload: (files: FileList) => Promise<void>
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
    return (
        <div className="w-80 bg-white border-r border-slate-200 flex flex-col">
            <div className="p-6 border-b border-slate-100">
                <h1 className="text-xl font-bold flex items-center gap-2 text-indigo-600">
                    <FileText className="w-6 h-6" />
                    DocVault AI
                </h1>
            </div>

            <UploadArea
                onUpload={onUpload}
                isUploading={isUploading}
                error={uploadError}
            />

            <DocumentList
                documents={documents}
                selectedDocId={selectedDocId}
                onSelect={onSelect}
                onDelete={onDelete}
            />
        </div>
    )
}
