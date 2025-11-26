import { useState, useEffect } from 'react'
import { Upload, Loader2, AlertCircle, Folder } from 'lucide-react'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { api } from '../services/api'

function cn(...inputs: (string | undefined | null | false)[]) {
    return twMerge(clsx(inputs))
}

interface UploadAreaProps {
    onUpload: (files: FileList, folder?: string) => Promise<void>
    isUploading: boolean
    error: string | null
}

export function UploadArea({ onUpload, isUploading, error }: UploadAreaProps) {
    const [isDragging, setIsDragging] = useState(false)
    const [selectedFolder, setSelectedFolder] = useState<string>('')
    const [availableFolders, setAvailableFolders] = useState<string[]>([])
    const [newFolderName, setNewFolderName] = useState('')
    const [showNewFolderInput, setShowNewFolderInput] = useState(false)

    useEffect(() => {
        loadFolders()
    }, [])

    const loadFolders = async () => {
        try {
            const response = await api.getFolders()
            setAvailableFolders(response.folders)
        } catch (err) {
            console.error("Failed to load folders", err)
        }
    }

    const handleCreateFolder = () => {
        if (newFolderName.trim()) {
            setSelectedFolder(newFolderName.trim())
            setNewFolderName('')
            setShowNewFolderInput(false)
        }
    }

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
            await onUpload(e.dataTransfer.files, selectedFolder || undefined)
            // Reload folders after upload in case a new folder was created
            await loadFolders()
        }
    }

    const handleFileInput = async (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files?.length) {
            await onUpload(e.target.files, selectedFolder || undefined)
            // Reload folders after upload in case a new folder was created
            await loadFolders()
        }
    }

    return (
        <div className="p-4">
            {/* Folder Selection */}
            <div className="mb-3">
                <label className="block text-xs font-semibold text-slate-600 mb-1.5 flex items-center gap-1">
                    <Folder className="w-3 h-3" />
                    Folder (Optional)
                </label>
                <div className="flex gap-2">
                    <select
                        value={selectedFolder}
                        onChange={(e) => setSelectedFolder(e.target.value)}
                        className="flex-1 px-3 py-1.5 text-sm border border-slate-300 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
                        disabled={isUploading}
                    >
                        <option value="">No Folder</option>
                        {availableFolders.map((folder) => (
                            <option key={folder} value={folder}>
                                {folder}
                            </option>
                        ))}
                    </select>
                    {!showNewFolderInput ? (
                        <button
                            type="button"
                            onClick={() => setShowNewFolderInput(true)}
                            className="px-3 py-1.5 text-xs text-indigo-600 hover:text-indigo-700 hover:bg-indigo-50 rounded-lg border border-indigo-200 transition-colors"
                            disabled={isUploading}
                        >
                            + New
                        </button>
                    ) : (
                        <div className="flex gap-1">
                            <input
                                type="text"
                                value={newFolderName}
                                onChange={(e) => setNewFolderName(e.target.value)}
                                onKeyPress={(e) => e.key === 'Enter' && handleCreateFolder()}
                                placeholder="Folder name"
                                className="px-2 py-1.5 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 w-32"
                                autoFocus
                            />
                            <button
                                type="button"
                                onClick={handleCreateFolder}
                                className="px-2 py-1.5 text-xs bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
                            >
                                Add
                            </button>
                            <button
                                type="button"
                                onClick={() => {
                                    setShowNewFolderInput(false)
                                    setNewFolderName('')
                                }}
                                className="px-2 py-1.5 text-xs bg-slate-200 text-slate-700 rounded-lg hover:bg-slate-300"
                            >
                                Cancel
                            </button>
                        </div>
                    )}
                </div>
            </div>

            {/* Upload Area */}
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
                            {selectedFolder && (
                                <p className="text-xs text-indigo-600 mt-1 font-medium">
                                    → {selectedFolder}
                                </p>
                            )}
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
