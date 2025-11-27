import { useState, useRef, useEffect, useMemo } from 'react'
import { FileText, FolderPlus, Upload, FolderOpen, Plus, ChevronDown, ChevronRight, Folder, File, Archive } from 'lucide-react'
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
    onCreateFolder
}: SidebarProps) {
    const fileInputRef = useRef<HTMLInputElement>(null)
    const folderInputRef = useRef<HTMLInputElement>(null)
    const [newFolderName, setNewFolderName] = useState('')
    const [showNewFolderInput, setShowNewFolderInput] = useState(false)
    const [showNewMenu, setShowNewMenu] = useState(false)
    const [expandedFolders, setExpandedFolders] = useState<Set<string>>(new Set())
    const [allFolders, setAllFolders] = useState<string[]>([])

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
            console.log("Creating folder:", trimmedName, "in parent:", currentFolder)
            // Create folder with current folder as parent (if in a folder)
            await onCreateFolder(trimmedName, currentFolder || null)
            console.log("Folder created successfully")
            setNewFolderName('')
            setShowNewFolderInput(false)
        } catch (err: any) {
            // Error is already shown via alert in the hook
            // Just keep the input open so user can retry
            console.error("Failed to create folder:", err)
            // Don't clear the input so user can see what they typed
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

        // First, build folder structure from all folders (including empty ones)
        allFolders.forEach(folderPath => {
            if (!folderPath) return
            
            const parts = folderPath.split('/').filter(p => p.trim() !== '')
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
        })

        // Then, add documents to their respective folders
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
    }, [documents, allFolders])

    const toggleFolder = (folderPath: string) => {
        const newExpanded = new Set(expandedFolders)
        if (newExpanded.has(folderPath)) {
            newExpanded.delete(folderPath)
        } else {
            newExpanded.add(folderPath)
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
            <div key={node.fullPath} className="mb-0.5">
                <div
                    className={cn(
                        "flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer transition-colors group",
                        "hover:bg-slate-100",
                        isActive && "bg-blue-50 text-blue-700"
                    )}
                    style={{ paddingLeft: `${8 + level * 16}px` }}
                    onClick={() => {
                        toggleFolder(node.fullPath)
                        handleFolderClick(node.fullPath)
                    }}
                >
                    {node.subfolders.size > 0 ? (
                        isExpanded ? (
                            <ChevronDown className="w-3 h-3 shrink-0 text-slate-500" />
                        ) : (
                            <ChevronRight className="w-3 h-3 shrink-0 text-slate-500" />
                        )
                    ) : (
                        <div className="w-3 h-3 shrink-0" />
                    )}
                    {isExpanded ? (
                        <FolderOpen className={cn("w-4 h-4 shrink-0", isActive ? "text-blue-600" : "text-indigo-500")} />
                    ) : (
                        <Folder className={cn("w-4 h-4 shrink-0", isActive ? "text-blue-600" : "text-slate-500")} />
                    )}
                    <span className={cn(
                        "text-xs font-medium flex-1 truncate",
                        isActive && "font-semibold"
                    )} title={node.name}>
                        {node.name}
                    </span>
                    {(node.files.length > 0 || node.subfolders.size > 0) && (
                        <span className="text-xs text-slate-400 shrink-0">
                            {node.files.length + Array.from(node.subfolders.values()).reduce((sum, sub) => sum + sub.files.length, 0)}
                        </span>
                    )}
                </div>

                {/* Render files and subfolders when expanded */}
                {isExpanded && (
                    <div className="mt-0.5">
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
                                        "flex items-center gap-2 px-2 py-1.5 rounded cursor-pointer transition-colors group",
                                        isSelected
                                            ? "bg-indigo-50 text-indigo-700"
                                            : "hover:bg-slate-50",
                                    )}
                                    style={{ paddingLeft: `${24 + level * 16}px` }}
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
        <div className="w-64 bg-white border-r border-slate-200 flex flex-col">
            <div className="p-4 border-b border-slate-200">
                <h1 className="text-xl font-semibold flex items-center gap-3 text-slate-900">
                    <Archive className="w-7 h-7 text-blue-600" />
                    My Vault
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
                            onKeyDown={(e) => {
                                if (e.key === 'Enter') {
                                    e.preventDefault()
                                    handleCreateFolder()
                                }
                            }}
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

            {/* Navigation - Folder Tree */}
            <div className="flex-1 overflow-y-auto py-2">
                <nav className="space-y-1 px-2">
                    {/* Root "My Vault" button */}
                    <button 
                        onClick={() => handleFolderClick(null)}
                        className={cn(
                            "w-full text-left px-3 py-2 rounded-lg hover:bg-slate-100 text-slate-700 flex items-center gap-3 transition-colors",
                            (currentFolder === null || currentFolder === undefined) && "bg-blue-50 text-blue-700 font-semibold"
                        )}
                    >
                        <Archive className={cn(
                            "w-5 h-5",
                            (currentFolder === null || currentFolder === undefined) && "text-blue-600"
                        )} />
                        <span className="text-sm font-medium">My Vault</span>
                    </button>

                    {/* Folder Tree */}
                    <div className="mt-2">
                        {folderTree.subfolders.size > 0 || folderTree.files.length > 0 ? (
                            <>
                                {Array.from(folderTree.subfolders.values())
                                    .sort((a, b) => a.name.localeCompare(b.name))
                                    .map(subfolder => renderFolderNode(subfolder, 0))}
                            </>
                        ) : (
                            <div className="px-3 py-8 text-center text-slate-400 text-xs">
                                No folders yet
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
