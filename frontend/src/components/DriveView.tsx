import { useState, useMemo, useEffect } from 'react'
import { Grid, List, Search, Download, Share2, Trash2, FileText, Folder, Image, File, Upload, ChevronRight, Archive, User, Settings, LogOut, Bell, HelpCircle, ChevronDown } from 'lucide-react'
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
        case 'ready':
            return 'bg-slate-50 border-slate-200'
        case 'processing':
            return 'bg-orange-50 border-orange-300'
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
 * @returns Object with status, optional progress percentage (0-100), and counts (completed/total)
 */
function getFolderProgress(
    folderPath: string,
    documents: Document[],
    uploadProgress?: Map<string, number>
): { status: string; progress?: number; completedCount?: number; totalCount?: number } {
    // Get all documents in this folder and subfolders (recursive)
    const folderDocs = documents.filter(doc =>
        doc.folder === folderPath ||
        (doc.folder && doc.folder.startsWith(`${folderPath}/`))
    )

    const totalCount = folderDocs.length
    const completedCount = folderDocs.filter(doc => doc.status === 'completed').length

    if (folderDocs.length === 0) {
        return { status: 'completed', progress: 100, completedCount: 0, totalCount: 0 }
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
        return { status: 'uploading', progress: avgProgress, completedCount, totalCount }
    }

    // Check if any file is processing (show completed/total count)
    if (folderDocs.some(doc => doc.status === 'processing')) {
        return { status: 'processing', completedCount, totalCount }
    }

    // Check if any file failed
    if (folderDocs.some(doc => doc.status === 'failed')) {
        return { status: 'failed', completedCount, totalCount }
    }

    // All files are completed
    return { status: 'completed', progress: 100, completedCount, totalCount }
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
}

export function DriveView({ documents, selectedDocId, onSelect, onDelete, onUpload, uploadProgress, currentFolder: propCurrentFolder, onFolderChange, onDeleteFolder }: DriveViewProps) {
    const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
    const [searchQuery, setSearchQuery] = useState('')
    const [searchResults, setSearchResults] = useState<Document[]>([])
    const [isSearching, setIsSearching] = useState(false)
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
    const [hoveredId, setHoveredId] = useState<string | null>(null)
    const [isDragging, setIsDragging] = useState(false)
    const [internalCurrentFolder, setInternalCurrentFolder] = useState<string | null>(null)
    const [showProfileMenu, setShowProfileMenu] = useState(false)

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

    // Perform semantic search when query is provided
    useEffect(() => {
        if (searchQuery.trim().length > 0) {
            setIsSearching(true)
            const timeoutId = setTimeout(async () => {
                try {
                    const results = await api.semanticSearch(searchQuery.trim(), 50, 0.1)
                    // Fetch full document details for each result
                    const fullDocs: Document[] = []
                    for (const result of results.results) {
                        try {
                            const doc = await api.getDocument(result.document_id)
                            fullDocs.push(doc)
                        } catch (err) {
                            console.error(`Failed to fetch document ${result.document_id}:`, err)
                        }
                    }
                    setSearchResults(fullDocs)
                } catch (err) {
                    console.error("Semantic search failed, falling back to text search:", err)
                    // Fallback to simple text search
                    const filtered = documents.filter(doc =>
                        extractFilename(doc.filename).toLowerCase().includes(searchQuery.toLowerCase()) ||
                        doc.summary?.toLowerCase().includes(searchQuery.toLowerCase()) ||
                        doc.tags?.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
                    )
                    setSearchResults(filtered)
                } finally {
                    setIsSearching(false)
                }
            }, 500) // Debounce 500ms

            return () => clearTimeout(timeoutId)
        } else {
            setSearchResults([])
            setIsSearching(false)
        }
    }, [searchQuery, documents])

    // Filter documents by current folder and search query
    const filteredDocs = useMemo(() => {
        // If searching, use search results (show all matches globally, ignore folder filter)
        if (searchQuery.trim().length > 0) {
            return searchResults
        }

        // Normal filtering when not searching
        let filtered = documents

        // Filter by current folder
        if (currentFolder) {
            filtered = filtered.filter(doc => doc.folder === currentFolder)
        } else {
            // Show only root documents (no folder) when at root
            filtered = filtered.filter(doc => !doc.folder)
        }

        return filtered
    }, [documents, currentFolder, searchQuery, searchResults])

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
        console.log(`[Drag & Drop] Checking ${items.length} items for folder structure`)
        
        let hasDirectories = items.some(item => {
            try {
                const entry = item.webkitGetAsEntry()
                const isDir = entry && entry.isDirectory
                if (isDir) {
                    console.log(`[Drag & Drop] Found directory: ${entry.name}`)
                }
                return isDir
            } catch (err) {
                console.warn(`[Drag & Drop] Error checking entry:`, err)
                return false
            }
        })
        
        console.log(`[Drag & Drop] Has directories: ${hasDirectories}`)

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
                    try {
                        const file = await new Promise<File>((resolve, reject) => {
                            entry.file((file: File) => resolve(file), reject)
                        })
                        allFiles.push(file)
                        if (basePath) {
                            filePaths.set(file, basePath)
                        }
                    } catch (err) {
                        console.error(`Error processing file entry: ${err}`)
                    }
                } else if (entry.isDirectory) {
                    // Recursively process directory contents
                    try {
                        const reader = entry.createReader()
                        
                        // Read all entries (may require multiple reads)
                        let entries: any[] = []
                        let hasMore = true
                        while (hasMore) {
                            const batch = await new Promise<any[]>((resolve, reject) => {
                                reader.readEntries((batch: any[]) => {
                                    resolve(batch)
                                }, reject)
                            })
                            entries.push(...batch)
                            hasMore = batch.length > 0
                        }

                        const folderName = entry.name
                        // Build nested folder path (e.g., "folder1/subfolder")
                        const newBasePath = basePath ? `${basePath}/${folderName}` : folderName

                        // Process all entries in the directory (files and subdirectories)
                        for (const subEntry of entries) {
                            await processEntry(subEntry, newBasePath)
                        }
                    } catch (err) {
                        console.error(`Error processing directory entry: ${err}`)
                    }
                }
            }

            // Process all dropped items (could be files or folders)
            try {
                for (const item of items) {
                    try {
                        const entry = item.webkitGetAsEntry()
                        if (entry) {
                            await processEntry(entry)
                        } else {
                            console.warn(`[Drag & Drop] Entry is null for item: ${item.type}`)
                        }
                    } catch (entryError) {
                        console.error(`[Drag & Drop] Error getting entry:`, entryError)
                        // Fallback: if webkitGetAsEntry fails, try to get files directly
                        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                            console.log(`[Drag & Drop] Falling back to direct file access`)
                            // This will be handled by the else branch below
                            break
                        }
                    }
                }
            } catch (processError) {
                console.error(`[Drag & Drop] Error processing entries:`, processError)
                // Fallback to regular file handling
                if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                    console.log(`[Drag & Drop] Falling back to regular file upload`)
                    // Set hasDirectories to false to trigger fallback handling below
                    hasDirectories = false
                } else {
                    // No files available, show error
                    setUploadError("Folder drag-and-drop is not supported in this browser. Please use the 'Folder Upload' button in the sidebar instead.")
                    return
                }
            }
            
            // If no files were collected, fall back to regular file handling
            if (allFiles.length === 0 && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                console.log(`[Drag & Drop] No files collected from directory entries, falling back to regular files`)
                hasDirectories = false
            }

            if (allFiles.length > 0) {
                console.log(`[Drag & Drop] Processing ${allFiles.length} files from folder structure`)
                
                // Create FileList from collected files
                // DataTransfer API allows us to create a FileList programmatically
                const dataTransfer = new DataTransfer()
                
                // Create a map from filename to folder path for reliable lookup
                const filenameToFolderPath = new Map<string, string>()
                allFiles.forEach(file => {
                    const folderPath = filePaths.get(file)
                    if (folderPath) {
                        filenameToFolderPath.set(file.name, folderPath)
                        console.log(`[Drag & Drop] File: ${file.name} -> Folder: ${folderPath}`)
                    }
                    dataTransfer.items.add(file)
                })

                /**
                 * Creates a function that returns the folder path for each file.
                 * Uses filename lookup since File objects from DataTransfer might be different instances.
                 * Preserves folder structure and prepends current folder if navigating within one.
                 */
                const getFolderPath = (file: File): string | undefined => {
                    // Try to get folder path from filename lookup first (more reliable)
                    let folderPath = filenameToFolderPath.get(file.name)
                    
                    // Fallback to direct File object lookup
                    if (!folderPath) {
                        folderPath = filePaths.get(file)
                    }
                    
                    if (folderPath) {
                        // If we're currently viewing a folder, prepend it to maintain structure
                        const finalPath = currentFolder ? `${currentFolder}/${folderPath}` : folderPath
                        console.log(`[Drag & Drop] Resolved folder for ${file.name}: ${finalPath}`)
                        return finalPath
                    }
                    
                    console.log(`[Drag & Drop] No folder path found for ${file.name}, using current folder: ${currentFolder || 'root'}`)
                    return currentFolder || undefined
                }

                console.log(`[Drag & Drop] Starting upload of ${allFiles.length} files`)
                await onUpload(dataTransfer.files, getFolderPath)
            } else {
                console.warn('[Drag & Drop] No files found in dropped folder')
            }
        }
        
        // Fallback: Handle as regular files if folder detection failed or not supported
        if (!hasDirectories && e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            // Regular file upload or files with webkitRelativePath (from webkitdirectory input)
            // This handles files dropped from folder input elements (not direct folder drag)
            const files = Array.from(e.dataTransfer.files)
            console.log(`[Drag & Drop] Handling as regular files (${files.length} files)`)

            // Check for ZIP files
            const zipFiles = files.filter(file => {
                const ext = file.name.split('.').pop()?.toLowerCase()
                return ext === 'zip'
            })

            if (zipFiles.length > 0) {
                // Handle ZIP file uploads - backend will extract and create folder structure
                await onUpload(e.dataTransfer.files, currentFolder || undefined)
            } else {
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
    }

    // Get breadcrumb path
    const breadcrumbPath = currentFolder ? currentFolder.split('/') : []


    const handleDeleteFolderClick = async (folderPath: string) => {
        const folderDocs = documents.filter(doc =>
            doc.folder === folderPath ||
            (doc.folder && doc.folder.startsWith(`${folderPath}/`))
        )
        const count = folderDocs.length

        if (!window.confirm(`Are you sure you want to delete this folder?\n\nThis will delete ${count} ${count === 1 ? 'item' : 'items'} including all files and subfolders.`)) {
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
        } catch (err: any) {
            console.error("Delete folder failed", err)
            const errorMsg = err.response?.data?.detail || err.message || "Failed to delete folder"
            alert(errorMsg)
        }
    }

    // Close menu when clicking outside
    useEffect(() => {
        const handleClickOutside = (event: MouseEvent) => {
            if (showProfileMenu && !(event.target as Element).closest('.profile-menu-container')) {
                setShowProfileMenu(false)
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [showProfileMenu])

    return (
        <div
            className="flex-1 flex flex-col bg-gradient-to-br from-white via-slate-50/30 to-blue-50/20 relative"
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
        >
            {/* Header Bar - Search, View Toggle, and Profile */}
            <div className="h-[76px] px-6 bg-white/80 backdrop-blur-sm flex items-center justify-between gap-4 shadow-soft">
                {/* Left: Search Bar */}
                <div className="flex-1 flex justify-center">
                    <div className="relative max-w-md w-full group">
                        <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-slate-400 group-focus-within:text-primary-600 transition-colors" />
                        <input
                            type="text"
                            placeholder={isSearching ? "Searching..." : "Search documents (AI-powered semantic search)..."}
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full pl-12 pr-4 py-3 border-2 border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-all duration-200 bg-white hover:border-slate-300"
                        />
                        {isSearching && (
                            <div className="absolute right-4 top-1/2 transform -translate-y-1/2">
                                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-primary-600"></div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Right: View Toggle and Profile */}
                <div className="flex items-center gap-3">
                    {/* View Toggle */}
                    <div className="flex items-center gap-1 border-2 border-slate-200 rounded-xl p-1 bg-slate-50/50">
                        <button
                            onClick={() => setViewMode('grid')}
                            className={cn(
                                "p-2 rounded-lg transition-all duration-200",
                                viewMode === 'grid' ? "bg-gradient-to-r from-primary-600 to-indigo-600 text-white shadow-md" : "text-slate-600 hover:bg-white hover:text-primary-600"
                            )}
                            title="Grid view"
                        >
                            <Grid className="w-5 h-5" />
                        </button>
                        <button
                            onClick={() => setViewMode('list')}
                            className={cn(
                                "p-2 rounded-lg transition-all duration-200",
                                viewMode === 'list' ? "bg-gradient-to-r from-primary-600 to-indigo-600 text-white shadow-md" : "text-slate-600 hover:bg-white hover:text-primary-600"
                            )}
                            title="List view"
                        >
                            <List className="w-5 h-5" />
                        </button>
                    </div>

                    {/* Notifications */}
                    <button
                        className="relative p-2 rounded-lg hover:bg-slate-100 transition-all duration-200 group"
                        title="Notifications"
                    >
                        <Bell className="w-5 h-5 text-slate-600 group-hover:text-primary-600 transition-colors" />
                        <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full border-2 border-white"></span>
                    </button>

                    {/* Profile Menu */}
                    <div className="relative profile-menu-container">
                        <button
                            onClick={() => setShowProfileMenu(!showProfileMenu)}
                            className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-slate-100 transition-all duration-200 group"
                        >
                            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary-500 to-indigo-600 flex items-center justify-center text-white font-semibold text-sm shadow-sm">
                                S
                            </div>
                            <ChevronDown className={cn(
                                "w-4 h-4 text-slate-600 transition-transform duration-200",
                                showProfileMenu && "transform rotate-180"
                            )} />
                        </button>

                        {/* Profile Dropdown */}
                        {showProfileMenu && (
                            <div className="absolute right-0 mt-2 w-56 bg-white/95 backdrop-blur-md border border-slate-200 rounded-xl shadow-2xl z-50 overflow-hidden animate-slide-down profile-menu-container">
                                {/* User Info */}
                                <div className="px-4 py-3 border-b border-slate-200 bg-gradient-to-r from-primary-50/50 to-indigo-50/30">
                                    <div className="flex items-center gap-3">
                                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-primary-500 to-indigo-600 flex items-center justify-center text-white font-semibold shadow-sm">
                                            S
                                        </div>
                                        <div>
                                            <p className="text-sm font-semibold text-slate-900">Sri</p>
                                            <p className="text-xs text-slate-500">sri@example.com</p>
                                        </div>
                                    </div>
                                </div>

                                {/* Menu Items */}
                                <div className="py-2">
                                    <button
                                        onClick={() => {
                                            setShowProfileMenu(false)
                                            // Handle account settings
                                        }}
                                        className="w-full text-left px-4 py-2.5 text-sm text-slate-700 hover:bg-gradient-to-r hover:from-blue-50 hover:to-indigo-50 flex items-center gap-3 transition-all group"
                                    >
                                        <User className="w-4 h-4 text-slate-500 group-hover:text-primary-600 transition-colors" />
                                        <span>My Account</span>
                                    </button>
                                    <button
                                        onClick={() => {
                                            setShowProfileMenu(false)
                                            // Handle settings
                                        }}
                                        className="w-full text-left px-4 py-2.5 text-sm text-slate-700 hover:bg-gradient-to-r hover:from-blue-50 hover:to-indigo-50 flex items-center gap-3 transition-all group"
                                    >
                                        <Settings className="w-4 h-4 text-slate-500 group-hover:text-primary-600 transition-colors" />
                                        <span>Settings</span>
                                    </button>
                                    <button
                                        onClick={() => {
                                            setShowProfileMenu(false)
                                            // Handle help
                                        }}
                                        className="w-full text-left px-4 py-2.5 text-sm text-slate-700 hover:bg-gradient-to-r hover:from-blue-50 hover:to-indigo-50 flex items-center gap-3 transition-all group"
                                    >
                                        <HelpCircle className="w-4 h-4 text-slate-500 group-hover:text-primary-600 transition-colors" />
                                        <span>Help & Support</span>
                                    </button>
                                    <div className="border-t border-slate-200 my-1"></div>
                                    <button
                                        onClick={() => {
                                            setShowProfileMenu(false)
                                            // Handle logout
                                        }}
                                        className="w-full text-left px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 flex items-center gap-3 transition-all group"
                                    >
                                        <LogOut className="w-4 h-4 group-hover:scale-110 transition-transform" />
                                        <span>Sign Out</span>
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>

            {/* Breadcrumb Navigation */}
            {breadcrumbPath.length > 0 && (
                <div className="border-b border-slate-200/80 px-6 py-4 bg-gradient-to-r from-blue-50 via-indigo-50/50 to-purple-50/30 backdrop-blur-sm">
                    <nav className="flex items-center gap-2 text-sm">
                        <button
                            onClick={() => setCurrentFolder(null)}
                            className="flex items-center gap-2 text-slate-600 hover:text-primary-600 transition-all duration-200 font-medium px-2 py-1 rounded-lg hover:bg-white/60 group"
                        >
                            <Archive className="w-4 h-4 group-hover:scale-110 transition-transform" />
                            <span>My Vault</span>
                        </button>
                        {breadcrumbPath.map((folder, index) => {
                            const path = breadcrumbPath.slice(0, index + 1).join('/')
                            return (
                                <div key={path} className="flex items-center gap-2">
                                    <ChevronRight className="w-4 h-4 text-slate-400" />
                                    <button
                                        onClick={() => setCurrentFolder(path)}
                                        className="text-slate-600 hover:text-primary-600 transition-all duration-200 font-medium px-2 py-1 rounded-lg hover:bg-white/60"
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
                <div className="border-b border-slate-200/80 px-6 py-3 flex items-center justify-end bg-gradient-to-r from-primary-50/50 to-indigo-50/30 animate-slide-down">
                    <div className="flex items-center gap-3">
                        <span className="text-sm font-medium text-slate-700 px-3 py-1.5 bg-white rounded-lg shadow-soft">{selectedIds.size} selected</span>
                        <button className="p-2 hover:bg-white rounded-lg transition-all hover:shadow-soft group">
                            <Download className="w-5 h-5 text-slate-600 group-hover:text-primary-600 transition-colors" />
                        </button>
                        <button className="p-2 hover:bg-white rounded-lg transition-all hover:shadow-soft group">
                            <Share2 className="w-5 h-5 text-slate-600 group-hover:text-primary-600 transition-colors" />
                        </button>
                        <button
                            onClick={() => {
                                selectedIds.forEach(id => onDelete(id))
                                setSelectedIds(new Set())
                            }}
                            className="p-2 hover:bg-danger-50 rounded-lg transition-all hover:shadow-soft group"
                        >
                            <Trash2 className="w-5 h-5 text-danger-600 group-hover:scale-110 transition-transform" />
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


                            return (
                                <div
                                    key={folderPath}
                                    onMouseEnter={() => setHoveredId(`folder-${folderPath}`)}
                                    onMouseLeave={() => setHoveredId(null)}
                                    className={cn(
                                        "relative group cursor-pointer rounded-2xl border-2 hover:border-primary-300 hover:shadow-large transition-all duration-300 overflow-hidden card-hover",
                                        statusColor || "bg-gradient-to-br from-white to-slate-50/50 border-slate-200 shadow-soft"
                                    )}
                                >
                                    {/* Folder Icon - Clickable to navigate */}
                                    <div
                                        onClick={() => setCurrentFolder(folderPath)}
                                        className="p-6 flex flex-col items-center justify-center min-h-[140px] w-full relative"
                                    >
                                        <div className="absolute inset-0 bg-gradient-to-br from-primary-50/0 to-indigo-50/0 group-hover:from-primary-50/50 group-hover:to-indigo-50/30 transition-all duration-300"></div>
                                        <Folder className={cn("w-14 h-14 relative z-10 transition-all duration-300 group-hover:scale-110", folderIconColor)} />
                                        <p className="mt-4 text-sm font-semibold text-slate-700 text-center line-clamp-2 px-2 break-words w-full min-w-0 max-w-full relative z-10">
                                            {folderName}
                                        </p>
                                        {isUploading && folderProgress.completedCount !== undefined && folderProgress.totalCount !== undefined ? (
                                            <p className="mt-1.5 text-xs font-medium relative z-10">
                                                <span className={cn(
                                                    folderStatus === 'processing' ? 'text-orange-600' : 'text-red-600'
                                                )}>
                                                    {folderProgress.completedCount}/{folderProgress.totalCount} completed
                                                </span>
                                            </p>
                                        ) : (
                                            <p className="mt-1.5 text-xs text-slate-500 font-medium relative z-10">
                                                {folderDocCount} {folderDocCount === 1 ? 'item' : 'items'}
                                            </p>
                                        )}
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

                                    {/* Delete Button - Same as file cards */}
                                    {hoveredId === `folder-${folderPath}` && (
                                        <div className="absolute top-2 right-2 flex gap-1">
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation()
                                                    handleDeleteFolderClick(folderPath)
                                                }}
                                                className="p-1.5 bg-white rounded-full shadow-lg hover:bg-red-50 hover:shadow-xl transition-all duration-200"
                                                title="Delete"
                                            >
                                                <Trash2 className="w-3 h-3 text-red-600" />
                                            </button>
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
                                    onClick={() => onSelect(doc)}
                                    className={cn(
                                        "relative group cursor-pointer rounded-xl border-2 transition-all duration-200",
                                        isSelected ? "border-blue-500 bg-blue-50 shadow-md" : 
                                        doc.status === 'processing' ? "border-orange-300 bg-orange-50 hover:border-orange-400 hover:shadow-lg" :
                                        doc.status === 'uploading' ? "border-red-300 bg-red-50 hover:border-red-400 hover:shadow-lg" :
                                        "border-slate-200 hover:border-blue-300 hover:shadow-lg",
                                        statusColor || fileTypeColor || "bg-white shadow-sm"
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

                                    {/* Progress Bar - Same as folders */}
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
                                                className="p-1.5 bg-white rounded-full shadow-lg hover:bg-blue-50 hover:shadow-xl transition-all duration-200"
                                                title="Open"
                                            >
                                                <FileText className="w-3 h-3 text-blue-600" />
                                            </button>
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation()
                                                    onDelete(doc.id)
                                                }}
                                                className="p-1.5 bg-white rounded-full shadow-lg hover:bg-red-50 hover:shadow-xl transition-all duration-200"
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
                                    {searchQuery ? 'No files found' : currentFolder ? 'This folder is empty' : 'DocVaultAI is empty'}
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


                            return (
                                <div
                                    key={folderPath}
                                    onMouseEnter={() => setHoveredId(`folder-${folderPath}`)}
                                    onMouseLeave={() => setHoveredId(null)}
                                    className={cn(
                                        "grid grid-cols-12 gap-4 px-4 py-3 rounded-lg cursor-pointer transition-colors group border-l-4 relative",
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
                                                {isUploading && folderProgress.completedCount !== undefined && folderProgress.totalCount !== undefined ? (
                                                    <p className={cn(
                                                        "text-xs font-medium",
                                                        folderStatus === 'processing' ? 'text-orange-600' : 'text-red-600'
                                                    )}>
                                                        {folderProgress.completedCount}/{folderProgress.totalCount} completed
                                                    </p>
                                                ) : (
                                                    <p className="text-xs text-slate-500">
                                                        {folderDocCount} {folderDocCount === 1 ? 'item' : 'items'}
                                                    </p>
                                                )}
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
                                                handleDeleteFolderClick(folderPath)
                                            }}
                                            className="p-1 rounded-full hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-opacity"
                                            title="Delete"
                                        >
                                            <Trash2 className="w-4 h-4 text-red-600" />
                                        </button>
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
                                doc.status === 'ready' ? 'bg-slate-50' :
                                    doc.status === 'processing' ? 'bg-orange-50' :
                                        doc.status === 'completed' ? 'bg-blue-50' :
                                            doc.status === 'failed' ? 'bg-red-50' : ''

                            return (
                                <div
                                    key={doc.id}
                                    onMouseEnter={() => setHoveredId(doc.id)}
                                    onMouseLeave={() => setHoveredId(null)}
                                    onClick={() => onSelect(doc)}
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
                                            title="Delete file"
                                        >
                                            <Trash2 className="w-4 h-4 text-slate-600" />
                                        </button>
                                    </div>
                                </div>
                            )
                        })}
                        {subfolders.length === 0 && filteredDocs.length === 0 && (
                            <div className="flex flex-col items-center justify-center py-16 text-slate-400">
                                <Upload className="w-12 h-12 mb-4 text-slate-300" />
                                <p className="text-lg font-medium text-slate-600 mb-2">
                                    {searchQuery ? 'No files found' : currentFolder ? 'This folder is empty' : 'DocVaultAI is empty'}
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
                <div className="absolute inset-0 z-50 bg-blue-500/10 border-4 border-dashed border-blue-500 rounded-xl flex items-center justify-center pointer-events-none backdrop-blur-sm">
                    <div className="bg-white rounded-xl shadow-2xl p-8 flex flex-col items-center gap-4 border border-blue-200">
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

            {/* Footer with Copyright */}
            <footer className="border-t border-slate-200/80 bg-white/80 backdrop-blur-sm px-6 py-4 mt-auto">
                <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-sm text-slate-500">
                    <div className="flex items-center gap-6">
                        <span>© {new Date().getFullYear()} DocVaultAI. All rights reserved.</span>
                        <div className="hidden sm:flex items-center gap-4">
                            <a href="#" className="hover:text-primary-600 transition-colors">Privacy Policy</a>
                            <a href="#" className="hover:text-primary-600 transition-colors">Terms of Service</a>
                            <a href="#" className="hover:text-primary-600 transition-colors">Support</a>
                        </div>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-slate-400">
                        <span>Version 1.0.0</span>
                        <span>•</span>
                        <span>Powered by AI</span>
                    </div>
                </div>
            </footer>
        </div>
    )
}

