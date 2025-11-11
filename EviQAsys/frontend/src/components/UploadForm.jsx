import { useState } from "react"

export default function UploadForm({ onUpload, isUploading }) {
    const [selectedFile, setSelectedFile] = useState(null)

    const handleSubmit = (event) => {
        event.preventDefault()
        if (!selectedFile) {
            return
        }
        onUpload(selectedFile)
    }

    return (
        <form className="panel" onSubmit={handleSubmit}>
            <label className="panel__label">
                Choose PDF
                <input
                    type="file"
                    accept="application/pdf"
                    onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                />
            </label>
            <button type="submit" disabled={!selectedFile || isUploading}>
                {isUploading ? "Uploading..." : "Upload PDF"}
            </button>
        </form>
    )
}
