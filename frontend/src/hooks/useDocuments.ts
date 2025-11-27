import { useState, useEffect, useCallback } from 'react'
import { Document } from '../types'
import { api } from '../services/api'
import { calculateFileChecksum } from '../utils/checksum'

export function useDocuments() {
    const [documents, setDocuments] = useState<Document[]>([])
    const [selectedDoc, setSelectedDoc] = useState<Document | null>(null)
    const [isUploading, setIsUploading] = useState(false)
    const [uploadError, setUploadError] = useState<string | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [uploadProgress, setUploadProgress] = useState<Map<string, number>>(new Map())

    const fetchDocuments = useCallback(async () => {
        try {
            const docs = await api.getDocuments()

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
            if (selectedDoc) {
                const updated = docs.find(d => d.id === selectedDoc.id)
                if (updated) setSelectedDoc(updated)
            }
        } catch (err) {
            console.error("Failed to fetch documents", err)
        } finally {
            setIsLoading(false)
        }
    }, [selectedDoc])

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
            const tempDoc: Document = {
                id: tempId,
                filename: file.name,
                upload_date: new Date().toISOString(),
                file_path: '',
                status: 'uploading',
                uploadProgress: 0,
                folder: fileFolder || undefined,
                size: file.size
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
            uploadedDocs.forEach((doc, index) => {
                const tempId = tempDocIds[index]
                const file = Array.from(files)[index]
                if (file && tempId) {
                    filenameToDocIdMap.set(file.name, doc.id)
                    // Transfer progress from tempId to doc.id
                    const fileProgress = progressMap.get(tempId) || 100
                    progressMap.delete(tempId)
                    progressMap.set(doc.id, fileProgress)
                }

                setDocuments(prev => {
                    // Remove temporary document and add real one
                    const filtered = prev.filter(d => d.id !== tempId)
                    const exists = filtered.find(d => d.id === doc.id)
                    if (exists) {
                        return filtered.map(d =>
                            d.id === doc.id
                                ? { ...doc, status: 'processing' as const, uploadProgress: 100 }
                                : d
                        )
                    }
                    return [...filtered, { ...doc, status: 'processing' as const, uploadProgress: 100 }]
                })
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

    return {
        documents,
        selectedDoc,
        setSelectedDoc,
        isUploading,
        uploadError,
        handleUpload,
        handleDelete,
        isLoading,
        uploadProgress
    }
}
