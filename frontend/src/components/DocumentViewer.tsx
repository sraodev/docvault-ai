import { useState, useEffect } from 'react'
import { FileText, File, Loader2, ChevronRight, Archive, Folder, X } from 'lucide-react'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { Document } from '../types'
import { api } from '../services/api'
import { extractFilename } from '../utils/filename'

function cn(...inputs: (string | undefined | null | false)[]) {
    return twMerge(clsx(inputs))
}

interface DocumentViewerProps {
    document: Document | null
    onClose?: () => void
    onNavigateToFolder?: (folder: string | null) => void
}

export function DocumentViewer({ document, onClose, onNavigateToFolder }: DocumentViewerProps) {
    const [activeTab, setActiveTab] = useState<'original' | 'summary' | 'markdown' | 'tags'>('original')
    const [markdownContent, setMarkdownContent] = useState<string>('')
    const [isProcessing, setIsProcessing] = useState(false)
    const [currentDocument, setCurrentDocument] = useState(document)

    // Update current document when prop changes
    useEffect(() => {
        setCurrentDocument(document)
    }, [document])

    // Poll for document updates when processing
    useEffect(() => {
        if (!currentDocument || currentDocument.status !== 'processing') return

        const pollInterval = setInterval(async () => {
            try {
                const updatedDoc = await api.getDocument(currentDocument.id)
                setCurrentDocument(updatedDoc)
                if (updatedDoc.status === 'completed' || updatedDoc.status === 'ready') {
                    setIsProcessing(false)
                    clearInterval(pollInterval)
                }
            } catch (error) {
                console.error('Failed to fetch document update:', error)
            }
        }, 2000) // Poll every 2 seconds when processing

        return () => clearInterval(pollInterval)
    }, [currentDocument?.id, currentDocument?.status])

    // Trigger AI processing when document is viewed and status is "ready"
    useEffect(() => {
        if (currentDocument && currentDocument.status === 'ready' && !isProcessing) {
            setIsProcessing(true)
            api.processDocument(currentDocument.id)
                .catch((error) => {
                    console.error('Failed to start AI processing:', error)
                    setIsProcessing(false)
                })
        }
    }, [currentDocument?.id, currentDocument?.status, isProcessing])

    useEffect(() => {
        if (currentDocument?.status === 'completed' && activeTab === 'markdown') {
            fetchMarkdown(currentDocument)
        }
    }, [currentDocument, activeTab])

    const fetchMarkdown = async (doc: Document) => {
        if (!doc.markdown_path) return
        try {
            const filename = extractFilename(doc.markdown_path)
            if (!filename) return

            const content = await api.getFileContent(filename)
            setMarkdownContent(content)
        } catch (err) {
            console.error("Failed to fetch markdown", err)
            setMarkdownContent("Error loading markdown.")
        }
    }

    if (!currentDocument) {
        return (
            <div className="flex-1 flex flex-col items-center justify-center text-slate-400">
                <div className="w-24 h-24 bg-slate-100 rounded-full flex items-center justify-center mb-6">
                    <FileText className="w-10 h-10 text-slate-300" />
                </div>
                <p className="text-lg font-medium text-slate-500">Select a document to view</p>
                <p className="text-sm mt-2">or upload a new one to get started</p>
            </div>
        )
    }

    // Build folder breadcrumb path
    const folderBreadcrumbs = currentDocument.folder ? currentDocument.folder.split('/') : []

    return (
        <div className="flex-1 flex flex-col h-full overflow-hidden bg-gradient-to-br from-white via-slate-50/30 to-blue-50/20">
            {/* Breadcrumbs */}
            <div className="h-[76px] px-6 bg-gradient-to-r from-blue-50 via-indigo-50/50 to-purple-50/30 border-b border-slate-200/80 flex items-center justify-between shadow-soft backdrop-blur-sm">
                <nav className="flex items-center gap-2 text-sm">
                    {onClose ? (
                        <button
                            onClick={onClose}
                            className="flex items-center gap-2 text-slate-600 hover:text-primary-600 transition-all duration-200 px-2 py-1 rounded-lg hover:bg-white/60 group"
                        >
                            <Archive className="w-4 h-4 group-hover:scale-110 transition-transform" />
                            <span className="font-medium">My Vault</span>
                        </button>
                    ) : (
                        <button className="flex items-center gap-2 text-slate-600 hover:text-primary-600 transition-all duration-200 px-2 py-1 rounded-lg hover:bg-white/60">
                            <Archive className="w-4 h-4" />
                            <span className="font-medium">My Vault</span>
                        </button>
                    )}
                    {folderBreadcrumbs.map((folderPart, index) => {
                        const folderPath = folderBreadcrumbs.slice(0, index + 1).join('/')
                        return (
                            <div key={folderPath} className="flex items-center gap-2">
                                <ChevronRight className="w-4 h-4 text-slate-400" />
                                {onNavigateToFolder ? (
                                    <button
                                        onClick={() => onNavigateToFolder(folderPath)}
                                        className="flex items-center gap-2 text-slate-600 hover:text-primary-600 transition-all duration-200 px-2 py-1 rounded-lg hover:bg-white/60"
                                    >
                                        {index === 0 && <Folder className="w-4 h-4" />}
                                        <span className="truncate max-w-[200px] font-medium">{folderPart}</span>
                                    </button>
                                ) : (
                                    <span className="flex items-center gap-2 text-slate-500">
                                        {index === 0 && <Folder className="w-4 h-4" />}
                                        <span className="truncate max-w-[200px] font-medium">{folderPart}</span>
                                    </span>
                                )}
                            </div>
                        )
                    })}
                    <ChevronRight className="w-4 h-4 text-slate-400" />
                    <span className="flex items-center gap-2 text-slate-900 font-semibold truncate max-w-[300px]">
                        <File className="w-4 h-4 shrink-0" />
                        <span className="truncate" title={currentDocument.filename}>{extractFilename(currentDocument.filename)}</span>
                    </span>
                </nav>
                {onClose && (
                    <button
                        onClick={onClose}
                        className="p-2 rounded-xl hover:bg-white/80 transition-all hover:shadow-soft group"
                        title="Close"
                    >
                        <X className="w-5 h-5 text-slate-600 group-hover:text-primary-600 transition-colors" />
                    </button>
                )}
            </div>

            <div className="h-16 border-b border-slate-200/80 bg-white/80 backdrop-blur-sm flex items-center justify-between px-6 shadow-soft">
                <div className="flex items-center gap-3 overflow-hidden flex-1">
                    <h2 className="font-bold text-lg truncate text-slate-900">{extractFilename(currentDocument.filename)}</h2>
                    <span className="px-3 py-1 rounded-lg text-xs font-semibold bg-gradient-to-r from-primary-50 to-indigo-50 text-primary-700 border border-primary-200 uppercase shrink-0">
                        {extractFilename(currentDocument.filename).split('.').pop() || 'FILE'}
                    </span>
                    {currentDocument.status === 'completed' && currentDocument.summary && !currentDocument.summary.includes('Error') && (
                        <span className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-gradient-to-r from-blue-50 to-indigo-50 text-blue-700 border border-blue-200 shadow-sm shrink-0 flex items-center gap-1.5">
                            <span className="w-1.5 h-1.5 bg-blue-500 rounded-full"></span>
                            AI
                        </span>
                    )}
                </div>
                <div className="flex bg-slate-100 p-1 rounded-xl border-2 border-slate-200">
                    {(['original', 'summary', 'markdown', 'tags'] as const).map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={cn(
                                "px-5 py-2 text-sm font-semibold rounded-lg transition-all duration-200",
                                activeTab === tab ? "bg-gradient-to-r from-primary-600 to-indigo-600 text-white shadow-md" : "text-slate-600 hover:text-slate-900 hover:bg-white/50"
                            )}
                        >
                            {tab.charAt(0).toUpperCase() + tab.slice(1)}
                        </button>
                    ))}
                </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6 bg-gradient-to-br from-slate-50/50 via-white to-blue-50/30">
                <div className="max-w-4xl mx-auto bg-white rounded-2xl shadow-medium border border-slate-200 min-h-[500px] p-8">
                    {activeTab === 'original' && (
                        <div className="h-full flex flex-col items-center justify-center text-slate-400">
                            <File className="w-16 h-16 mb-4 opacity-20" />
                            <p>Original File Content</p>
                            {currentDocument.file_path ? (
                                <a
                                    href={`${api.getApiUrl()}/files/${extractFilename(currentDocument.file_path)}`}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="mt-4 text-blue-600 hover:text-blue-700 hover:underline text-sm font-medium transition-colors"
                                >
                                    Open/Download Original File
                                </a>
                            ) : (
                                <span className="mt-4 text-xs text-slate-400">File path not available</span>
                            )}
                        </div>
                    )}

                    {activeTab === 'summary' && (
                        <div className="prose prose-slate max-w-none">
                            <div className="flex items-center gap-3 mb-4">
                                <h3 className="text-lg font-semibold text-slate-800">Summary</h3>
                                {currentDocument.status === 'completed' && currentDocument.summary && !currentDocument.summary.includes('Error') && (
                                    <span className="px-3 py-1 rounded-lg text-xs font-semibold bg-gradient-to-r from-blue-50 to-indigo-50 text-blue-700 border border-blue-200 shadow-sm flex items-center gap-1.5">
                                        <span className="w-1.5 h-1.5 bg-blue-500 rounded-full"></span>
                                        AI Generated
                                    </span>
                                )}
                            </div>
                            {currentDocument.status === 'processing' || (currentDocument.status === 'ready' && isProcessing) ? (
                                <div className="flex items-center gap-2 text-slate-500 animate-pulse">
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    Generating summary...
                                </div>
                            ) : currentDocument.status === 'ready' ? (
                                <div className="flex flex-col items-center gap-2 text-slate-500">
                                    <p className="text-slate-400 italic">AI processing not started yet. Click to view to trigger processing.</p>
                                </div>
                            ) : currentDocument.summary && !currentDocument.summary.includes('Error generating summary') && !currentDocument.summary.includes('Error code:') ? (
                                <p className="text-slate-600 leading-relaxed whitespace-pre-wrap">{currentDocument.summary}</p>
                            ) : (
                                <div className="flex flex-col items-center justify-center py-8 text-slate-400">
                                    <FileText className="w-12 h-12 mb-3 text-slate-300" />
                                    <p className="text-slate-500 font-medium mb-1">AI Summary Unavailable</p>
                                    <p className="text-sm text-slate-400 text-center max-w-md">
                                        The AI service is currently unavailable. You can still view and download the original document.
                                    </p>
                                </div>
                            )}
                        </div>
                    )}

                    {activeTab === 'markdown' && (
                        <div className="prose prose-slate max-w-none">
                            <h3 className="text-lg font-semibold mb-4 text-slate-800">Markdown View</h3>
                            {currentDocument.status === 'processing' || (currentDocument.status === 'ready' && isProcessing) ? (
                                <div className="flex items-center gap-2 text-slate-500 animate-pulse">
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    Converting to markdown...
                                </div>
                            ) : currentDocument.status === 'ready' ? (
                                <div className="flex flex-col items-center gap-2 text-slate-500">
                                    <p className="text-slate-400 italic">AI processing not started yet. Click to view to trigger processing.</p>
                                </div>
                            ) : markdownContent && !markdownContent.includes('Error') && !markdownContent.includes('Error code:') ? (
                                <pre className="bg-slate-50 p-4 rounded-lg overflow-x-auto text-sm font-mono text-slate-700 whitespace-pre-wrap">
                                    {markdownContent}
                                </pre>
                            ) : (
                                <div className="flex flex-col items-center justify-center py-8 text-slate-400">
                                    <FileText className="w-12 h-12 mb-3 text-slate-300" />
                                    <p className="text-slate-500 font-medium mb-1">Markdown View Unavailable</p>
                                    <p className="text-sm text-slate-400 text-center max-w-md">
                                        The AI service is currently unavailable. You can still view and download the original document.
                                    </p>
                                </div>
                            )}
                        </div>
                    )}

                    {activeTab === 'tags' && (
                        <div className="prose prose-slate max-w-none">
                            <div className="flex items-center gap-3 mb-6">
                                <h3 className="text-lg font-semibold text-slate-800">Tags</h3>
                                {currentDocument.status === 'completed' && currentDocument.tags && currentDocument.tags.length > 0 && (
                                    <span className="px-3 py-1 rounded-lg text-xs font-semibold bg-gradient-to-r from-blue-50 to-indigo-50 text-blue-700 border border-blue-200 shadow-sm flex items-center gap-1.5">
                                        <span className="w-1.5 h-1.5 bg-blue-500 rounded-full"></span>
                                        {currentDocument.tags.length} {currentDocument.tags.length === 1 ? 'Tag' : 'Tags'}
                                    </span>
                                )}
                            </div>
                            {currentDocument.status === 'processing' || (currentDocument.status === 'ready' && isProcessing) ? (
                                <div className="flex items-center gap-2 text-slate-500 animate-pulse">
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    Extracting tags...
                                </div>
                            ) : currentDocument.status === 'ready' ? (
                                <div className="flex flex-col items-center gap-2 text-slate-500">
                                    <p className="text-slate-400 italic">AI processing not started yet. Click to view to trigger processing.</p>
                                </div>
                            ) : currentDocument.tags && currentDocument.tags.length > 0 ? (
                                <div className="flex flex-wrap gap-2">
                                    {currentDocument.tags.map((tag, idx) => (
                                        <span
                                            key={idx}
                                            className="px-3 py-1.5 rounded-lg text-sm font-medium bg-gradient-to-r from-blue-50 to-indigo-50 text-blue-700 border border-blue-200 hover:border-blue-300 hover:shadow-sm transition-all cursor-default"
                                        >
                                            {tag}
                                        </span>
                                    ))}
                                </div>
                            ) : (
                                <div className="flex flex-col items-center justify-center py-8 text-slate-400">
                                    <FileText className="w-12 h-12 mb-3 text-slate-300" />
                                    <p className="text-slate-500 font-medium mb-1">No Tags Available</p>
                                    <p className="text-sm text-slate-400 text-center max-w-md">
                                        Tags will be automatically extracted from the document content after AI processing completes.
                                    </p>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
