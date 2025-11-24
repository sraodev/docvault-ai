import axios from 'axios'
import { Document } from '../types'

const API_URL = 'http://localhost:8000'

export const api = {
    getDocuments: async (): Promise<Document[]> => {
        const res = await axios.get(`${API_URL}/documents`)
        return res.data
    },

    getDocument: async (id: string): Promise<Document> => {
        const res = await axios.get(`${API_URL}/documents/${id}`)
        return res.data
    },

    deleteDocument: async (id: string): Promise<void> => {
        await axios.delete(`${API_URL}/documents/${id}`)
    },

    uploadFiles: async (files: FileList): Promise<void> => {
        const fileArray = Array.from(files)
        for (const file of fileArray) {
            const formData = new FormData()
            formData.append('file', file)
            await axios.post(`${API_URL}/upload`, formData)
        }
    },

    getFileContent: async (filename: string): Promise<string> => {
        const res = await axios.get(`${API_URL}/files/${filename}`)
        return res.data
    },

    getApiUrl: () => API_URL
}
