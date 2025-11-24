import { useState, useEffect, useCallback } from 'react'
import { Document } from '../types'
import { api } from '../services/api'

export function useDocuments() {
    const [documents, setDocuments] = useState<Document[]>([])
    const [selectedDoc, setSelectedDoc] = useState<Document | null>(null)
    const [isUploading, setIsUploading] = useState(false)
    const [uploadError, setUploadError] = useState<string | null>(null)
    const [isLoading, setIsLoading] = useState(true)

    const fetchDocuments = useCallback(async () => {
        try {
            const docs = await api.getDocuments()
            setDocuments(docs)

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

    const handleUpload = async (files: FileList) => {
        setIsUploading(true)
        setUploadError(null)
        try {
            await api.uploadFiles(files)
            await fetchDocuments()
        } catch (err) {
            console.error("Upload failed", err)
            setUploadError("Failed to upload files.")
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
        isLoading
    }
}
