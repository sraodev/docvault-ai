import { Sidebar } from './components/Sidebar'
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
    handleDelete
  } = useDocuments()

  return (
    <div className="flex h-screen bg-slate-50 font-sans text-slate-900">
      <Sidebar
        documents={documents}
        selectedDocId={selectedDoc?.id}
        onSelect={setSelectedDoc}
        onDelete={handleDelete}
        onUpload={handleUpload}
        isUploading={isUploading}
        uploadError={uploadError}
      />

      <DocumentViewer document={selectedDoc} />
    </div>
  )
}

export default App
