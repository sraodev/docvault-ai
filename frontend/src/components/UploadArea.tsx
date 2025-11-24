import { useState } from 'react'
import { Upload, Loader2, AlertCircle } from 'lucide-react'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

function cn(...inputs: (string | undefined | null | false)[]) {
    return twMerge(clsx(inputs))
}

interface UploadAreaProps {
    onUpload: (files: FileList) => Promise<void>
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
            await onUpload(e.dataTransfer.files)
        }
    }

    const handleFileInput = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files?.length) {
            await onUpload(e.target.files)
        }
    }

    return (
        <div className="p-4">
            <label
                onDragOver={onDragOver}
                onDragLeave={onDragLeave}
                onDrop={onDrop}
                className={cn(
                    "flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer transition-colors",
                    isDragging ? "border-indigo-500 bg-indigo-50" : "border-slate-300 bg-slate-50 hover:bg-slate-100"
                )}
            >
                <div className="flex flex-col items-center justify-center pt-5 pb-6">
                    {isUploading ? (
                        <Loader2 className="w-8 h-8 text-indigo-500 animate-spin" />
                    ) : (
                        <>
                            <Upload className={cn("w-8 h-8 mb-3", isDragging ? "text-indigo-500" : "text-slate-400")} />
                            <p className="text-sm text-slate-500 font-medium">
                                {isDragging ? "Drop files here" : "Click or drag to upload"}
                            </p>
                            <p className="text-xs text-slate-400 mt-1">PDF, TXT, MD</p>
                        </>
                    )}
                </div>
                <input type="file" className="hidden" multiple onChange={handleFileInput} disabled={isUploading} />
            </label>
            {error && (
                <div className="mt-2 text-xs text-red-500 flex items-center gap-1">
                    <AlertCircle className="w-3 h-3" />
                    {error}
                </div>
            )}
        </div>
    )
}
