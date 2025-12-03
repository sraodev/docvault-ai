import { useState } from 'react'
import { Upload, Loader2, AlertCircle, X } from 'lucide-react'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { logger } from '../utils/logger'
import {
    getUnsupportedFiles,
    getSupportedFormatsDisplay,
    SUPPORTED_FORMATS_SET,
    DOCUMENT_FORMATS,
    TEXT_FORMATS,
    CODE_FORMATS,
    WEB_FORMATS,
    CONFIG_FORMATS,
    ZIP_FORMAT
} from '../utils/supportedFormats'

function cn(...inputs: (string | undefined | null | false)[]) {
    return twMerge(clsx(inputs))
}

interface UploadAreaProps {
    onUpload: (files: FileList, folder?: string | ((file: File) => string | undefined)) => Promise<void>
    isUploading: boolean
    error: string | null
}

export function UploadArea({ onUpload, isUploading, error }: UploadAreaProps) {
    const [isDragging, setIsDragging] = useState(false)
    const [unsupportedFiles, setUnsupportedFiles] = useState<string[]>([])

    const onDragOver = (e: React.DragEvent) => {
        e.preventDefault()
        setIsDragging(true)
    }

    const onDragLeave = (e: React.DragEvent) => {
        e.preventDefault()
        setIsDragging(false)
    }

    const onDrop = async (e: React.DragEvent) => {
        e.preventDefault()
        setIsDragging(false)
        if (e.dataTransfer.files?.length) {
            const files = Array.from(e.dataTransfer.files)

            // Check for unsupported files
            const unsupported = getUnsupportedFiles(files)
            if (unsupported.length > 0) {
                setUnsupportedFiles(unsupported.map(f => f.name))
                return // Don't proceed with upload
            }

            setUnsupportedFiles([]) // Clear any previous errors

            // Filter to only supported files
            const supportedFiles = files.filter(file => {
                const ext = file.name.toLowerCase().substring(file.name.lastIndexOf('.'))
                return SUPPORTED_FORMATS_SET.has(ext)
            })

            if (supportedFiles.length === 0) {
                return // No supported files
            }

            // Create FileList from supported files
            const dataTransfer = new DataTransfer()
            supportedFiles.forEach(file => dataTransfer.items.add(file))
            const supportedFileList = dataTransfer.files

            // Check for ZIP files - backend will extract and create folder structure
            const hasZipFiles = supportedFiles.some(file => {
                const ext = file.name.split('.').pop()?.toLowerCase()
                return ext === 'zip'
            })

            if (hasZipFiles) {
                // Handle ZIP files - backend will extract and create folders
                await onUpload(supportedFileList)
            } else {
                // Check if any file has webkitRelativePath (indicates folder drag & drop)
                const hasFolderStructure = supportedFiles.some(file => (file as any).webkitRelativePath)

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
                    await onUpload(supportedFileList, getFolderPath)
                } else {
                    // Regular file upload (no folder structure)
                    await onUpload(supportedFileList)
                }
            }
        }
    }

    const handleFileInput = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files?.length) {
            const files = Array.from(e.target.files)

            // Check for unsupported files
            const unsupported = getUnsupportedFiles(files)
            if (unsupported.length > 0) {
                const unsupportedNames = unsupported.map(f => f.name)
                setUnsupportedFiles(unsupportedNames)
                logger.warn("Unsupported files detected in file input", "UploadArea", {
                    unsupportedFiles: unsupportedNames,
                    totalFiles: files.length
                })
                e.target.value = '' // Reset input
                return // Don't proceed with upload
            }

            setUnsupportedFiles([]) // Clear any previous errors

            // Create FileList from supported files only
            const dataTransfer = new DataTransfer()
            files.forEach(file => dataTransfer.items.add(file))
            await onUpload(dataTransfer.files)
        }
    }

    return (
        <div className="p-4">
            {/* Upload Area */}
            <label
                onDragOver={onDragOver}
                onDragLeave={onDragLeave}
                onDrop={onDrop}
                className={cn(
                    "flex flex-col items-center justify-center w-full h-24 border-2 border-dashed rounded-lg cursor-pointer transition-colors",
                    isDragging ? "border-blue-500 bg-blue-50" : "border-slate-300 bg-slate-50 hover:bg-slate-100"
                )}
            >
                <div className="flex flex-col items-center justify-center">
                    {isUploading ? (
                        <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
                    ) : (
                        <>
                            <Upload className={cn("w-5 h-5 mb-1", isDragging ? "text-blue-500" : "text-slate-400")} />
                            <p className="text-xs text-slate-500 font-medium">
                                {isDragging ? "Drop files" : "Upload files"}
                            </p>
                        </>
                    )}
                </div>
                <input
                    type="file"
                    className="hidden"
                    multiple
                    onChange={handleFileInput}
                    disabled={isUploading}
                    accept={[...DOCUMENT_FORMATS, ...TEXT_FORMATS, ...CODE_FORMATS, ...WEB_FORMATS, ...CONFIG_FORMATS, ZIP_FORMAT].join(',')}
                />
            </label>

            {/* Unsupported files warning */}
            {unsupportedFiles.length > 0 && (
                <div className="mt-2 text-xs flex items-start gap-2 p-2 rounded-lg bg-orange-50 text-orange-700 border border-orange-200 animate-in fade-in slide-in-from-top-2">
                    <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5 text-orange-600" />
                    <div className="flex-1">
                        <span className="block font-medium mb-1">Unsupported File Format</span>
                        <div className="space-y-1">
                            {unsupportedFiles.map((filename, idx) => (
                                <div key={idx} className="flex items-center gap-2 text-xs">
                                    <X className="w-3 h-3" />
                                    <span className="font-mono">{filename}</span>
                                </div>
                            ))}
                        </div>
                        <p className="mt-2 text-xs opacity-80">
                            Supported formats: {getSupportedFormatsDisplay()}
                        </p>
                    </div>
                    <button
                        onClick={() => setUnsupportedFiles([])}
                        className="text-orange-600 hover:text-orange-800 shrink-0"
                        aria-label="Dismiss"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>
            )}

            {error && (
                <div className={cn(
                    "mt-2 text-xs flex items-start gap-2 p-2 rounded-lg animate-in fade-in slide-in-from-top-2",
                    error.includes("already exists") || error.includes("DUPLICATE")
                        ? "bg-yellow-50 text-yellow-700 border border-yellow-200"
                        : error.includes("not supported") || error.includes("Format not supported") || error.includes("is not supported")
                            ? "bg-orange-50 text-orange-700 border border-orange-200"
                            : "bg-red-50 text-red-700 border border-red-200"
                )}>
                    <AlertCircle className={cn(
                        "w-3.5 h-3.5 shrink-0 mt-0.5",
                        error.includes("not supported") || error.includes("Format not supported") || error.includes("is not supported")
                            ? "text-orange-600"
                            : error.includes("already exists") || error.includes("DUPLICATE")
                                ? "text-yellow-600"
                                : "text-red-600"
                    )} />
                    <div className="flex-1">
                        <span className="block font-medium mb-0.5">
                            {error.includes("not supported") || error.includes("Format not supported") || error.includes("is not supported")
                                ? "Format Not Supported"
                                : error.includes("already exists") || error.includes("DUPLICATE")
                                    ? "Duplicate File"
                                    : "Upload Error"}
                        </span>
                        <span className="block break-words text-xs opacity-90">{error}</span>
                    </div>
                </div>
            )}
        </div>
    )
}
