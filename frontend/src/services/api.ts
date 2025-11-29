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

    processDocument: async (id: string): Promise<{ message: string; status: string }> => {
        try {
            const res = await axios.post(`${API_URL}/documents/${id}/process`)
            return res.data
        } catch (error) {
            console.error(`Error triggering AI processing for ${id}:`, error)
            throw new Error("Failed to start AI processing.")
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

            // Use bulk upload endpoint for multiple files (more efficient)
            if (fileArray.length > 1) {
                // Call bulk upload function (defined below)
                const formData = new FormData()
                const folders: string[] = []

                // Add all files to FormData
                fileArray.forEach((file) => {
                    const cleanFilename = extractFilename(file.name)
                    const fileWithCleanName = new File([file], cleanFilename, { type: file.type })
                    formData.append('files', fileWithCleanName)

                    // Handle folder: can be a string or a function that returns folder path per file
                    let fileFolder: string | undefined
                    if (typeof folder === 'function') {
                        fileFolder = folder(file)
                    } else {
                        fileFolder = folder
                    }
                    folders.push(fileFolder || '')
                })

                // Add folders array
                folders.forEach(f => formData.append('folders', f))

                // Set concurrency based on number of files (higher for large batches)
                const concurrency = Math.min(Math.max(20, Math.ceil(fileArray.length / 10)), 50)
                formData.append('concurrency', concurrency.toString())

                const response = await axios.post<{
                    total_files: number
                    successful: number
                    failed: number
                    duplicates: number
                    document_ids: string[]
                    errors: Array<{ filename: string; error: string }>
                }>(`${API_URL}/upload/bulk`, formData, {
                    timeout: 600000, // 10 minutes timeout for large bulk uploads
                    onUploadProgress: (progressEvent) => {
                        if (progressEvent.total && onProgress) {
                            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
                            // Update progress for all files
                            fileArray.forEach((file, index) => {
                                const fileId = `temp-${index}-${file.name}`
                                onProgress(fileId, progress)
                            })
                        }
                    }
                })

                // Fetch the uploaded documents
                const uploadedDocs: Document[] = []
                for (const docId of response.data.document_ids) {
                    try {
                        const doc = await api.getDocument(docId)
                        uploadedDocs.push(doc)
                        if (onProgress) {
                            onProgress(docId, 100)
                        }
                    } catch (err) {
                        console.error(`Error fetching document ${docId}:`, err)
                    }
                }

                // Handle errors and duplicates
                if (response.data.errors.length > 0) {
                    const errorMessages = response.data.errors.map(e => `${e.filename}: ${e.error}`).join(', ')
                    console.warn('Some files failed to upload:', errorMessages)
                }

                return uploadedDocs
            }

            // Single file upload (use original endpoint)
            const formData = new FormData()
            const file = fileArray[0]
            const cleanFilename = extractFilename(file.name)
            const fileWithCleanName = new File([file], cleanFilename, { type: file.type })
            const isZipFile = cleanFilename.toLowerCase().endsWith('.zip')

            formData.append('file', fileWithCleanName)

            let fileFolder: string | undefined
            if (typeof folder === 'function') {
                fileFolder = folder(file)
            } else {
                fileFolder = folder
            }

            if (fileFolder) {
                formData.append('folder', fileFolder)
            }

            const response = await axios.post<Document | {
                message: string
                total_files: number
                created: number
                skipped: number
                errors: number
                documents: Document[]
                skipped_files: Array<{ filename: string; reason: string }>
                error_details: Array<{ filename: string; error: string }>
            }>(`${API_URL}/upload`, formData, {
                onUploadProgress: (progressEvent) => {
                    if (progressEvent.total && onProgress) {
                        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
                        onProgress(cleanFilename, progress)
                    }
                },
                timeout: 600000 // 10 minutes timeout for ZIP files (which may contain many files)
            })

            // Handle ZIP file response (returns multiple documents)
            if (isZipFile && 'documents' in response.data) {
                const zipResponse = response.data
                // Update progress for all extracted documents
                zipResponse.documents.forEach((doc) => {
                    if (onProgress) {
                        onProgress(doc.id, 100)
                    }
                })
                return zipResponse.documents
            }

            // Handle regular file response (single document)
            const doc = response.data as Document
            if (onProgress) {
                onProgress(doc.id, 100)
            }

            return [doc]
        } catch (error: any) {
            console.error("Error uploading files:", error)
            if (error.response?.status === 409 && error.response?.data?.error === 'duplicate_file') {
                throw new Error(`DUPLICATE: ${error.response.data.message}`)
            }
            throw new Error("Failed to upload files. Please check your connection and try again.")
        }
    },

    uploadFilesBulk: async (
        files: File[],
        folder?: string | ((file: File) => string | undefined),
        onProgress?: (fileId: string, progress: number) => void
    ): Promise<Document[]> => {
        try {
            const formData = new FormData()
            const folders: string[] = []

            // Add all files to FormData
            files.forEach((file) => {
                const cleanFilename = extractFilename(file.name)
                const fileWithCleanName = new File([file], cleanFilename, { type: file.type })
                formData.append('files', fileWithCleanName)

                // Handle folder: can be a string or a function that returns folder path per file
                let fileFolder: string | undefined
                if (typeof folder === 'function') {
                    fileFolder = folder(file)
                } else {
                    fileFolder = folder
                }
                folders.push(fileFolder || '')
            })

            // Add folders array
            folders.forEach(f => formData.append('folders', f))

            // Set concurrency based on number of files (higher for large batches)
            const concurrency = Math.min(Math.max(20, Math.ceil(files.length / 10)), 50)
            formData.append('concurrency', concurrency.toString())

            const response = await axios.post<{
                total_files: number
                successful: number
                failed: number
                duplicates: number
                document_ids: string[]
                errors: Array<{ filename: string; error: string }>
            }>(`${API_URL}/upload/bulk`, formData, {
                timeout: 600000, // 10 minutes timeout for large bulk uploads
                onUploadProgress: (progressEvent) => {
                    if (progressEvent.total && onProgress) {
                        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
                        // Update progress for all files
                        files.forEach((file, index) => {
                            const fileId = `temp-${index}-${file.name}`
                            onProgress(fileId, progress)
                        })
                    }
                }
            })

            // Fetch the uploaded documents
            const uploadedDocs: Document[] = []
            for (const docId of response.data.document_ids) {
                try {
                    const doc = await api.getDocument(docId)
                    uploadedDocs.push(doc)
                    if (onProgress) {
                        onProgress(docId, 100)
                    }
                } catch (err) {
                    console.error(`Error fetching document ${docId}:`, err)
                }
            }

            // Handle errors and duplicates
            if (response.data.errors.length > 0) {
                const errorMessages = response.data.errors.map(e => `${e.filename}: ${e.error}`).join(', ')
                console.warn('Some files failed to upload:', errorMessages)
            }

            return uploadedDocs
        } catch (error: any) {
            console.error("Error in bulk upload:", error)
            throw new Error(error.response?.data?.detail || "Failed to upload files. Please try again.")
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
            const formData = new FormData()
            formData.append('folder_name', folderName)
            if (parentFolder && parentFolder.trim()) {
                formData.append('parent_folder', parentFolder.trim())
            }
            const res = await axios.post(`${API_URL}/documents/folders`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data'
                }
            })
            return res.data
        } catch (error: any) {
            console.error(`Error creating folder ${folderName}:`, error)
            console.error("Error response:", error.response?.data)
            console.error("Error status:", error.response?.status)
            const errorMsg = error.response?.data?.detail || error.response?.data?.message || error.message || "Failed to create folder."
            throw new Error(errorMsg)
        }
    },

    /**
     * Get all unique AI tags across all documents.
     * Returns tags with their usage counts.
     * 
     * @returns Object containing:
     *   - tags: Array of unique tag strings (sorted by frequency, then alphabetically)
     *   - tag_counts: Object mapping tag to count of documents using it
     *   - total_tags: Total number of unique tags
     */
    getAllTags: async (): Promise<{ tags: string[]; tag_counts: Record<string, number>; total_tags: number }> => {
        try {
            const res = await axios.get(`${API_URL}/documents/tags`)
            return res.data
        } catch (error: any) {
            console.error("Error fetching tags:", error)
            const errorMsg = error.response?.data?.detail || error.message || "Failed to fetch tags."
            throw new Error(errorMsg)
        }
    },

    /**
     * Get all documents that have a specific tag.
     * Tag matching is case-insensitive.
     * 
     * @param tag - The tag to search for
     * @returns Array of documents that contain this tag
     */
    getDocumentsByTag: async (tag: string): Promise<Document[]> => {
        try {
            const encodedTag = encodeURIComponent(tag)
            const res = await axios.get(`${API_URL}/documents/tags/${encodedTag}`)
            return res.data
        } catch (error: any) {
            console.error(`Error fetching documents by tag "${tag}":`, error)
            const errorMsg = error.response?.data?.detail || error.message || "Failed to fetch documents by tag."
            throw new Error(errorMsg)
        }
    },

    /**
     * Get extracted structured fields for a document.
     * Returns fields like vendor, amount, date for invoices;
     * name, skills, experience_years, email for resumes;
     * parties_involved, start_date, end_date for contracts.
     * 
     * @param docId - The document ID
     * @returns Object containing document_id and extracted_fields
     */
    getDocumentFields: async (docId: string): Promise<{ document_id: string; extracted_fields: Record<string, any> }> => {
        try {
            const res = await axios.get(`${API_URL}/documents/${docId}/fields`)
            return res.data
        } catch (error: any) {
            console.error(`Error fetching extracted fields for document ${docId}:`, error)
            const errorMsg = error.response?.data?.detail || error.message || "Failed to fetch extracted fields."
            throw new Error(errorMsg)
        }
    },

    /**
     * AI-Based Semantic Search across all documents.
     * Uses embeddings + cosine similarity to find relevant documents.
     * 
     * Supports natural language queries like:
     * - "Find invoices above ₹50,000"
     * - "Resume containing Python senior engineer"
     * - "Contracts expiring this year"
     * 
     * @param query - Natural language search query
     * @param limit - Maximum number of results (default: 10)
     * @param minSimilarity - Minimum cosine similarity score 0.0-1.0 (default: 0.3)
     * @returns Search results with similarity scores
     */
    semanticSearch: async (
        query: string,
        limit?: number,
        minSimilarity?: number
    ): Promise<{
        query: string
        semantic_query: string
        filters_applied: Record<string, any>
        total_results: number
        returned_results: number
        results: Array<{
            document_id: string
            filename: string
            summary?: string
            folder?: string
            extracted_fields?: Record<string, any>
            similarity_score: number
            upload_date: string
        }>
    }> => {
        try {
            const params: Record<string, any> = { q: query }
            if (limit !== undefined) params.limit = limit
            if (minSimilarity !== undefined) params.min_similarity = minSimilarity
            
            const res = await axios.get(`${API_URL}/documents/search`, { params })
            return res.data
        } catch (error: any) {
            console.error(`Error in semantic search for query "${query}":`, error)
            const errorMsg = error.response?.data?.detail || error.message || "Failed to perform semantic search."
            throw new Error(errorMsg)
        }
    },

    getApiUrl: () => API_URL
}
