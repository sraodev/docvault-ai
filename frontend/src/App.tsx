import { useState } from 'react'
import { Sidebar } from './components/Sidebar'
import { DriveView } from './components/DriveView'
import { DocumentViewer } from './components/DocumentViewer'
import { useDocuments } from './hooks/useDocuments'

function App() {
  const {
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
    uploadProgress
  } = useDocuments()

  const [showViewer, setShowViewer] = useState(false)
  const [currentFolder, setCurrentFolder] = useState<string | null>(null)

  const handleSelect = (doc: any) => {
    setSelectedDoc(doc)
    setShowViewer(true)
  }

  const handleCloseViewer = () => {
    setShowViewer(false)
    setSelectedDoc(null)
  }

  const handleNavigateHome = () => {
    // Close document viewer if open
    setShowViewer(false)
    setSelectedDoc(null)
    // Navigate to root folder
    setCurrentFolder(null)
  }

  const handleFolderChange = (folder: string | null) => {
    // When folder changes from tree view, close document viewer if open
    if (showViewer) {
      setShowViewer(false)
      setSelectedDoc(null)
    }
    setCurrentFolder(folder)
  }

  return (
    <div className="flex h-screen bg-white font-sans text-slate-900">
      <Sidebar
        documents={documents}
        folders={folders}
        selectedDocId={selectedDoc?.id}
        onSelect={handleSelect}
        onDelete={handleDelete}
        onUpload={handleUpload}
        isUploading={isUploading}
        uploadError={uploadError}
        uploadProgress={uploadProgress}
        currentFolder={currentFolder}
        onFolderChange={handleFolderChange}
        onCreateFolder={handleCreateFolder}
        onDeleteFolder={handleDeleteFolder}
        onNavigateHome={handleNavigateHome}
      />

      {showViewer && selectedDoc ? (
        <DocumentViewer
          document={selectedDoc}
          onClose={handleCloseViewer}
          onNavigateToFolder={(folder: string | null) => {
            setCurrentFolder(folder)
            handleCloseViewer()
          }}
          onDeleteFolder={handleDeleteFolder}
          documents={documents}
        />
      ) : (
        <DriveView
          documents={documents}
          selectedDocId={selectedDoc?.id}
          onSelect={handleSelect}
          onDelete={handleDelete}
          onUpload={handleUpload}
          uploadProgress={uploadProgress}
          currentFolder={currentFolder}
          onFolderChange={setCurrentFolder}
          onDeleteFolder={handleDeleteFolder}
        />
      )}
    </div>
  )
}

export default App
