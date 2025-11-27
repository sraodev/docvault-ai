import { useState, useEffect } from 'react'
import { FileText, File, Loader2, ChevronRight, Home, Folder, X } from 'lucide-react'
import { clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'
import { Document } from '../types'
import { api } from '../services/api'

function cn(...inputs: (string | undefined | null | false)[]) {
    return twMerge(clsx(inputs))
}

import { extractFilename } from '../utils/filename'

interface DocumentViewerProps {
    document: Document | null
    onClose?: () => void
    onNavigateToFolder?: (folder: string | null) => void
}

export function DocumentViewer({ document, onClose, onNavigateToFolder }: DocumentViewerProps) {
    const [activeTab, setActiveTab] = useState<'original' | 'summary' | 'markdown'>('original')
    const [markdownContent, setMarkdownContent] = useState<string>('')

    useEffect(() => {
        if (document?.status === 'completed' && activeTab === 'markdown') {
            fetchMarkdown(document)
        }
    }, [document, activeTab])

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

    if (!document) {
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
    const folderBreadcrumbs = document.folder ? document.folder.split('/') : []

    return (
        <div className="flex-1 flex flex-col h-full overflow-hidden">
            {/* Breadcrumbs */}
            <div className="px-6 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between">
                <nav className="flex items-center gap-2 text-sm">
                    {onClose ? (
                        <button
                            onClick={onClose}
                            className="flex items-center gap-1 text-slate-500 hover:text-slate-700 transition-colors"
                        >
                            <Home className="w-4 h-4" />
                            <span>Documents</span>
                        </button>
                    ) : (
                        <button className="flex items-center gap-1 text-slate-500 hover:text-slate-700 transition-colors">
                            <Home className="w-4 h-4" />
                            <span>Documents</span>
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
                                        className="flex items-center gap-1 text-slate-500 hover:text-slate-700 transition-colors"
                                    >
                                        {index === 0 && <Folder className="w-4 h-4" />}
                                        <span className="truncate max-w-[200px]">{folderPart}</span>
                                    </button>
                                ) : (
                                    <span className="flex items-center gap-1 text-slate-500">
                                        {index === 0 && <Folder className="w-4 h-4" />}
                                        <span className="truncate max-w-[200px]">{folderPart}</span>
                                    </span>
                                )}
                            </div>
                        )
                    })}
                    <ChevronRight className="w-4 h-4 text-slate-400" />
                    <span className="flex items-center gap-1 text-slate-900 font-medium truncate max-w-[300px]">
                        <File className="w-4 h-4 shrink-0" />
                        <span className="truncate" title={document.filename}>{extractFilename(document.filename)}</span>
                    </span>
                </nav>
                {onClose && (
                    <button
                        onClick={onClose}
                        className="p-1.5 rounded-full hover:bg-slate-200 transition-colors"
                        title="Close"
                    >
                        <X className="w-4 h-4 text-slate-600" />
                    </button>
                )}
            </div>

            <div className="h-16 border-b border-slate-200 bg-white flex items-center justify-between px-6">
                <div className="flex items-center gap-3 overflow-hidden">
                    <h2 className="font-semibold text-lg truncate">{extractFilename(document.filename)}</h2>
                    <span className="px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600 border border-slate-200 uppercase shrink-0">
                        {extractFilename(document.filename).split('.').pop() || 'FILE'}
                    </span>
                </div>
                <div className="flex bg-slate-100 p-1 rounded-lg">
                    {(['original', 'summary', 'markdown'] as const).map((tab) => (
                        <button
                            key={tab}
                            onClick={() => setActiveTab(tab)}
                            className={cn(
                                "px-4 py-1.5 text-sm font-medium rounded-md transition-all",
                                activeTab === tab ? "bg-white text-indigo-600 shadow-sm" : "text-slate-500 hover:text-slate-700"
                            )}
                        >
                            {tab.charAt(0).toUpperCase() + tab.slice(1)}
                        </button>
                    ))}
                </div>
            </div>

            <div className="flex-1 overflow-y-auto p-6 bg-slate-50/50">
                <div className="max-w-4xl mx-auto bg-white rounded-xl shadow-sm border border-slate-200 min-h-[500px] p-8">
                    {activeTab === 'original' && (
                        <div className="h-full flex flex-col items-center justify-center text-slate-400">
                            <File className="w-16 h-16 mb-4 opacity-20" />
                            <p>Original File Content</p>
                            {document.file_path ? (
                                <a
                                    href={`${api.getApiUrl()}/files/${extractFilename(document.file_path)}`}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="mt-4 text-indigo-600 hover:underline text-sm"
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
                            <h3 className="text-lg font-semibold mb-4 text-slate-800">AI Summary</h3>
                            {document.status === 'processing' ? (
                                <div className="flex items-center gap-2 text-slate-500 animate-pulse">
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    Generating summary...
                                </div>
                            ) : document.summary ? (
                                <p className="text-slate-600 leading-relaxed whitespace-pre-wrap">{document.summary}</p>
                            ) : (
                                <p className="text-slate-400 italic">No summary available.</p>
                            )}
                        </div>
                    )}

                    {activeTab === 'markdown' && (
                        <div className="prose prose-slate max-w-none">
                            <h3 className="text-lg font-semibold mb-4 text-slate-800">Markdown View</h3>
                            {document.status === 'processing' ? (
                                <div className="flex items-center gap-2 text-slate-500 animate-pulse">
                                    <Loader2 className="w-4 h-4 animate-spin" />
                                    Converting to markdown...
                                </div>
                            ) : markdownContent ? (
                                <pre className="bg-slate-50 p-4 rounded-lg overflow-x-auto text-sm font-mono text-slate-700 whitespace-pre-wrap">
                                    {markdownContent}
                                </pre>
                            ) : (
                                <p className="text-slate-400 italic">No markdown content available.</p>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
