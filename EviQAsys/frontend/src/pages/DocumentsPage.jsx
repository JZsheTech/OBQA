import { useState } from "react"
import { listDocuments, uploadDocument } from "../api/client"
import DocumentList from "../components/DocumentList"
import UploadForm from "../components/UploadForm"

export default function DocumentsPage() {
    const [collectionId, setCollectionId] = useState("")
    const [documents, setDocuments] = useState([])
    const [isLoading, setIsLoading] = useState(false)
    const [isUploading, setIsUploading] = useState(false)
    const [message, setMessage] = useState("")

    const loadDocuments = async () => {
        if (!collectionId) return
        setIsLoading(true)
        setMessage("")
        try {
            const data = await listDocuments(collectionId)
            setDocuments(data)
        } catch (error) {
            setMessage(error.message)
        } finally {
            setIsLoading(false)
        }
    }

    const handleUpload = async (file) => {
        if (!collectionId) {
            setMessage("Please provide a collection ID before uploading.")
            return
        }
        setIsUploading(true)
        setMessage("")
        try {
            const result = await uploadDocument(collectionId, file)
            setMessage(`Uploaded ${result.file_name}`)
            await loadDocuments()
        } catch (error) {
            setMessage(error.message)
        } finally {
            setIsUploading(false)
        }
    }

    return (
        <div className="app">
            <header>
                <h1>EviQAsys Document Console</h1>
                <p>Upload PDFs and verify MinerU ingestion results.</p>
            </header>

            <section className="panel">
                <label htmlFor="collectionId" className="panel__label">
                    Collection ID
                </label>
                <div className="panel__row">
                    <input
                        id="collectionId"
                        type="number"
                        value={collectionId}
                        onChange={(event) => setCollectionId(event.target.value)}
                        placeholder="Enter collection id"
                    />
                    <button onClick={loadDocuments} disabled={!collectionId || isLoading}>
                        {isLoading ? "Loading..." : "Load Documents"}
                    </button>
                </div>
            </section>

            <UploadForm onUpload={handleUpload} isUploading={isUploading} />
            <DocumentList documents={documents} isLoading={isLoading} onRefresh={loadDocuments} />

            {message && <div className="message">{message}</div>}
        </div>
    )
}
