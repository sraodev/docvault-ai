import axios from 'axios'
import { Document } from '../types'
import { extractFilename } from '../utils/filename'

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
                
                // Extract just the filename (remove any path that might be in file.name)
                const cleanFilename = extractFilename(file.name)
                // Create a new File object with clean filename to ensure backend receives only filename
                const fileWithCleanName = new File([file], cleanFilename, { type: file.type })
                
                formData.append('file', fileWithCleanName)

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
                            // Use clean filename as temporary ID until we get the response
                            onProgress(cleanFilename, progress)
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

    deleteFolder: async (folderPath: string): Promise<{ message: string; deleted_count: number }> => {
        try {
            const encodedPath = encodeURIComponent(folderPath)
            const res = await axios.delete(`${API_URL}/documents/folders/${encodedPath}`)
            return res.data
        } catch (error: any) {
            console.error(`Error deleting folder ${folderPath}:`, error)
            const errorMsg = error.response?.data?.detail || error.message || "Failed to delete folder."
            throw new Error(errorMsg)
        }
    },

    moveFolder: async (folderPath: string, newFolderPath: string | null): Promise<{ message: string; moved_count: number }> => {
        try {
            const formData = new FormData()
            if (newFolderPath) {
                formData.append('new_folder_path', newFolderPath)
            }
            const res = await axios.put(`${API_URL}/documents/folders/${encodeURIComponent(folderPath)}/move`, formData)
            return res.data
        } catch (error) {
            console.error(`Error moving folder ${folderPath}:`, error)
            throw new Error("Failed to move folder.")
        }
    },

    createFolder: async (folderName: string, parentFolder?: string | null): Promise<{ message: string; folder_path: string; folder_name: string }> => {
        try {
            console.log("API: Creating folder", folderName, "parent:", parentFolder)
            const formData = new FormData()
            formData.append('folder_name', folderName)
            if (parentFolder && parentFolder.trim()) {
                formData.append('parent_folder', parentFolder.trim())
            }
            console.log("API: Sending POST request to", `${API_URL}/documents/folders`)
            const res = await axios.post(`${API_URL}/documents/folders`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            })
            console.log("API: Folder created successfully", res.data)
            return res.data
        } catch (error: any) {
            console.error(`Error creating folder ${folderName}:`, error)
            console.error("Error response:", error.response?.data)
            console.error("Error status:", error.response?.status)
            const errorMsg = error.response?.data?.detail || error.response?.data?.message || error.message || "Failed to create folder."
            throw new Error(errorMsg)
        }
    },

    getApiUrl: () => API_URL
}
