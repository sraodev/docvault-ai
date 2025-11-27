import { useState, useRef, useEffect } from 'react'
import { FileText, List, FolderKanban, FolderPlus, Upload, FolderOpen, Plus, ChevronDown } from 'lucide-react'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
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
    onUpload: (files: FileList, folder?: string | ((file: File) => string | undefined)) => Promise<void>
    isUploading: boolean
    uploadError: string | null
    uploadProgress?: Map<string, number>
}

export function Sidebar({
    documents,
    selectedDocId,
    onSelect,
    onDelete,
    onUpload,
    isUploading,
    uploadError,
    uploadProgress
}: SidebarProps) {
    const [viewMode, setViewMode] = useState<'list' | 'folders'>('list')
    const fileInputRef = useRef<HTMLInputElement>(null)
    const folderInputRef = useRef<HTMLInputElement>(null)
    const [newFolderName, setNewFolderName] = useState('')
    const [showNewFolderInput, setShowNewFolderInput] = useState(false)
    const [showNewMenu, setShowNewMenu] = useState(false)

    const handleNewFolder = () => {
        setShowNewMenu(false)
        setShowNewFolderInput(true)
    }

    const handleCreateFolder = () => {
        if (newFolderName.trim()) {
            // Create folder logic - for now just reset
            setNewFolderName('')
            setShowNewFolderInput(false)
            // TODO: Implement folder creation API call
        }
    }

    const handleFileUpload = () => {
        setShowNewMenu(false)
        fileInputRef.current?.click()
    }

    const handleFolderUpload = () => {
        setShowNewMenu(false)
        folderInputRef.current?.click()
    }

    const handleFileInput = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files?.length) {
            await onUpload(e.target.files)
        }
    }

    const handleFolderInput = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files?.length) {
            // Create a function to extract folder path from each file's webkitRelativePath
            const getFolderPath = (file: File): string | undefined => {
                // webkitRelativePath format: "folder/subfolder/filename.ext" or "filename.ext" (root)
                // When using webkitdirectory, the path includes the selected folder name
                const relativePath = (file as any).webkitRelativePath

                if (!relativePath) {
                    // Fallback: if webkitRelativePath is not available, file is in root
                    return undefined
                }

                const pathParts = relativePath.split('/')

                if (pathParts.length > 1) {
                    // Remove the filename to get the folder path
                    // This preserves the full folder structure including subfolders
                    const folderPath = pathParts.slice(0, -1).join('/')
                    // Return empty string for root files, or the folder path
                    return folderPath || undefined
                }
                // File is in root of selected folder - return undefined
                return undefined
            }

            // Upload files with folder structure preserved
            await onUpload(e.target.files, getFolderPath)
        }
        // Reset input so same folder can be selected again
        e.target.value = ''
    }

    // Close dropdown when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (showNewMenu && !(event.target as Element).closest('.new-menu-container')) {
                setShowNewMenu(false)
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [showNewMenu])

    return (
        <div className="w-64 bg-white border-r border-slate-200 flex flex-col">
            <div className="p-4 border-b border-slate-200">
                <h1 className="text-xl font-semibold flex items-center gap-3 text-slate-900">
                    <FileText className="w-7 h-7 text-blue-600" />
                    DocVault AI
                </h1>
            </div>

            {/* + New Button with Dropdown */}
            <div className="px-2 py-2 border-b border-slate-200 relative new-menu-container">
                {showNewFolderInput ? (
                    <div className="space-y-2 mb-2">
                        <input
                            type="text"
                            value={newFolderName}
                            onChange={(e) => setNewFolderName(e.target.value)}
                            onKeyPress={(e) => e.key === 'Enter' && handleCreateFolder()}
                            placeholder="Folder name"
                            className="w-full px-2 py-1.5 text-xs border border-slate-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                            autoFocus
                        />
                        <div className="flex gap-1">
                            <button
                                onClick={handleCreateFolder}
                                className="flex-1 px-2 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
                            >
                                Create
                            </button>
                            <button
                                onClick={() => {
                                    setShowNewFolderInput(false)
                                    setNewFolderName('')
                                }}
                                className="flex-1 px-2 py-1 text-xs bg-slate-200 text-slate-700 rounded hover:bg-slate-300"
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                ) : (
                    <>
                        <button
                            onClick={() => setShowNewMenu(!showNewMenu)}
                            className="w-full px-3 py-2 rounded-lg hover:bg-slate-100 text-slate-700 flex items-center justify-between transition-colors"
                        >
                            <div className="flex items-center gap-2">
                                <Plus className="w-4 h-4" />
                                <span className="text-sm font-medium">New</span>
                            </div>
                            <ChevronDown className={cn(
                                "w-4 h-4 transition-transform",
                                showNewMenu && "transform rotate-180"
                            )} />
                        </button>

                        {/* Dropdown Menu */}
                        {showNewMenu && (
                            <div className="absolute left-2 right-2 mt-1 bg-white border border-slate-200 rounded-lg shadow-lg z-50 overflow-hidden">
                                <button
                                    onClick={handleNewFolder}
                                    className="w-full text-left px-3 py-2 hover:bg-slate-100 text-slate-700 flex items-center gap-3 transition-colors"
                                >
                                    <FolderPlus className="w-4 h-4" />
                                    <span className="text-sm">New Folder</span>
                                </button>
                                <button
                                    onClick={handleFileUpload}
                                    disabled={isUploading}
                                    className="w-full text-left px-3 py-2 hover:bg-slate-100 text-slate-700 flex items-center gap-3 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    <Upload className="w-4 h-4" />
                                    <span className="text-sm">File Upload</span>
                                </button>
                                <button
                                    onClick={handleFolderUpload}
                                    disabled={isUploading}
                                    className="w-full text-left px-3 py-2 hover:bg-slate-100 text-slate-700 flex items-center gap-3 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    <FolderOpen className="w-4 h-4" />
                                    <span className="text-sm">Folder Upload</span>
                                </button>
                            </div>
                        )}
                    </>
                )}
            </div>

            {/* Navigation */}
            <div className="flex-1 overflow-y-auto py-2">
                <nav className="space-y-1 px-2">
                    <button className="w-full text-left px-3 py-2 rounded-lg hover:bg-slate-100 text-slate-700 flex items-center gap-3 transition-colors">
                        <FolderKanban className="w-5 h-5" />
                        <span className="text-sm font-medium">My Vault</span>
                    </button>
                    <button className="w-full text-left px-3 py-2 rounded-lg hover:bg-slate-100 text-slate-700 flex items-center gap-3 transition-colors">
                        <List className="w-5 h-5" />
                        <span className="text-sm font-medium">Recent</span>
                    </button>
                </nav>
            </div>

            {/* Hidden Inputs */}
            <input
                ref={fileInputRef}
                type="file"
                multiple
                onChange={handleFileInput}
                className="hidden"
                disabled={isUploading}
            />
            <input
                ref={folderInputRef}
                type="file"
                webkitdirectory=""
                directory=""
                multiple
                onChange={handleFolderInput}
                className="hidden"
                disabled={isUploading}
            />
        </div>
    )
}
