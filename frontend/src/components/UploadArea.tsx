import { useState } from 'react'
import { Upload, Loader2, AlertCircle } from 'lucide-react'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

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

            // Check for ZIP files - backend will extract and create folder structure
            const hasZipFiles = files.some(file => {
                const ext = file.name.split('.').pop()?.toLowerCase()
                return ext === 'zip'
            })

            if (hasZipFiles) {
                // Handle ZIP files - backend will extract and create folders
                await onUpload(e.dataTransfer.files)
            } else {
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
    }

    const handleFileInput = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files?.length) {
            await onUpload(e.target.files)
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
                <input type="file" className="hidden" multiple onChange={handleFileInput} disabled={isUploading} />
            </label>
            {error && (
                <div className={cn(
                    "mt-2 text-xs flex items-start gap-2 p-2 rounded-lg",
                    error.includes("already exists") || error.includes("DUPLICATE")
                        ? "bg-yellow-50 text-yellow-700 border border-yellow-200"
                        : "bg-red-50 text-red-700 border border-red-200"
                )}>
                    <AlertCircle className="w-3.5 h-3.5 shrink-0 mt-0.5" />
                    <span className="flex-1">{error}</span>
                </div>
            )}
        </div>
    )
}
