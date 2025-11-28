import { useState } from 'react'
import { Sidebar } from './components/Sidebar'
import { DriveView } from './components/DriveView'
import { DocumentViewer } from './components/DocumentViewer'
import { useDocuments } from './hooks/useDocuments'

function App() {
  const {
    documents,
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

  return (
    <div className="flex h-screen bg-white font-sans text-slate-900">
      <Sidebar
        documents={documents}
        selectedDocId={selectedDoc?.id}
        onSelect={handleSelect}
        onDelete={handleDelete}
        onUpload={handleUpload}
        isUploading={isUploading}
        uploadError={uploadError}
        uploadProgress={uploadProgress}
        currentFolder={currentFolder}
        onFolderChange={setCurrentFolder}
        onCreateFolder={handleCreateFolder}
        onDeleteFolder={handleDeleteFolder}
      />

      {showViewer && selectedDoc ? (
        <DocumentViewer
          document={selectedDoc}
          onClose={handleCloseViewer}
          onNavigateToFolder={(folder: string | null) => {
            setCurrentFolder(folder)
            handleCloseViewer()
          }}
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
