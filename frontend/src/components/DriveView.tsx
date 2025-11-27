import { useState } from 'react'
import { Grid, List, Search, MoreVertical, Download, Share2, Trash2, FileText, Folder, Image, File, FileType, Upload } from 'lucide-react'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { Document } from '../types'
import { ProgressBar } from './ProgressBar'
import { formatFileSize } from '../utils/formatSize'

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

interface DriveViewProps {
    documents: Document[]
    selectedDocId?: string
    onSelect: (doc: Document) => void
    onDelete: (id: string) => void
    onUpload?: (files: FileList, folder?: string | ((file: File) => string | undefined)) => Promise<void>
    uploadProgress?: Map<string, number>
}

export function DriveView({ documents, selectedDocId, onSelect, onDelete, onUpload, uploadProgress }: DriveViewProps) {
    const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid')
    const [searchQuery, setSearchQuery] = useState('')
    const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
    const [hoveredId, setHoveredId] = useState<string | null>(null)
    const [isDragging, setIsDragging] = useState(false)

    const filteredDocs = documents.filter(doc =>
        doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
    )

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
        if (e.dataTransfer.types.includes('Files')) {
            setIsDragging(true)
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

    const handleDrop = async (e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        setIsDragging(false)

        if (e.dataTransfer.files && e.dataTransfer.files.length > 0 && onUpload) {
            const files = Array.from(e.dataTransfer.files)
            
            // Check if any file has webkitRelativePath (indicates folder drag & drop)
            const hasFolderStructure = files.some(file => (file as any).webkitRelativePath)
            
            if (hasFolderStructure) {
                // Extract folder path from each file's webkitRelativePath
                const getFolderPath = (file: File): string | undefined => {
                    const relativePath = (file as any).webkitRelativePath
                    
                    if (!relativePath) {
                        return undefined
                    }
                    
                    const pathParts = relativePath.split('/')
                    
                    if (pathParts.length > 1) {
                        // Remove the filename to get the folder path
                        const folderPath = pathParts.slice(0, -1).join('/')
                        return folderPath || undefined
                    }
                    // File is in root of selected folder
                    return undefined
                }
                
                // Upload files with folder structure preserved
                await onUpload(e.dataTransfer.files, getFolderPath)
            } else {
                // Regular file upload (no folder structure)
                await onUpload(e.dataTransfer.files)
            }
        }
    }

    return (
        <div 
            className="flex-1 flex flex-col bg-white relative"
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
        >
            {/* Toolbar */}
            <div className="border-b border-slate-200 px-6 py-3 flex items-center justify-between">
                <div className="flex items-center gap-4 flex-1">
                    {/* Search */}
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

                {/* Actions */}
                {selectedIds.size > 0 && (
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
                )}
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-6">
                {viewMode === 'grid' ? (
                    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
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
                                    <div className="p-6 flex flex-col items-center justify-center min-h-[120px]">
                                        {getFileIcon(doc.filename)}
                                        <p className="mt-3 text-xs font-medium text-slate-700 text-center line-clamp-2 px-2">
                                            {doc.filename}
                                        </p>
                                        {doc.size && (
                                            <p className="mt-1 text-xs text-slate-500">
                                                {formatFileSize(doc.size)}
                                            </p>
                                        )}
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
                        {filteredDocs.length === 0 && (
                            <div className="col-span-full text-center py-12 text-slate-400">
                                {searchQuery ? 'No files found' : 'No documents yet'}
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
                                                {doc.filename}
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
                                        {new Date(doc.upload_date).toLocaleDateString()}
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
                        {filteredDocs.length === 0 && (
                            <div className="text-center py-12 text-slate-400">
                                {searchQuery ? 'No files found' : 'No documents yet'}
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

