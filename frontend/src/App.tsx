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
    uploadProgress
  } = useDocuments()

  const [showViewer, setShowViewer] = useState(false)

  const handleSelect = (doc: any) => {
    setSelectedDoc(doc)
    setShowViewer(true)
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
      />

      {showViewer && selectedDoc ? (
        <DocumentViewer
          document={selectedDoc}
          onClose={() => {
            setShowViewer(false)
            setSelectedDoc(null)
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
        />
      )}
    </div>
  )
}

export default App
