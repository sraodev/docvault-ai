import axios from 'axios'
import { Document } from '../types'

const API_URL = 'http://localhost:8000'

export const api = {
    getDocuments: async (): Promise<Document[]> => {
        try {
            const res = await axios.get(`${API_URL}/documents`)
            return res.data
        } catch (error) {
            console.error("Error fetching documents:", error)
            throw new Error("Failed to fetch documents. Please try again later.")
        }
    },

    getDocument: async (id: string): Promise<Document> => {
        try {
            const res = await axios.get(`${API_URL}/documents/${id}`)
            return res.data
        } catch (error) {
            console.error(`Error fetching document ${id}:`, error)
            throw new Error("Failed to load document details.")
        }
    },

    deleteDocument: async (id: string): Promise<void> => {
        try {
            await axios.delete(`${API_URL}/documents/${id}`)
        } catch (error) {
            console.error(`Error deleting document ${id}:`, error)
            throw new Error("Failed to delete document.")
        }
    },

    checkDuplicate: async (checksum: string): Promise<{ is_duplicate: boolean; filename?: string; document_id?: string }> => {
        try {
            const formData = new FormData()
            formData.append('checksum', checksum)
            const res = await axios.post(`${API_URL}/upload/check-duplicate`, formData)
            return res.data
        } catch (error) {
            console.error("Error checking duplicate:", error)
            return { is_duplicate: false }
        }
    },

    uploadFiles: async (
        files: FileList,
        folder?: string | ((file: File) => string | undefined),
        onProgress?: (fileId: string, progress: number) => void
    ): Promise<Document[]> => {
        try {
            const fileArray = Array.from(files)
            const uploadedDocs: Document[] = []

            for (const file of fileArray) {
                const formData = new FormData()
                formData.append('file', file)

                // Handle folder: can be a string or a function that returns folder path per file
                let fileFolder: string | undefined
                if (typeof folder === 'function') {
                    fileFolder = folder(file)
                } else {
                    fileFolder = folder
                }

                if (fileFolder) {
                    formData.append('folder', fileFolder)
                }

                const response = await axios.post<Document>(`${API_URL}/upload`, formData, {
                    onUploadProgress: (progressEvent) => {
                        if (progressEvent.total && onProgress) {
                            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
                            // Use filename as temporary ID until we get the response
                            onProgress(file.name, progress)
                        }
                    }
                })

                uploadedDocs.push(response.data)
                // Notify 100% completion
                if (onProgress) {
                    onProgress(response.data.id, 100)
                }
            }

            return uploadedDocs
        } catch (error: any) {
            console.error("Error uploading files:", error)
            // Handle duplicate file error
            if (error.response?.status === 409 && error.response?.data?.error === 'duplicate_file') {
                throw new Error(`DUPLICATE: ${error.response.data.message}`)
            }
            throw new Error("Failed to upload files. Please check your connection and try again.")
        }
    },

    getFolders: async (): Promise<{ folders: string[] }> => {
        try {
            const res = await axios.get(`${API_URL}/documents/folders/list`)
            return res.data
        } catch (error) {
            console.error("Error fetching folders:", error)
            return { folders: [] }
        }
    },

    getDocumentsByFolder: async (folder?: string): Promise<Document[]> => {
        try {
            const params = folder ? { folder } : {}
            const res = await axios.get(`${API_URL}/documents`, { params })
            return res.data
        } catch (error) {
            console.error("Error fetching documents by folder:", error)
            throw new Error("Failed to fetch documents.")
        }
    },

    getFileContent: async (filename: string): Promise<string> => {
        try {
            const res = await axios.get(`${API_URL}/files/${filename}`)
            return res.data
        } catch (error) {
            console.error(`Error fetching file content ${filename}:`, error)
            throw new Error("Failed to load file content.")
        }
    },

    getApiUrl: () => API_URL
}
