import { useState } from "react"
import Button from "./ui/Button"

export default function UploadForm({ onUpload, isUploading }) {
    const [selectedFile, setSelectedFile] = useState(null)

    const handleSubmit = (event) => {
        event.preventDefault()
        if (!selectedFile) return
        onUpload(selectedFile)
    }

    return (
        <form className="card" onSubmit={handleSubmit}>
            <div className="card__header">
                <div>
                    <h3 className="card__title">上传 PDF</h3>
                    <p className="caption">通过 MinerU 解析后将同步入库</p>
                </div>
                <span className="pill muted">{selectedFile ? selectedFile.name : "等待文件"}</span>
            </div>

            <div className="stack">
                <label className="caption" htmlFor="uploadInput">
                    选择文件（仅支持 PDF）
                </label>
                <input
                    id="uploadInput"
                    className="input"
                    type="file"
                    accept="application/pdf"
                    onChange={(event) => setSelectedFile(event.target.files?.[0] ?? null)}
                />
                <Button type="submit" disabled={!selectedFile || isUploading}>
                    {isUploading ? "上传中..." : "上传 PDF"}
                </Button>
            </div>
        </form>
    )
}
