import { useState, useEffect, useCallback } from 'react'
import { Document } from '../types'
import { api } from '../services/api'
import { calculateFileChecksum } from '../utils/checksum'

export function useDocuments() {
    const [documents, setDocuments] = useState<Document[]>([])
    const [folders, setFolders] = useState<string[]>([])
    const [selectedDoc, setSelectedDoc] = useState<Document | null>(null)
    const [isUploading, setIsUploading] = useState(false)
    const [uploadError, setUploadError] = useState<string | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [uploadProgress, setUploadProgress] = useState<Map<string, number>>(new Map())

    const fetchDocuments = useCallback(async () => {
        try {
            const docs = await api.getDocuments()
            // Fetch folders list to ensure empty folders are included
            const foldersResponse = await api.getFolders()
            setFolders(foldersResponse.folders || [])

            // Merge with existing documents to preserve upload progress
            setDocuments(prevDocs => {
                return docs.map(doc => {
                    const existing = prevDocs.find(d => d.id === doc.id)
                    // Preserve upload progress if document is still uploading/processing
                    if (existing && (existing.status === 'uploading' || existing.status === 'processing')) {
                        return { ...doc, uploadProgress: existing.uploadProgress, size: doc.size ?? existing.size }
                    }
                    return doc
                })
            })

            // Update selected doc if it exists in the new list to keep status updated
            setSelectedDoc(prevSelected => {
                if (!prevSelected) return null
                const updated = docs.find(d => d.id === prevSelected.id)
                return updated || prevSelected
            })
        } catch (err) {
            console.error("Failed to fetch documents", err)
        } finally {
            setIsLoading(false)
        }
    }, [])

    useEffect(() => {
        fetchDocuments()
        const interval = setInterval(fetchDocuments, 5000)
        return () => clearInterval(interval)
    }, [fetchDocuments])

    const handleUpload = async (files: FileList, folder?: string | ((file: File) => string | undefined)) => {
        setIsUploading(true)
        setUploadError(null)
        const progressMap = new Map<string, number>()
        const filenameToDocIdMap = new Map<string, string>()
        const tempDocIds: string[] = []
        const duplicateFiles: string[] = []

        // Check for duplicates before uploading
        const fileArray = Array.from(files)
        for (const file of fileArray) {
            try {
                const checksum = await calculateFileChecksum(file)
                const duplicateCheck = await api.checkDuplicate(checksum)
                if (duplicateCheck.is_duplicate) {
                    duplicateFiles.push(file.name)
                    continue
                }
            } catch (err) {
                console.error(`Error checking duplicate for ${file.name}:`, err)
                // Continue with upload if check fails
            }
        }

        // Show duplicate message if any
        if (duplicateFiles.length > 0) {
            const duplicateMsg = duplicateFiles.length === 1
                ? `File "${duplicateFiles[0]}" already exists and was skipped.`
                : `${duplicateFiles.length} files already exist and were skipped: ${duplicateFiles.join(', ')}`
            setUploadError(duplicateMsg)

            // Filter out duplicate files
            const uniqueFiles = fileArray.filter(file => !duplicateFiles.includes(file.name))
            if (uniqueFiles.length === 0) {
                setIsUploading(false)
                return
            }
            // Create FileList from unique files
            const dataTransfer = new DataTransfer()
            uniqueFiles.forEach(file => dataTransfer.items.add(file))
            files = dataTransfer.files
        }

        // Create temporary document entries for immediate UI feedback
        Array.from(files).forEach((file, index) => {
            const tempId = `temp-${Date.now()}-${index}`
            tempDocIds.push(tempId)
            filenameToDocIdMap.set(file.name, tempId)
            progressMap.set(tempId, 0)

            // Get folder path for this file
            const fileFolder = typeof folder === 'function' ? folder(file) : folder

            // Add temporary document to list
            const uploadTime = new Date().toISOString()
            const tempDoc: Document = {
                id: tempId,
                filename: file.name,
                upload_date: uploadTime,
                file_path: '',
                status: 'uploading',
                uploadProgress: 0,
                folder: fileFolder || undefined,
                size: file.size,
                modified_date: uploadTime
            }
            setDocuments(prev => [...prev, tempDoc])
        })
        setUploadProgress(new Map(progressMap))

        try {
            const uploadedDocs = await api.uploadFiles(files, folder, (fileId, progress) => {
                // Update progress - fileId could be filename (during upload) or doc.id (after response)
                const docId = filenameToDocIdMap.get(fileId) || fileId
                progressMap.set(docId, progress)
                setUploadProgress(new Map(progressMap))

                // Update temporary document progress
                setDocuments(prev => prev.map(doc => {
                    if (doc.id === docId) {
                        return { ...doc, uploadProgress: progress }
                    }
                    return doc
                }))
            })

            // Replace temporary documents with real ones
            // Note: ZIP files may return more documents than original files (due to extraction)
            uploadedDocs.forEach((doc, index) => {
                // For ZIP files, there may be more docs than temp IDs
                // Use the doc's own ID for progress tracking
                const docId = doc.id
                
                // Try to find matching temp ID if available
                if (index < tempDocIds.length) {
                    const tempId = tempDocIds[index]
                    const file = Array.from(files)[index]
                    if (file && tempId) {
                        filenameToDocIdMap.set(file.name, docId)
                        // Transfer progress from tempId to doc.id
                        const fileProgress = progressMap.get(tempId) || 100
                        progressMap.delete(tempId)
                        progressMap.set(docId, fileProgress)
                    }
                } else {
                    // For extracted files from ZIP, set progress directly
                    progressMap.set(docId, 100)
                }

                setDocuments(prev => {
                    // Remove temporary document if it exists, then add/update real one
                    const filtered = index < tempDocIds.length 
                        ? prev.filter(d => d.id !== tempDocIds[index])
                        : prev
                    
                    const exists = filtered.find(d => d.id === docId)
                    if (exists) {
                        return filtered.map(d =>
                            d.id === docId
                                ? { ...doc, status: 'processing' as const, uploadProgress: 100 }
                                : d
                        )
                    }
                    return [...filtered, { ...doc, status: 'processing' as const, uploadProgress: 100 }]
                })
            })
            
            // Clean up any remaining temp IDs that weren't matched
            tempDocIds.forEach((tempId, index) => {
                if (index >= uploadedDocs.length) {
                    progressMap.delete(tempId)
                    setDocuments(prev => prev.filter(d => d.id !== tempId))
                }
            })

            setUploadProgress(new Map(progressMap))

            // Clear progress after a short delay
            setTimeout(() => {
                setUploadProgress(new Map())
            }, 2000)

            await fetchDocuments()
        } catch (err: any) {
            console.error("Upload failed", err)
            // Handle duplicate error specifically
            if (err.response?.status === 409 || err.message?.includes('already exists') || err.message?.startsWith('DUPLICATE:')) {
                const duplicateMsg = err.response?.data?.detail || err.message?.replace('DUPLICATE: ', '') || 'File already exists'
                setUploadError(duplicateMsg)
            } else {
                setUploadError("Failed to upload files.")
            }
            // Remove temporary documents on error
            setDocuments(prev => prev.filter(d => !tempDocIds.includes(d.id)))
            setUploadProgress(new Map())
        } finally {
            setIsUploading(false)
        }
    }

    const handleDelete = async (docId: string) => {
        if (!window.confirm("Are you sure you want to delete this document?")) return

        try {
            await api.deleteDocument(docId)
            setDocuments(prev => prev.filter(d => d.id !== docId))
            if (selectedDoc?.id === docId) {
                setSelectedDoc(null)
            }
        } catch (err) {
            console.error("Delete failed", err)
            alert("Failed to delete document")
        }
    }

    /**
     * Deletes a folder and all its contents (including subfolders).
     * Shows confirmation dialog before deletion.
     * 
     * @param folderPath - The folder path to delete
     */
    const handleDeleteFolder = async (folderPath: string) => {
        // Count all documents in this folder and subfolders
        const folderDocs = documents.filter(doc =>
            doc.folder === folderPath ||
            (doc.folder && doc.folder.startsWith(`${folderPath}/`))
        )
        const count = folderDocs.length

        // Show confirmation dialog with item count
        if (!window.confirm(`Are you sure you want to delete this folder?\n\nThis will delete ${count} ${count === 1 ? 'item' : 'items'} including all files and subfolders.`)) {
            return
        }

        try {
            await api.deleteFolder(folderPath)

            // Remove all documents in this folder from state immediately
            // This provides instant UI feedback before server refresh
            setDocuments(prev => prev.filter(doc =>
                doc.folder !== folderPath &&
                !(doc.folder && doc.folder.startsWith(`${folderPath}/`))
            ))

            // Remove deleted folder and all subfolders from folders state immediately
            setFolders(prev => prev.filter(folder =>
                folder !== folderPath &&
                !(folder && folder.startsWith(`${folderPath}/`))
            ))

            // Clear selected doc if it was in the deleted folder
            if (selectedDoc && (selectedDoc.folder === folderPath || (selectedDoc.folder && selectedDoc.folder.startsWith(`${folderPath}/`)))) {
                setSelectedDoc(null)
            }

            // Refresh documents and folders from server to ensure consistency
            // This ensures the tree view is updated with the latest state
            await fetchDocuments()
        } catch (err: any) {
            console.error("Delete folder failed", err)
            const errorMsg = err.response?.data?.detail || err.message || "Failed to delete folder"
            alert(errorMsg)
            throw err // Re-throw so caller can handle it
        }
    }


    /**
     * Creates a new folder. Since folders are virtual (metadata only),
     * this validates the folder name and stores it in the database.
     * The folder will appear in the tree immediately after creation.
     * 
     * @param folderName - Name of the folder to create
     * @param parentFolder - Optional parent folder path (for nested folders)
     */
    const handleCreateFolder = async (folderName: string, parentFolder?: string | null) => {
        try {
            const result = await api.createFolder(folderName, parentFolder)
            // Refresh documents and folders to ensure consistency
            await fetchDocuments()
            // Show success message
            alert(`Folder "${result.folder_path}" created successfully!`)
        } catch (err: any) {
            console.error("Create folder failed in hook", err)
            const errorMsg = err.message || "Failed to create folder"
            alert(`Error: ${errorMsg}`)
            throw err
        }
    }

    return {
        documents,
        folders,
        selectedDoc,
        setSelectedDoc,
        isUploading,
        uploadError,
        handleUpload,
        handleDelete,
        handleDeleteFolder,
        handleCreateFolder,
        isLoading,
        uploadProgress
    }
}
