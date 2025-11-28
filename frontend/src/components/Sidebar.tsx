import { useState, useRef, useEffect, useMemo } from 'react'
import { FileText, FolderPlus, Upload, FolderOpen, Plus, ChevronDown, ChevronRight, Folder, File, Archive, Trash2 } from 'lucide-react'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { Document } from '../types'
import { extractFilename } from '../utils/filename'
import { api } from '../services/api'

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
    currentFolder?: string | null
    onFolderChange?: (folder: string | null) => void
    onCreateFolder?: (folderName: string, parentFolder?: string | null) => Promise<void>
    onDeleteFolder?: (folderPath: string) => Promise<void>
}

export function Sidebar({
    documents,
    selectedDocId,
    onSelect,
    onDelete,
    onUpload,
    isUploading,
    uploadError,
    uploadProgress,
    currentFolder,
    onFolderChange,
    onCreateFolder,
    onDeleteFolder
}: SidebarProps) {
    const fileInputRef = useRef<HTMLInputElement>(null)
    const folderInputRef = useRef<HTMLInputElement>(null)
    const [newFolderName, setNewFolderName] = useState('')
    const [showNewFolderInput, setShowNewFolderInput] = useState(false)
    const [showNewMenu, setShowNewMenu] = useState(false)
    const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set(['root']))

    const handleNewFolder = () => {
        setShowNewMenu(false)
        setShowNewFolderInput(true)
    }

    const handleCreateFolder = async () => {
        const trimmedName = newFolderName.trim()
        if (!trimmedName) {
            alert("Please enter a folder name")
            return
        }

        if (!onCreateFolder) {
            alert("Folder creation is not available. Please refresh the page.")
            console.error("onCreateFolder prop is not provided to Sidebar")
            return
        }

        try {
            // Create folder with current folder as parent (if in a folder)
            await onCreateFolder(trimmedName, currentFolder || null)
            setNewFolderName('')
            setShowNewFolderInput(false)
        } catch (err: any) {
            // Error is already shown via alert in the hook
            // Just keep the input open so user can retry
            console.error("Failed to create folder:", err)
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

    // Calculate total files count (only files, excluding folders)
    const totalFilesCount = useMemo(() => {
        // documents array contains only file documents, not folders
        return documents.length
    }, [documents])

    // Build folder tree structure
    const folderTree = useMemo(() => {
        interface FolderNode {
            name: string
            fullPath: string
            files: Document[]
            subfolders: Map<string, FolderNode>
        }

        const root: FolderNode = {
            name: '',
            fullPath: '',
            files: [],
            subfolders: new Map()
        }

        // Build folder structure from documents
        documents.forEach(doc => {
            if (!doc.folder) {
                root.files.push(doc)
                return
            }

            const parts = doc.folder.split('/').filter(p => p.trim() !== '')
            let current = root

            parts.forEach((part, index) => {
                if (!current.subfolders.has(part)) {
                    const fullPath = parts.slice(0, index + 1).join('/')
                    current.subfolders.set(part, {
                        name: part,
                        fullPath,
                        files: [],
                        subfolders: new Map()
                    })
                }
                current = current.subfolders.get(part)!
            })

            current.files.push(doc)
        })

        return root
    }, [documents])

    const toggleFolder = (folderPath: string) => {
        const newExpanded = new Set(expandedFolders)
        if (newExpanded.has(folderPath)) {
            newExpanded.delete(folderPath)
        } else {
            newExpanded.add(folderPath)
        }
        setExpandedFolders(newExpanded)
    }

    const toggleRoot = () => {
        const newExpanded = new Set(expandedFolders)
        if (newExpanded.has('root')) {
            newExpanded.delete('root')
        } else {
            newExpanded.add('root')
        }
        setExpandedFolders(newExpanded)
    }

    const handleFolderClick = (folderPath: string | null) => {
        if (onFolderChange) {
            onFolderChange(folderPath)
        }
    }

    const renderFolderNode = (node: { name: string; fullPath: string; files: Document[]; subfolders: Map<string, any> }, level: number = 0): JSX.Element | null => {
        const isExpanded = expandedFolders.has(node.fullPath)
        const isActive = currentFolder === node.fullPath || (node.fullPath === '' && currentFolder === null)

        // Skip rendering root node if it has no content
        if (node.fullPath === '' && node.files.length === 0 && node.subfolders.size === 0) {
            return null
        }

        // Only render non-root folders
        if (node.fullPath === '') {
            // For root, render subfolders directly
            return (
                <>
                    {Array.from(node.subfolders.values())
                        .sort((a, b) => a.name.localeCompare(b.name))
                        .map(subfolder => renderFolderNode(subfolder, level))}
                </>
            )
        }

        return (
            <div key={node.fullPath} className="mb-1">
                <div
                    className={cn(
                        "flex items-center gap-2 px-3 py-2 rounded-xl cursor-pointer transition-all duration-200 group border-2",
                        isActive
                            ? "bg-white border-primary-200 shadow-soft"
                            : "border-transparent hover:bg-slate-50 hover:border-slate-200"
                    )}
                    style={{ paddingLeft: `${12 + level * 16}px` }}
                    onClick={() => {
                        toggleFolder(node.fullPath)
                        handleFolderClick(node.fullPath)
                    }}
                >
                    {node.subfolders.size > 0 ? (
                        isExpanded ? (
                            <ChevronDown className="w-3.5 h-3.5 shrink-0 text-slate-500 group-hover:text-primary-600 transition-colors" />
                        ) : (
                            <ChevronRight className="w-3.5 h-3.5 shrink-0 text-slate-500 group-hover:text-primary-600 transition-colors" />
                        )
                    ) : (
                        <div className="w-3.5 h-3.5 shrink-0" />
                    )}
                    {isExpanded ? (
                        <FolderOpen className={cn("w-4 h-4 shrink-0 transition-transform group-hover:scale-110", isActive ? "text-primary-600" : "text-blue-500")} />
                    ) : (
                        <Folder className={cn("w-4 h-4 shrink-0 transition-transform group-hover:scale-110", isActive ? "text-primary-600" : "text-slate-500")} />
                    )}
                    <span className={cn(
                        "text-sm font-medium flex-1 truncate transition-colors",
                        isActive ? "text-primary-700" : "text-slate-600 group-hover:text-slate-900",
                        isActive && "font-semibold"
                    )} title={node.name}>
                        {node.name}
                    </span>
                    {(node.files.length > 0 || node.subfolders.size > 0) && (
                        <span className={cn(
                            "text-xs shrink-0 px-1.5 py-0.5 rounded-full",
                            isActive ? "bg-primary-100 text-primary-700" : "bg-slate-100 text-slate-500"
                        )}>
                            {node.files.length + Array.from(node.subfolders.values()).reduce((sum, sub) => sum + sub.files.length, 0)}
                        </span>
                    )}
                    {onDeleteFolder && (
                        <button
                            onClick={async (e) => {
                                e.stopPropagation()
                                const count = node.files.length + Array.from(node.subfolders.values()).reduce((sum, sub) => sum + sub.files.length + (sub.subfolders.size > 0 ? 1 : 0), 0)
                                if (window.confirm(`Are you sure you want to delete this folder?\n\nThis will delete ${count} ${count === 1 ? 'item' : 'items'} including all files and subfolders.`)) {
                                    try {
                                        if (onDeleteFolder) {
                                            await onDeleteFolder(node.fullPath)
                                        } else {
                                            await api.deleteFolder(node.fullPath)
                                        }
                                    } catch (err: any) {
                                        console.error("Delete folder failed", err)
                                        const errorMsg = err.response?.data?.detail || err.message || "Failed to delete folder"
                                        alert(errorMsg)
                                    }
                                }
                            }}
                            className="p-1 rounded-md text-slate-400 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all shrink-0"
                            title="Delete folder"
                        >
                            <Trash2 className="w-3.5 h-3.5" />
                        </button>
                    )}
                </div>

                {/* Render files and subfolders when expanded */}
                {isExpanded && (
                    <div className="mt-1 space-y-0.5">
                        {/* Render files */}
                        {node.files.map((doc) => {
                            const isSelected = selectedDocId === doc.id
                            return (
                                <div
                                    key={doc.id}
                                    onClick={(e) => {
                                        e.stopPropagation()
                                        onSelect(doc)
                                    }}
                                    className={cn(
                                        "flex items-center gap-2 px-3 py-2 rounded-xl cursor-pointer transition-all duration-200 group border-2",
                                        isSelected
                                            ? "bg-white border-primary-200 shadow-soft"
                                            : "border-transparent hover:bg-slate-50 hover:border-slate-200",
                                    )}
                                    style={{ paddingLeft: `${28 + level * 16}px` }}
                                >
                                    <File className={cn(
                                        "w-4 h-4 shrink-0 transition-transform group-hover:scale-110",
                                        isSelected ? "text-primary-600" : "text-slate-500"
                                    )} />
                                    <span
                                        className="text-sm flex-1 truncate"
                                        title={doc.filename}
                                    >
                                        {extractFilename(doc.filename)}
                                    </span>
                                    <button
                                        onClick={(e) => {
                                            e.stopPropagation()
                                            if (window.confirm(`Are you sure you want to delete "${extractFilename(doc.filename)}"?`)) {
                                                onDelete(doc.id)
                                            }
                                        }}
                                        className="p-1 rounded-md text-slate-400 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all shrink-0"
                                        title="Delete file"
                                    >
                                        <Trash2 className="w-3.5 h-3.5" />
                                    </button>
                                </div>
                            )
                        })}

                        {/* Render subfolders */}
                        {Array.from(node.subfolders.values())
                            .sort((a, b) => a.name.localeCompare(b.name))
                            .map(subfolder => renderFolderNode(subfolder, level + 1))}
                    </div>
                )}
            </div>
        )
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
        <div className="w-64 bg-white/95 backdrop-blur-sm border-r border-slate-200/80 flex flex-col shadow-lg">

            <div className="h-[76px] px-6 border-b border-slate-200/80 bg-white flex items-center">
                <h1 className="text-xl font-bold flex items-center gap-3 animate-fade-in">
                    <FileText className="w-7 h-7 text-primary-600" />
                    <span className="bg-gradient-to-r from-primary-600 to-indigo-600 bg-clip-text text-transparent">DocVaultAI</span>
                </h1>
            </div>

            {/* + New Button with Dropdown */}
            <div className="px-6 py-2 relative new-menu-container bg-gradient-to-b from-white to-slate-50/50">
                {showNewFolderInput ? (
                    <div className="space-y-2 mb-2">
                        <input
                            type="text"
                            value={newFolderName}
                            onChange={(e) => setNewFolderName(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                    e.preventDefault()
                                    handleCreateFolder()
                                }
                            }}
                            placeholder="Folder name"
                            className="w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent transition-all"
                            autoFocus
                        />
                        <div className="flex gap-2">
                            <button
                                onClick={handleCreateFolder}
                                className="flex-1 px-3 py-2 text-sm bg-gradient-to-r from-primary-600 to-primary-700 text-white rounded-lg hover:from-primary-700 hover:to-primary-800 transition-all shadow-sm hover:shadow-md font-medium"
                            >
                                Create
                            </button>
                            <button
                                onClick={() => {
                                    setShowNewFolderInput(false)
                                    setNewFolderName('')
                                }}
                                className="flex-1 px-3 py-2 text-sm bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 transition-all font-medium"
                            >
                                Cancel
                            </button>
                        </div>
                    </div>
                ) : (
                    <>
                        <button
                            onClick={() => setShowNewMenu(!showNewMenu)}
                            className="w-full px-3 py-1.5 bg-white border-2 border-slate-200 text-slate-700 rounded-lg hover:border-primary-300 hover:shadow-sm active:scale-98 flex items-center justify-between transition-all duration-200 font-medium shadow-sm group"
                        >
                            <div className="flex items-center gap-2">
                                <div className="p-1 bg-primary-50 rounded-md group-hover:bg-primary-100 transition-colors">
                                    <Plus className="w-3.5 h-3.5 text-primary-600" />
                                </div>
                                <span className="text-xs group-hover:text-primary-700 transition-colors">New</span>
                            </div>
                            <ChevronDown className={cn(
                                "w-3.5 h-3.5 transition-transform duration-200",
                                showNewMenu && "transform rotate-180"
                            )} />
                        </button>

                        {/* Dropdown Menu */}
                        {showNewMenu && (
                            <div className="absolute left-6 right-6 mt-2 bg-white/95 backdrop-blur-md border border-slate-200 rounded-xl shadow-2xl z-50 overflow-hidden animate-slide-down">
                                <button
                                    onClick={handleNewFolder}
                                    className="w-full text-left px-4 py-3 hover:bg-gradient-to-r hover:from-blue-50 hover:to-indigo-50 text-slate-700 flex items-center gap-3 transition-all duration-200 group"
                                >
                                    <FolderPlus className="w-5 h-5 text-primary-600 group-hover:scale-110 transition-transform" />
                                    <span className="text-sm font-medium">New Folder</span>
                                </button>
                                <button
                                    onClick={handleFileUpload}
                                    disabled={isUploading}
                                    className="w-full text-left px-4 py-3 hover:bg-gradient-to-r hover:from-blue-50 hover:to-indigo-50 text-slate-700 flex items-center gap-3 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed group"
                                >
                                    <Upload className="w-5 h-5 text-primary-600 group-hover:scale-110 transition-transform" />
                                    <span className="text-sm font-medium">File Upload</span>
                                </button>
                                <button
                                    onClick={handleFolderUpload}
                                    disabled={isUploading}
                                    className="w-full text-left px-4 py-3 hover:bg-gradient-to-r hover:from-blue-50 hover:to-indigo-50 text-slate-700 flex items-center gap-3 transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed group"
                                >
                                    <FolderOpen className="w-5 h-5 text-primary-600 group-hover:scale-110 transition-transform" />
                                    <span className="text-sm font-medium">Folder Upload</span>
                                </button>
                            </div>
                        )}
                    </>
                )}
            </div>

            {/* Navigation - Folder Tree */}
            <div className="flex-1 overflow-y-auto py-3 bg-gradient-to-b from-transparent to-slate-50/30">
                <nav className="space-y-1 px-3">
                    {/* Root "My Vault" as Tree Root */}
                    <div className="mb-1">
                        <div
                            className={cn(
                                "flex items-center gap-2 px-3 py-2 rounded-xl cursor-pointer transition-all duration-200 group border-2",
                                (currentFolder === null || currentFolder === undefined)
                                    ? "bg-white border-primary-200 shadow-soft"
                                    : "border-transparent hover:bg-slate-50 hover:border-slate-200"
                            )}
                            onClick={() => {
                                toggleRoot()
                                handleFolderClick(null)
                            }}
                        >
                            {/* Expand/Collapse Chevron */}
                            {(folderTree.subfolders.size > 0 || folderTree.files.length > 0) ? (
                                expandedFolders.has('root') ? (
                                    <ChevronDown className="w-3.5 h-3.5 shrink-0 text-slate-500 group-hover:text-primary-600 transition-colors" />
                                ) : (
                                    <ChevronRight className="w-3.5 h-3.5 shrink-0 text-slate-500 group-hover:text-primary-600 transition-colors" />
                                )
                            ) : (
                                <div className="w-3.5 h-3.5 shrink-0" />
                            )}
                            {expandedFolders.has('root') ? (
                                <Archive className={cn("w-4 h-4 shrink-0 transition-transform group-hover:scale-110", (currentFolder === null || currentFolder === undefined) ? "text-primary-600" : "text-blue-500")} />
                            ) : (
                                <Archive className={cn("w-4 h-4 shrink-0 transition-transform group-hover:scale-110", (currentFolder === null || currentFolder === undefined) ? "text-primary-600" : "text-slate-500")} />
                            )}
                            <span className={cn(
                                "text-sm font-medium flex-1 truncate transition-colors",
                                (currentFolder === null || currentFolder === undefined) ? "text-primary-700 font-semibold" : "text-slate-600 group-hover:text-slate-900"
                            )} title="My Vault">
                                My Vault
                            </span>
                            {totalFilesCount > 0 && (
                                <span className={cn(
                                    "text-xs shrink-0 px-1.5 py-0.5 rounded-full",
                                    (currentFolder === null || currentFolder === undefined) ? "bg-primary-100 text-primary-700" : "bg-slate-100 text-slate-500"
                                )}>
                                    {totalFilesCount}
                                </span>
                            )}
                        </div>

                        {/* Tree Content - Show when expanded */}
                        {expandedFolders.has('root') && (
                            <div className="mt-1 space-y-0.5">
                                {/* Render root-level files */}
                                {folderTree.files.map((doc) => {
                                    const isSelected = selectedDocId === doc.id
                                    return (
                                        <div
                                            key={doc.id}
                                            onClick={(e) => {
                                                e.stopPropagation()
                                                onSelect(doc)
                                            }}
                                            className={cn(
                                                "flex items-center gap-2 px-3 py-2 rounded-xl cursor-pointer transition-all duration-200 group border-2",
                                                isSelected
                                                    ? "bg-white border-primary-200 shadow-soft"
                                                    : "border-transparent hover:bg-slate-50 hover:border-slate-200",
                                            )}
                                            style={{ paddingLeft: `${28}px` }}
                                        >
                                            <File className={cn(
                                                "w-4 h-4 shrink-0 transition-transform group-hover:scale-110",
                                                isSelected ? "text-primary-600" : "text-slate-500"
                                            )} />
                                            <span
                                                className="text-sm flex-1 truncate"
                                                title={doc.filename}
                                            >
                                                {extractFilename(doc.filename)}
                                            </span>
                                        </div>
                                    )
                                })}

                                {/* Render root-level folders */}
                                {Array.from(folderTree.subfolders.values())
                                    .sort((a, b) => a.name.localeCompare(b.name))
                                    .map(subfolder => renderFolderNode(subfolder, 0))}

                                {/* Show message if empty */}
                                {folderTree.subfolders.size === 0 && folderTree.files.length === 0 && (
                                    <div className="px-3 py-2 text-center text-slate-400 text-xs italic" style={{ paddingLeft: `${28}px` }}>
                                        No folders or files yet
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
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
