const formatBytes = (value) => {
    if (!value) return "—"
    if (value < 1024) return `${value} B`
    if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
    return `${(value / (1024 * 1024)).toFixed(2)} MB`
}

export default function DocumentList({ documents, isLoading, onRefresh }) {
    return (
        <div className="panel">
            <div className="panel__header">
                <h2>Document List</h2>
                <button onClick={onRefresh} disabled={isLoading}>
                    {isLoading ? "Loading..." : "Refresh"}
                </button>
            </div>
            {documents.length === 0 ? (
                <p className="empty">No documents loaded yet.</p>
            ) : (
                <div className="table-wrapper">
                    <table>
                        <thead>
                            <tr>
                                <th>Name</th>
                                <th>Size</th>
                                <th>Created</th>
                                <th>Elements</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            {documents.map((doc) => (
                                <tr key={doc.id}>
                                    <td>{doc.file_name ?? "Untitled"}</td>
                                    <td>{formatBytes(doc.file_size_bytes)}</td>
                                    <td>{new Date(doc.created_at).toLocaleString()}</td>
                                    <td>{doc.element_count ?? "—"}</td>
                                    <td>
                                        <span className={`status status--${doc.parse_status}`}>
                                            {doc.parse_status}
                                        </span>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    )
}
