import Button from "./ui/Button"
import StatusPill from "./ui/StatusPill"

const formatBytes = (value) => {
    if (!value) return "—"
    if (value < 1024) return `${value} B`
    if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
    return `${(value / (1024 * 1024)).toFixed(2)} MB`
}

const formatDateTime = (value) => {
    if (!value) return "—"
    try {
        return new Date(value).toLocaleString()
    } catch (err) {
        return value
    }
}

export default function DocumentList({ documents = [], isLoading, onRefresh }) {
    return (
        <div className="card">
            <div className="card__header">
                <div>
                    <h3 className="card__title">文档列表</h3>
                    <p className="caption">用于快速查看当前 Collection 中的文档和解析状态</p>
                </div>
                <Button variant="ghost" onClick={onRefresh} disabled={isLoading}>
                    {isLoading ? "刷新中..." : "刷新"}
                </Button>
            </div>

            {documents.length === 0 ? (
                <div className="empty-state">
                    当前列表为空，可输入 Collection ID 后点击“刷新”载入最新数据。
                </div>
            ) : (
                <div className="table-scroll">
                    <table className="data-table">
                        <thead>
                            <tr>
                                <th>名称</th>
                                <th>文件大小</th>
                                <th>创建时间</th>
                                <th>元素数量</th>
                                <th>状态</th>
                            </tr>
                        </thead>
                        <tbody>
                            {documents.map((doc) => (
                                <tr key={doc.id}>
                                    <td>{doc.file_name ?? doc.title ?? "Untitled"}</td>
                                    <td>{formatBytes(doc.file_size_bytes)}</td>
                                    <td>{formatDateTime(doc.created_at)}</td>
                                    <td>{doc.element_count ?? "—"}</td>
                                    <td>
                                        <StatusPill status={doc.parse_status} />
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
