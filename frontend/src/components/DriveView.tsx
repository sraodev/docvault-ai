import { useState, useMemo, useEffect } from 'react'
import { Grid, List, Search, MoreVertical, Download, Share2, Trash2, FileText, Folder, Image, File, Upload, ChevronRight, Home, Move, X } from 'lucide-react'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { Document } from '../types'
import { ProgressBar } from './ProgressBar'
import { formatFileSize } from '../utils/formatSize'
import { extractFilename } from '../utils/filename'
import { api } from '../services/api'

function cn(...inputs: (string | undefined | null | false)[]) {
    return twMerge(clsx(inputs))
}

function getFileIcon(filename: string) {
    const ext = filename.split('.').pop()?.toLowerCase()
    switch (ext) {
        case 'pdf':
            return <FileText className="w-10 h-10 text-blue-500" />
        case 'doc':
        case 'docx':
            return <FileText className="w-10 h-10 text-blue-500" />
        case 'jpg':
        case 'jpeg':
        case 'png':
        case 'gif':
            return <Image className="w-10 h-10 text-green-500" />
        default:
            return <File className="w-10 h-10 text-slate-500" />
    }
}

function getFileTypeColor(filename: string): string {
    const ext = filename.split('.').pop()?.toLowerCase()
    switch (ext) {
        case 'pdf':
            return 'bg-blue-50 border-blue-200'
        case 'doc':
        case 'docx':
            return 'bg-blue-50 border-blue-200'
        case 'jpg':
        case 'jpeg':
        case 'png':
        case 'gif':
            return 'bg-green-50 border-green-200'
        default:
            return 'bg-slate-50 border-slate-200'
    }
}

function getStatusColor(status: string): string {
    switch (status) {
        case 'uploading':
            return 'bg-red-50 border-red-200'
        case 'processing':
            return 'bg-orange-50 border-orange-200'
        case 'completed':
            return 'bg-blue-50 border-blue-200'
        case 'failed':
            return 'bg-red-50 border-red-200'
        default:
            return ''
    }
}

/**
 * Determines the overall status of a folder based on the status of files within it.
 * Status priority: uploading > processing > failed > completed
 * 
 * @param folderPath - The folder path to check (e.g., "folder1/subfolder")
 * @param documents - Array of all documents to search through
 * @returns Status string: 'uploading', 'processing', 'failed', or 'completed'
 */
function getFolderStatus(folderPath: string, documents: Document[]): string {
    // Get all documents in this folder and subfolders (recursive)
    const folderDocs = documents.filter(doc => 
        doc.folder === folderPath || 
        (doc.folder && doc.folder.startsWith(`${folderPath}/`))
    )
    
    if (folderDocs.length === 0) {
        return 'completed' // Empty folder is considered completed
    }
    
    // Check if any file is uploading (highest priority)
    if (folderDocs.some(doc => doc.status === 'uploading')) {
        return 'uploading'
    }
    
    // Check if any file is processing
    if (folderDocs.some(doc => doc.status === 'processing')) {
        return 'processing'
    }
    
    // Check if any file failed
    if (folderDocs.some(doc => doc.status === 'failed')) {
        return 'failed'
    }
    
    // All files are completed
    return 'completed'
}

/**
 * Calculates the progress and status for a folder based on files within it.
 * Used to display progress indicators on folder cards.
 * 
 * @param folderPath - The folder path to check
 * @param documents - Array of all documents
 * @param uploadProgress - Optional map of document IDs to upload progress percentages
 * @returns Object with status and optional progress percentage (0-100)
 */
function getFolderProgress(
    folderPath: string, 
    documents: Document[], 
    uploadProgress?: Map<string, number>
): { status: string; progress?: number } {
    // Get all documents in this folder and subfolders (recursive)
    const folderDocs = documents.filter(doc => 
        doc.folder === folderPath || 
        (doc.folder && doc.folder.startsWith(`${folderPath}/`))
    )
    
    if (folderDocs.length === 0) {
        return { status: 'completed', progress: 100 }
    }
    
    // Check if any file is uploading - calculate average progress
    const uploadingDocs = folderDocs.filter(doc => doc.status === 'uploading')
    if (uploadingDocs.length > 0) {
        // Calculate average progress for uploading files
        // This gives a combined progress indicator for the folder
        const totalProgress = uploadingDocs.reduce((sum, doc) => {
            // Get progress from document's uploadProgress or from the progress map
            const progress = doc.uploadProgress ?? uploadProgress?.get(doc.id) ?? 0
            return sum + progress
        }, 0)
        const avgProgress = Math.round(totalProgress / uploadingDocs.length)
        return { status: 'uploading', progress: avgProgress }
    }
    
    // Check if any file is processing (no progress percentage, just status)
    if (folderDocs.some(doc => doc.status === 'processing')) {
        return { status: 'processing' }
    }
    
    // Check if any file failed
    if (folderDocs.some(doc => doc.status === 'failed')) {
        return { status: 'failed' }
    }
    
    // All files are completed
    return { status: 'completed', progress: 100 }
}

interface DriveViewProps {
    documents: Document[]
    selectedDocId?: string
    onSelect: (doc: Document) => void
    onDelete: (id: string) => void
    onUpload?: (files: FileList, folder?: string | ((file: File) => string | undefined)) => Promise<void>
    uploadProgress?: Map<string, number>
    currentFolder?: string | null
    onFolderChange?: (folder: string | null) => void
    onDeleteFolder?: (folderPath: string) => Promise<void>
    onMoveFolder?: (folderPath: string, newFolderPath: string | null) => Promise<void>
}

export function DriveView({ documents, selectedDocId, onSelect, onDelete, onUpload, uploadProgress, currentFolder: propCurrentFolder, onFolderChange, onDeleteFolder, onMoveFolder }: DriveViewProps) {
    const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
    const [searchQuery, setSearchQuery] = useState('')
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
    const [hoveredId, setHoveredId] = useState<string | null>(null)
    const [isDragging, setIsDragging] = useState(false)
    const [internalCurrentFolder, setInternalCurrentFolder] = useState<string | null>(null)
    const [folderActionMenu, setFolderActionMenu] = useState<string | null>(null)
    const [showMoveDialog, setShowMoveDialog] = useState(false)
    const [moveFolderPath, setMoveFolderPath] = useState<string | null>(null)
    const [newFolderPath, setNewFolderPath] = useState<string>('')
    
    // Use prop if provided, otherwise use internal state
    const currentFolder = propCurrentFolder !== undefined ? propCurrentFolder : internalCurrentFolder
    const setCurrentFolder = (folder: string | null) => {
        if (onFolderChange) {
            onFolderChange(folder)
        } else {
            setInternalCurrentFolder(folder)
        }
    }

    // Extract unique folders from documents
    const folders = useMemo(() => {
        const folderSet = new Set<string>()
        documents.forEach(doc => {
            if (doc.folder) {
                // Handle nested folders (e.g., "folder/subfolder/subsubfolder")
                const parts = doc.folder.split('/').filter(p => p.trim() !== '')
                // Add each level of the folder path
                let path = ''
                parts.forEach((part, index) => {
                    path = index === 0 ? part : `${path}/${part}`
                    folderSet.add(path)
                })
            }
        })
        return Array.from(folderSet).sort()
    }, [documents])

    // Filter documents by current folder and search query
    const filteredDocs = useMemo(() => {
        let filtered = documents
        
        // Filter by current folder
        if (currentFolder) {
            filtered = filtered.filter(doc => doc.folder === currentFolder)
        } else {
            // Show only root documents (no folder) when at root
            filtered = filtered.filter(doc => !doc.folder)
        }
        
        // Filter by search query (search in extracted filename)
        if (searchQuery) {
            filtered = filtered.filter(doc =>
                extractFilename(doc.filename).toLowerCase().includes(searchQuery.toLowerCase())
            )
        }
        
        return filtered
    }, [documents, currentFolder, searchQuery])

    // Get subfolders for current folder
    const subfolders = useMemo(() => {
        if (!currentFolder) {
            // At root, show top-level folders (folders without '/')
            return folders.filter(folder => !folder.includes('/'))
        }
        // Show immediate subfolders of current folder
        // e.g., if currentFolder is "folder1/subfolder1", show "folder1/subfolder1/subfolder2"
        const prefix = `${currentFolder}/`
        const immediateSubfolders = new Set<string>()
        
        folders.forEach(folder => {
            if (folder.startsWith(prefix)) {
                // Get the part after the prefix
                const remaining = folder.substring(prefix.length)
                // Extract only the immediate subfolder name (before next '/')
                const immediateSubfolder = remaining.split('/')[0]
                if (immediateSubfolder) {
                    immediateSubfolders.add(`${currentFolder}/${immediateSubfolder}`)
                }
            }
        })
        
        return Array.from(immediateSubfolders).sort()
    }, [folders, currentFolder])

    const toggleSelection = (id: string) => {
        setSelectedIds(prev => {
            const next = new Set(prev)
            if (next.has(id)) {
                next.delete(id)
            } else {
                next.add(id)
            }
            return next
        })
    }

    const selectAll = () => {
        if (selectedIds.size === filteredDocs.length) {
            setSelectedIds(new Set())
        } else {
            setSelectedIds(new Set(filteredDocs.map(d => d.id)))
        }
    }

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        // Allow both files and directories to be dropped
        if (e.dataTransfer.types.includes('Files') || 
            Array.from(e.dataTransfer.items).some(item => {
                const entry = item.webkitGetAsEntry()
                return entry && (entry.isFile || entry.isDirectory)
            })) {
            setIsDragging(true)
            // Set dropEffect to indicate we can accept the drop
            e.dataTransfer.dropEffect = 'copy'
        }
    }

    const handleDragLeave = (e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        // Check if we're actually leaving the container (not just moving to a child)
        const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
        const x = e.clientX
        const y = e.clientY
        
        // Only set dragging to false if we're outside the container bounds
        if (x < rect.left || x > rect.right || y < rect.top || y > rect.bottom) {
            setIsDragging(false)
        }
    }

    /**
     * Handles file and folder drag-and-drop events.
     * Supports both individual files and entire folder structures.
     * Uses File System Access API to preserve folder hierarchy.
     */
    const handleDrop = async (e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        setIsDragging(false)

        if (!onUpload) return

        // Check if we have directory entries (folder drag & drop from file system)
        // This uses the File System Access API to detect folder structures
        const items = Array.from(e.dataTransfer.items)
        const hasDirectories = items.some(item => {
            const entry = item.webkitGetAsEntry()
            return entry && entry.isDirectory
        })

        if (hasDirectories) {
            // Handle folder drag & drop using File System Access API
            // This preserves the full folder structure including nested folders
            const allFiles: File[] = []
            const filePaths: Map<File, string> = new Map() // Maps each file to its folder path

            /**
             * Recursively processes directory entries to extract all files with their paths.
             * Handles nested folder structures by maintaining basePath throughout recursion.
             */
            const processEntry = async (entry: any, basePath: string = '') => {
                if (entry.isFile) {
                    // Extract file and store with its folder path
                    const file = await new Promise<File>((resolve, reject) => {
                        entry.file((file: File) => resolve(file), reject)
                    })
                    allFiles.push(file)
                    if (basePath) {
                        filePaths.set(file, basePath)
                    }
                } else if (entry.isDirectory) {
                    // Recursively process directory contents
                    const reader = entry.createReader()
                    const entries = await new Promise<any[]>((resolve, reject) => {
                        reader.readEntries(resolve, reject)
                    })
                    
                    const folderName = entry.name
                    // Build nested folder path (e.g., "folder1/subfolder")
                    const newBasePath = basePath ? `${basePath}/${folderName}` : folderName
                    
                    // Process all entries in the directory (files and subdirectories)
                    for (const subEntry of entries) {
                        await processEntry(subEntry, newBasePath)
                    }
                }
            }

            // Process all dropped items (could be files or folders)
            for (const item of items) {
                const entry = item.webkitGetAsEntry()
                if (entry) {
                    await processEntry(entry)
                }
            }

            if (allFiles.length > 0) {
                // Create FileList from collected files
                // DataTransfer API allows us to create a FileList programmatically
                const dataTransfer = new DataTransfer()
                allFiles.forEach(file => dataTransfer.items.add(file))
                
                /**
                 * Creates a function that returns the folder path for each file.
                 * Preserves folder structure and prepends current folder if navigating within one.
                 */
                const getFolderPath = (file: File): string | undefined => {
                    const folderPath = filePaths.get(file)
                    if (folderPath) {
                        // If we're currently viewing a folder, prepend it to maintain structure
                        return currentFolder ? `${currentFolder}/${folderPath}` : folderPath
                    }
                    return currentFolder || undefined
                }
                
                await onUpload(dataTransfer.files, getFolderPath)
            }
        } else if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            // Regular file upload or files with webkitRelativePath (from webkitdirectory input)
            // This handles files dropped from folder input elements (not direct folder drag)
            const files = Array.from(e.dataTransfer.files)
            
            // Check if any file has webkitRelativePath (indicates folder drag & drop from input element)
            // webkitRelativePath is set when using <input type="file" webkitdirectory>
            const hasFolderStructure = files.some(file => (file as any).webkitRelativePath)
            
            if (hasFolderStructure) {
                /**
                 * Extract folder path from each file's webkitRelativePath.
                 * webkitRelativePath format: "folder/subfolder/filename.ext"
                 */
                const getFolderPath = (file: File): string | undefined => {
                    const relativePath = (file as any).webkitRelativePath
                    
                    if (!relativePath) {
                        return currentFolder || undefined
                    }
                    
                    const pathParts = relativePath.split('/')
                    
                    if (pathParts.length > 1) {
                        // Remove filename to get folder path
                        let folderPath = pathParts.slice(0, -1).join('/')
                        // Prepend current folder if navigating within one
                        if (currentFolder) {
                            folderPath = `${currentFolder}/${folderPath}`
                        }
                        return folderPath || undefined
                    }
                    return currentFolder || undefined
                }
                
                await onUpload(e.dataTransfer.files, getFolderPath)
            } else {
                // Regular file upload (no folder structure) - upload to current folder if in one
                if (currentFolder) {
                    await onUpload(e.dataTransfer.files, currentFolder)
                } else {
                    await onUpload(e.dataTransfer.files)
                }
            }
        }
    }

    // Get breadcrumb path
    const breadcrumbPath = currentFolder ? currentFolder.split('/') : []

    // Get available folders for move dialog
    const availableFolders = useMemo(() => {
        const folderSet = new Set<string>()
        documents.forEach(doc => {
            if (doc.folder) {
                const parts = doc.folder.split('/').filter(p => p.trim() !== '')
                for (let i = 0; i < parts.length; i++) {
                    folderSet.add(parts.slice(0, i + 1).join('/'))
                }
            }
        })
        return Array.from(folderSet).sort()
    }, [documents])

    const handleDeleteFolderClick = async (folderPath: string) => {
        const folderDocs = documents.filter(doc => 
            doc.folder === folderPath || 
            (doc.folder && doc.folder.startsWith(`${folderPath}/`))
        )
        const count = folderDocs.length
        
        if (!window.confirm(`Are you sure you want to delete this folder?\n\nThis will delete ${count} ${count === 1 ? 'item' : 'items'} including all files and subfolders.`)) {
            setFolderActionMenu(null)
            return
        }

        try {
            if (onDeleteFolder) {
                await onDeleteFolder(folderPath)
            } else {
                await api.deleteFolder(folderPath)
            }
            
            // Navigate away if we're currently viewing this folder or a subfolder
            if (currentFolder && (currentFolder === folderPath || currentFolder.startsWith(`${folderPath}/`))) {
                // Navigate to parent folder or root
                const parentPath = folderPath.split('/').slice(0, -1).join('/')
                setCurrentFolder(parentPath || null)
            }
            
            setFolderActionMenu(null)
        } catch (err: any) {
            console.error("Delete folder failed", err)
            const errorMsg = err.response?.data?.detail || err.message || "Failed to delete folder"
            alert(errorMsg)
            setFolderActionMenu(null)
        }
    }

    const handleMoveFolderClick = (folderPath: string) => {
        setMoveFolderPath(folderPath)
        setNewFolderPath('')
        setShowMoveDialog(true)
        setFolderActionMenu(null)
    }

    const handleMoveFolderConfirm = async () => {
        if (!moveFolderPath) return
        
        const targetPath = newFolderPath.trim() || null
        
        // Don't allow moving to itself or a subfolder
        if (targetPath && (targetPath === moveFolderPath || targetPath.startsWith(`${moveFolderPath}/`))) {
            alert("Cannot move folder into itself or a subfolder")
            return
        }

        try {
            if (onMoveFolder) {
                await onMoveFolder(moveFolderPath, targetPath)
            } else {
                await api.moveFolder(moveFolderPath, targetPath)
            }
            setShowMoveDialog(false)
            setMoveFolderPath(null)
            setNewFolderPath('')
        } catch (err) {
            console.error("Move folder failed", err)
            // Error already shown in handler
        }
    }

    // Close menu when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (folderActionMenu && !(event.target as Element).closest('.folder-action-menu')) {
                setFolderActionMenu(null)
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [folderActionMenu])

    return (
        <div 
            className="flex-1 flex flex-col bg-white relative"
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
        >
            {/* Search Bar and View Toggle */}
            <div className="border-b border-slate-200 px-6 py-3 bg-white flex items-center gap-4">
                <div className="relative flex-1 max-w-md">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-slate-400" />
                    <input
                        type="text"
                        placeholder="Search in DocVault"
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-10 pr-4 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    />
                </div>

                {/* View Toggle */}
                <div className="flex items-center gap-1 border border-slate-300 rounded-lg p-1">
                    <button
                        onClick={() => setViewMode('grid')}
                        className={cn(
                            "p-1.5 rounded transition-colors",
                            viewMode === 'grid' ? "bg-blue-50 text-blue-600" : "text-slate-600 hover:bg-slate-100"
                        )}
                        title="Grid view"
                    >
                        <Grid className="w-4 h-4" />
                    </button>
                    <button
                        onClick={() => setViewMode('list')}
                        className={cn(
                            "p-1.5 rounded transition-colors",
                            viewMode === 'list' ? "bg-blue-50 text-blue-600" : "text-slate-600 hover:bg-slate-100"
                        )}
                        title="List view"
                    >
                        <List className="w-4 h-4" />
                    </button>
                </div>
            </div>

            {/* Breadcrumb Navigation */}
            {breadcrumbPath.length > 0 && (
                <div className="border-b border-slate-200 px-6 py-2 bg-slate-50">
                    <nav className="flex items-center gap-1 text-sm">
                        <button
                            onClick={() => setCurrentFolder(null)}
                            className="flex items-center gap-1 text-slate-600 hover:text-slate-900 transition-colors"
                        >
                            <Home className="w-4 h-4" />
                            <span>My Vault</span>
                        </button>
                        {breadcrumbPath.map((folder, index) => {
                            const path = breadcrumbPath.slice(0, index + 1).join('/')
                            return (
                                <div key={path} className="flex items-center gap-1">
                                    <ChevronRight className="w-4 h-4 text-slate-400" />
                                    <button
                                        onClick={() => setCurrentFolder(path)}
                                        className="text-slate-600 hover:text-slate-900 transition-colors"
                                    >
                                        {folder}
                                    </button>
                                </div>
                            )
                        })}
                    </nav>
                </div>
            )}

            {/* Toolbar - Actions */}
            {selectedIds.size > 0 && (
                <div className="border-b border-slate-200 px-6 py-3 flex items-center justify-end">
                    <div className="flex items-center gap-2">
                        <span className="text-sm text-slate-600">{selectedIds.size} selected</span>
                        <button className="p-2 hover:bg-slate-100 rounded-full">
                            <Download className="w-4 h-4 text-slate-600" />
                        </button>
                        <button className="p-2 hover:bg-slate-100 rounded-full">
                            <Share2 className="w-4 h-4 text-slate-600" />
                        </button>
                        <button 
                            onClick={() => {
                                selectedIds.forEach(id => onDelete(id))
                                setSelectedIds(new Set())
                            }}
                            className="p-2 hover:bg-red-50 rounded-full"
                        >
                            <Trash2 className="w-4 h-4 text-red-600" />
                        </button>
                    </div>
                </div>
            )}

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
                {viewMode === 'grid' ? (
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
                        {/* Display Folders First */}
                        {subfolders.map((folderPath) => {
                            const folderName = folderPath.split('/').pop() || folderPath
                            // Count documents directly in this folder AND in all subfolders
                            const folderDocCount = documents.filter(doc => 
                                doc.folder === folderPath || 
                                (doc.folder && doc.folder.startsWith(`${folderPath}/`))
                            ).length
                            
                            const folderStatus = getFolderStatus(folderPath, documents)
                            const folderProgress = getFolderProgress(folderPath, documents, uploadProgress)
                            const statusColor = getStatusColor(folderStatus)
                            const folderIconColor = folderStatus === 'uploading' ? 'text-red-600' :
                                                   folderStatus === 'processing' ? 'text-orange-600' :
                                                   folderStatus === 'completed' ? 'text-blue-600' :
                                                   'text-slate-600'
                            const isUploading = folderStatus === 'uploading' || folderStatus === 'processing'
                            
                            const isMenuOpen = folderActionMenu === folderPath
                            
                            return (
                                <div
                                    key={folderPath}
                                    onMouseEnter={() => setHoveredId(`folder-${folderPath}`)}
                                    onMouseLeave={() => setHoveredId(null)}
                                    className={cn(
                                        "relative group cursor-pointer rounded-lg border-2 hover:border-slate-300 hover:shadow-md transition-all overflow-hidden",
                                        statusColor || "bg-slate-50 border-slate-200"
                                    )}
                                >
                                    {/* Folder Icon - Clickable to navigate */}
                                    <div 
                                        onClick={() => setCurrentFolder(folderPath)}
                                        className="p-6 flex flex-col items-center justify-center min-h-[120px] w-full"
                                    >
                                        <Folder className={cn("w-12 h-12", folderIconColor)} />
                                        <p className="mt-3 text-xs font-medium text-slate-700 text-center line-clamp-2 px-2 break-words w-full min-w-0 max-w-full">
                                            {folderName}
                                        </p>
                                        <p className="mt-1 text-xs text-slate-500">
                                            {folderDocCount} {folderDocCount === 1 ? 'item' : 'items'}
                                        </p>
                                    </div>

                                    {/* Progress Bar */}
                                    {isUploading && (
                                        <div className="px-3 pb-3">
                                            <ProgressBar
                                                status={folderProgress.status as 'uploading' | 'processing' | 'completed' | 'failed'}
                                                progress={folderProgress.progress}
                                                showLabel={false}
                                            />
                                        </div>
                                    )}

                                    {/* Action Menu Button */}
                                    <div className="absolute top-2 right-2 z-10 folder-action-menu">
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation()
                                                setFolderActionMenu(isMenuOpen ? null : folderPath)
                                            }}
                                            className="p-1.5 bg-white rounded-full shadow-md hover:bg-slate-100 opacity-0 group-hover:opacity-100 transition-opacity"
                                            title="Folder actions"
                                        >
                                            <MoreVertical className="w-4 h-4 text-slate-600" />
                                        </button>

                                        {/* Action Menu Dropdown */}
                                        {isMenuOpen && (
                                            <div className="absolute right-0 mt-1 w-48 bg-white border border-slate-200 rounded-lg shadow-lg z-50">
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation()
                                                        handleMoveFolderClick(folderPath)
                                                    }}
                                                    className="w-full text-left px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 flex items-center gap-2"
                                                >
                                                    <Move className="w-4 h-4" />
                                                    Move Folder
                                                </button>
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation()
                                                        handleDeleteFolderClick(folderPath)
                                                    }}
                                                    className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                    Delete Folder
                                                </button>
                    </div>
                )}
            </div>

            {/* Move Folder Dialog */}
            {showMoveDialog && moveFolderPath && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                    <div className="bg-white rounded-lg shadow-xl p-6 w-full max-w-md">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold text-slate-900">Move Folder</h3>
                            <button
                                onClick={() => {
                                    setShowMoveDialog(false)
                                    setMoveFolderPath(null)
                                    setNewFolderPath('')
                                }}
                                className="p-1 hover:bg-slate-100 rounded-full"
                            >
                                <X className="w-5 h-5 text-slate-500" />
                            </button>
                        </div>
                        
                        <div className="mb-4">
                            <p className="text-sm text-slate-600 mb-2">
                                Moving: <span className="font-medium text-slate-900">{moveFolderPath.split('/').pop()}</span>
                            </p>
                            <label className="block text-sm font-medium text-slate-700 mb-2">
                                Destination Folder (leave empty for root):
                            </label>
                            <input
                                type="text"
                                value={newFolderPath}
                                onChange={(e) => setNewFolderPath(e.target.value)}
                                placeholder="e.g., Documents/Projects"
                                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                                autoFocus
                            />
                            {availableFolders.length > 0 && (
                                <div className="mt-2">
                                    <p className="text-xs text-slate-500 mb-1">Available folders:</p>
                                    <div className="max-h-32 overflow-y-auto border border-slate-200 rounded p-2">
                                        <button
                                            onClick={() => setNewFolderPath('')}
                                            className="w-full text-left px-2 py-1 text-xs text-slate-600 hover:bg-slate-100 rounded"
                                        >
                                            (Root)
                                        </button>
                                        {availableFolders
                                            .filter(f => f !== moveFolderPath && !f.startsWith(`${moveFolderPath}/`))
                                            .map(folder => (
                                                <button
                                                    key={folder}
                                                    onClick={() => setNewFolderPath(folder)}
                                                    className="w-full text-left px-2 py-1 text-xs text-slate-600 hover:bg-slate-100 rounded"
                                                >
                                                    {folder}
                                                </button>
                                            ))}
                                    </div>
                                </div>
                            )}
                        </div>

                        <div className="flex justify-end gap-2">
                            <button
                                onClick={() => {
                                    setShowMoveDialog(false)
                                    setMoveFolderPath(null)
                                    setNewFolderPath('')
                                }}
                                className="px-4 py-2 text-sm text-slate-700 bg-slate-100 rounded-lg hover:bg-slate-200 transition-colors"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleMoveFolderConfirm}
                                className="px-4 py-2 text-sm text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                            >
                                Move
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
})}
                        
                        {/* Display Documents */}
                        {filteredDocs.map((doc) => {
                            const isSelected = selectedIds.has(doc.id)
                            const isHovered = hoveredId === doc.id
                            const isUploading = doc.status === 'uploading' || doc.status === 'processing'
                            const statusColor = getStatusColor(doc.status)
                            const fileTypeColor = doc.status === 'completed' ? getFileTypeColor(doc.filename) : ''

                            return (
                                <div
                                    key={doc.id}
                                    onMouseEnter={() => setHoveredId(doc.id)}
                                    onMouseLeave={() => setHoveredId(null)}
                                    onClick={() => !isSelected && onSelect(doc)}
                                    className={cn(
                                        "relative group cursor-pointer rounded-lg border-2 transition-all",
                                        isSelected ? "border-blue-500 bg-blue-50" : "border-slate-200 hover:border-slate-300 hover:shadow-md",
                                        statusColor || fileTypeColor
                                    )}
                                >
                                    {/* Checkbox */}
                                    <div className="absolute top-2 left-2 z-10">
                                        <input
                                            type="checkbox"
                                            checked={isSelected}
                                            onChange={(e) => {
                                                e.stopPropagation()
                                                toggleSelection(doc.id)
                                            }}
                                            onClick={(e) => e.stopPropagation()}
                                            className="w-4 h-4 text-blue-600 border-slate-300 rounded focus:ring-blue-500"
                                        />
                                    </div>

                                    {/* File Icon */}
                                    <div className="p-6 flex flex-col items-center justify-center min-h-[120px] w-full">
                                        {getFileIcon(doc.filename)}
                                        <p className="mt-3 text-xs font-medium text-slate-700 text-center line-clamp-2 px-2 break-words w-full min-w-0 max-w-full">
                                            {extractFilename(doc.filename)}
                                        </p>
                                        <div className="mt-2 flex flex-col items-center gap-1">
                                            {doc.size && (
                                                <p className="text-xs text-slate-500">
                                                    {formatFileSize(doc.size)}
                                                </p>
                                            )}
                                            <p className="text-xs text-slate-400">
                                                {doc.modified_date 
                                                    ? new Date(doc.modified_date).toLocaleDateString()
                                                    : new Date(doc.upload_date).toLocaleDateString()}
                                            </p>
                                        </div>
                                    </div>

                                    {/* Progress Bar */}
                                    {isUploading && (
                                        <div className="px-3 pb-3">
                                            <ProgressBar
                                                status={doc.status}
                                                progress={doc.uploadProgress ?? uploadProgress?.get(doc.id)}
                                                showLabel={false}
                                            />
                                        </div>
                                    )}

                                    {/* Hover Actions */}
                                    {isHovered && !isSelected && (
                                        <div className="absolute top-2 right-2 flex gap-1">
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation()
                                                    onSelect(doc)
                                                }}
                                                className="p-1.5 bg-white rounded-full shadow-md hover:bg-slate-50"
                                                title="Open"
                                            >
                                                <FileText className="w-3 h-3 text-slate-600" />
                                            </button>
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation()
                                                    onDelete(doc.id)
                                                }}
                                                className="p-1.5 bg-white rounded-full shadow-md hover:bg-red-50"
                                                title="Delete"
                                            >
                                                <Trash2 className="w-3 h-3 text-red-600" />
                                            </button>
                                        </div>
                                    )}
                                </div>
                            )
                        })}
                        {subfolders.length === 0 && filteredDocs.length === 0 && (
                            <div className="col-span-full flex flex-col items-center justify-center py-16 text-slate-400">
                                <Upload className="w-12 h-12 mb-4 text-slate-300" />
                                <p className="text-lg font-medium text-slate-600 mb-2">
                                    {searchQuery ? 'No files found' : currentFolder ? 'This folder is empty' : 'No documents yet'}
                                </p>
                                {!searchQuery && (
                                    <p className="text-sm text-slate-500">
                                        Drag and drop files or folders here, or use <span className="font-medium text-slate-600">"+ New"</span> to upload
                                    </p>
                                )}
                            </div>
                        )}
                    </div>
                ) : (
                    <div className="space-y-1">
                        {/* List Header */}
                        <div className="grid grid-cols-12 gap-4 px-4 py-2 text-xs font-semibold text-slate-500 uppercase tracking-wider border-b border-slate-200">
                            <div className="col-span-1">
                                <input
                                    type="checkbox"
                                    checked={selectedIds.size === filteredDocs.length && filteredDocs.length > 0}
                                    onChange={selectAll}
                                    className="w-4 h-4 text-blue-600 border-slate-300 rounded"
                                />
                            </div>
                            <div className="col-span-5">Name</div>
                            <div className="col-span-2">Owner</div>
                            <div className="col-span-2">Modified</div>
                            <div className="col-span-1">Size</div>
                            <div className="col-span-1"></div>
                        </div>

                        {/* List Items */}
                        {/* Display Folders First */}
                        {subfolders.map((folderPath) => {
                            const folderName = folderPath.split('/').pop() || folderPath
                            // Count documents directly in this folder AND in all subfolders
                            const folderDocCount = documents.filter(doc => 
                                doc.folder === folderPath || 
                                (doc.folder && doc.folder.startsWith(`${folderPath}/`))
                            ).length
                            
                            const folderStatus = getFolderStatus(folderPath, documents)
                            const folderProgress = getFolderProgress(folderPath, documents, uploadProgress)
                            const statusBgColor = folderStatus === 'uploading' ? 'bg-red-50' :
                                                  folderStatus === 'processing' ? 'bg-orange-50' :
                                                  folderStatus === 'completed' ? 'bg-blue-50' :
                                                  folderStatus === 'failed' ? 'bg-red-50' : ''
                            const borderColor = folderStatus === 'uploading' ? 'border-red-400' :
                                              folderStatus === 'processing' ? 'border-orange-400' :
                                              folderStatus === 'completed' ? 'border-blue-400' :
                                              folderStatus === 'failed' ? 'border-red-400' : 'border-slate-300'
                            const folderIconColor = folderStatus === 'uploading' ? 'text-red-600' :
                                                   folderStatus === 'processing' ? 'text-orange-600' :
                                                   folderStatus === 'completed' ? 'text-blue-600' :
                                                   'text-slate-600'
                            const isUploading = folderStatus === 'uploading' || folderStatus === 'processing'
                            
                            const isMenuOpen = folderActionMenu === folderPath
                            
                            return (
                                <div
                                    key={folderPath}
                                    onMouseEnter={() => setHoveredId(`folder-${folderPath}`)}
                                    onMouseLeave={() => setHoveredId(null)}
                                    className={cn(
                                        "grid grid-cols-12 gap-4 px-4 py-3 rounded-lg cursor-pointer transition-colors group border-l-4 relative folder-action-menu",
                                        statusBgColor || "hover:bg-slate-50",
                                        borderColor
                                    )}
                                >
                                    <div 
                                        onClick={() => setCurrentFolder(folderPath)}
                                        className="col-span-1 flex items-center"
                                    >
                                        <Folder className={cn("w-5 h-5", folderIconColor)} />
                                    </div>
                                    <div 
                                        onClick={() => setCurrentFolder(folderPath)}
                                        className="col-span-5 flex items-center gap-3"
                                    >
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium text-slate-900 truncate">
                                                {folderName}
                                            </p>
                                            <div className="flex items-center gap-2 mt-1">
                                                <p className="text-xs text-slate-500">
                                                    {folderDocCount} {folderDocCount === 1 ? 'item' : 'items'}
                                                </p>
                                                {isUploading && (
                                                    <ProgressBar
                                                        status={folderProgress.status as 'uploading' | 'processing' | 'completed' | 'failed'}
                                                        progress={folderProgress.progress}
                                                        showLabel={true}
                                                    />
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                    <div 
                                        onClick={() => setCurrentFolder(folderPath)}
                                        className="col-span-2 flex items-center text-sm text-slate-600"
                                    >
                                        Folder
                                    </div>
                                    <div 
                                        onClick={() => setCurrentFolder(folderPath)}
                                        className="col-span-2 flex items-center text-sm text-slate-600"
                                    >
                                        -
                                    </div>
                                    <div 
                                        onClick={() => setCurrentFolder(folderPath)}
                                        className="col-span-1 flex items-center text-sm text-slate-600"
                                    >
                                        -
                                    </div>
                                    <div className="col-span-1 flex items-center justify-end gap-2">
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation()
                                                setFolderActionMenu(isMenuOpen ? null : folderPath)
                                            }}
                                            className="p-1 rounded hover:bg-slate-200 opacity-0 group-hover:opacity-100 transition-opacity"
                                            title="Folder actions"
                                        >
                                            <MoreVertical className="w-4 h-4 text-slate-600" />
                                        </button>
                                        {isMenuOpen && (
                                            <div className="absolute right-4 top-full mt-1 w-48 bg-white border border-slate-200 rounded-lg shadow-lg z-50">
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation()
                                                        handleMoveFolderClick(folderPath)
                                                    }}
                                                    className="w-full text-left px-4 py-2 text-sm text-slate-700 hover:bg-slate-100 flex items-center gap-2"
                                                >
                                                    <Move className="w-4 h-4" />
                                                    Move Folder
                                                </button>
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation()
                                                        handleDeleteFolderClick(folderPath)
                                                    }}
                                                    className="w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50 flex items-center gap-2"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                    Delete Folder
                                                </button>
                                            </div>
                                        )}
                                        <ChevronRight className="w-4 h-4 text-slate-400" />
                                    </div>
                                </div>
                            )
                        })}
                        
                        {/* Display Documents */}
                        {filteredDocs.map((doc) => {
                            const isSelected = selectedIds.has(doc.id)
                            const isUploading = doc.status === 'uploading' || doc.status === 'processing'
                            const statusBgColor = doc.status === 'uploading' ? 'bg-red-50' :
                                                  doc.status === 'processing' ? 'bg-orange-50' :
                                                  doc.status === 'completed' ? 'bg-blue-50' :
                                                  doc.status === 'failed' ? 'bg-red-50' : ''

                            return (
                                <div
                                    key={doc.id}
                                    onMouseEnter={() => setHoveredId(doc.id)}
                                    onMouseLeave={() => setHoveredId(null)}
                                    onClick={() => !isSelected && onSelect(doc)}
                                    className={cn(
                                        "grid grid-cols-12 gap-4 px-4 py-3 rounded-lg hover:bg-slate-50 cursor-pointer transition-colors group",
                                        isSelected && "bg-blue-50",
                                        selectedDocId === doc.id && "bg-blue-100",
                                        !isSelected && statusBgColor
                                    )}
                                >
                                    <div className="col-span-1 flex items-center">
                                        <input
                                            type="checkbox"
                                            checked={isSelected}
                                            onChange={(e) => {
                                                e.stopPropagation()
                                                toggleSelection(doc.id)
                                            }}
                                            onClick={(e) => e.stopPropagation()}
                                            className="w-4 h-4 text-blue-600 border-slate-300 rounded"
                                        />
                                    </div>
                                    <div className="col-span-5 flex items-center gap-3">
                                        {getFileIcon(doc.filename)}
                                        <div className="flex-1 min-w-0">
                                            <p className="text-sm font-medium text-slate-900 truncate">
                                                {extractFilename(doc.filename)}
                                            </p>
                                            {isUploading && (
                                                <ProgressBar
                                                    status={doc.status}
                                                    progress={doc.uploadProgress ?? uploadProgress?.get(doc.id)}
                                                    showLabel={true}
                                                />
                                            )}
                                        </div>
                                    </div>
                                    <div className="col-span-2 flex items-center text-sm text-slate-600">
                                        Me
                                    </div>
                                    <div className="col-span-2 flex items-center text-sm text-slate-600">
                                        {doc.modified_date 
                                            ? new Date(doc.modified_date).toLocaleDateString()
                                            : new Date(doc.upload_date).toLocaleDateString()}
                                    </div>
                                    <div className="col-span-1 flex items-center text-sm text-slate-600">
                                        {formatFileSize(doc.size)}
                                    </div>
                                    <div className="col-span-1 flex items-center justify-end">
                                        <button
                                            onClick={(e) => {
                                                e.stopPropagation()
                                                onDelete(doc.id)
                                            }}
                                            className="p-1 rounded-full hover:bg-slate-200 opacity-0 group-hover:opacity-100 transition-opacity"
                                        >
                                            <MoreVertical className="w-4 h-4 text-slate-600" />
                                        </button>
                                    </div>
                                </div>
                            )
                        })}
                        {subfolders.length === 0 && filteredDocs.length === 0 && (
                            <div className="flex flex-col items-center justify-center py-16 text-slate-400">
                                <Upload className="w-12 h-12 mb-4 text-slate-300" />
                                <p className="text-lg font-medium text-slate-600 mb-2">
                                    {searchQuery ? 'No files found' : currentFolder ? 'This folder is empty' : 'No documents yet'}
                                </p>
                                {!searchQuery && (
                                    <p className="text-sm text-slate-500">
                                        Drag and drop files or folders here, or use <span className="font-medium text-slate-600">"+ New"</span> to upload
                                    </p>
                                )}
                            </div>
                        )}
                    </div>
                )}
            </div>

            {/* Drag and Drop Overlay */}
            {isDragging && (
                <div className="absolute inset-0 z-50 bg-blue-500/10 border-4 border-dashed border-blue-500 rounded-lg flex items-center justify-center pointer-events-none">
                    <div className="bg-white rounded-lg shadow-xl p-8 flex flex-col items-center gap-4">
                        <div className="w-16 h-16 rounded-full bg-blue-100 flex items-center justify-center">
                            <Upload className="w-8 h-8 text-blue-600" />
                        </div>
                        <div className="text-center">
                            <p className="text-lg font-semibold text-slate-900">Drop files to upload</p>
                            <p className="text-sm text-slate-500 mt-1">Release to start uploading</p>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}

