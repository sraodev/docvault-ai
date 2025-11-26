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

    uploadFiles: async (files: FileList, folder?: string): Promise<void> => {
        try {
            const fileArray = Array.from(files)
            for (const file of fileArray) {
                const formData = new FormData()
                formData.append('file', file)
                if (folder) {
                    formData.append('folder', folder)
                }
                await axios.post(`${API_URL}/upload`, formData)
            }
        } catch (error) {
            console.error("Error uploading files:", error)
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
