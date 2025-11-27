import { useCallback, useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { deleteChat, listChatHistory } from "../api/client"
import PageHeader from "../components/layout/PageHeader"
import Button from "../components/ui/Button"
import { useToast } from "../components/ui/Toast"

function formatDateTime(value) {
    if (!value) return "--"
    try {
        return new Date(value).toLocaleString()
    } catch (error) {
        console.warn("Failed to format date", error)
        return value
    }
}

function formatCollectionName(name, id) {
    if (name) return name
    if (id) return `Collection #${id}`
    return "Collection 未命名"
}

function formatDocumentTitle(title, id) {
    if (title) return title
    if (id) return `Document #${id}`
    return "Document 未命名"
}

function formatChatTitle(title, id) {
    if (title) return title
    if (id) return `Chat #${id}`
    return "未命名 Chat"
}

export default function ChatHistory() {
    const navigate = useNavigate()
    const { addToast } = useToast()
    const [history, setHistory] = useState({ collections: [], documents: [] })
    const [loading, setLoading] = useState(false)
    const [deletingIds, setDeletingIds] = useState(new Set())

    const loadHistory = useCallback(async () => {
        setLoading(true)
        try {
            const data = await listChatHistory()
            const collections = (Array.isArray(data?.collections) ? data.collections : []).filter(
                (item) => item?.chat_id && item?.collection_id,
            )
            const documents = (Array.isArray(data?.documents) ? data.documents : []).filter(
                (item) => item?.chat_id && item?.document_id,
            )
            setHistory({ collections, documents })
        } catch (error) {
            addToast({ type: "error", title: "加载 Chat 历史失败", message: error.message })
        } finally {
            setLoading(false)
        }
    }, [addToast])

    useEffect(() => {
        loadHistory()
    }, [loadHistory])

    async function handleDelete(chatId) {
        if (!chatId) return
        const confirmed = window.confirm("确定删除该聊天记录吗？聊天内容将被清除。")
        if (!confirmed) return
        setDeletingIds((prev) => {
            const next = new Set(prev)
            next.add(chatId)
            return next
        })
        try {
            await deleteChat(chatId)
            addToast({ type: "success", title: "已删除聊天", message: `Chat #${chatId}` })
            await loadHistory()
        } catch (error) {
            addToast({ type: "error", title: "删除聊天失败", message: error.message })
        } finally {
            setDeletingIds((prev) => {
                const next = new Set(prev)
                next.delete(chatId)
                return next
            })
        }
    }

    return (
        <>
            <PageHeader
                breadcrumbs={[
                    { label: "Home", href: "/" },
                    { label: "Chat 历史" },
                ]}
                title="Chat 历史"
                subtitle="聚合 collection/document 聊天记录，按创建时间倒序，可深链到聊天页。"
                actions={
                    <div className="segmented-control">
                        <Button variant="ghost" onClick={loadHistory} disabled={loading}>
                            {loading ? "刷新中..." : "刷新"}
                        </Button>
                        <Button variant="tonal" disabled>
                            筛选（占位）
                        </Button>
                    </div>
                }
            />

            <div className="grid two-column">
                <div className="card">
                    <div className="card__header">
                        <h3 className="card__title">Collection 聊天历史</h3>
                        <span className="pill muted">
                            {history.collections.length > 0 ? `${history.collections.length} 条` : "按 created_at 倒序"}
                        </span>
                    </div>
                    <p className="caption">按 created_at 倒序，可跳转到 Collection Chat 三栏页面。</p>
                    {loading ? (
                        <div className="inline-kv">
                            <span className="status-dot" style={{ background: "var(--color-brand)" }}></span>
                            <strong>加载中...</strong>
                        </div>
                    ) : history.collections.length === 0 ? (
                        <div className="empty-state">暂无 Collection 聊天历史。</div>
                    ) : (
                        <div className="list">
                            {history.collections.map((item) => (
                                <button
                                    key={item.chat_id}
                                    type="button"
                                    className="list-item"
                                    onClick={() =>
                                        navigate(`/collections/${item.collection_id}/chat/${item.chat_id}`)
                                    }
                                    disabled={deletingIds.has(item.chat_id)}
                                >
                                    <div>
                                        <strong>
                                            {formatCollectionName(item.collection_name, item.collection_id)} ·{" "}
                                            {formatChatTitle(item.chat_title, item.chat_id)}
                                        </strong>
                                        <p className="caption">{formatDateTime(item.created_at)}</p>
                                    </div>
                                    <div className="list-item__meta">
                                        <span className="pill muted">Collection</span>
                                        <Button
                                            variant="ghost"
                                            className="danger-link"
                                            style={{ color: "var(--color-danger)" }}
                                            disabled={deletingIds.has(item.chat_id)}
                                            onClick={(event) => {
                                                event.stopPropagation()
                                                handleDelete(item.chat_id)
                                            }}
                                        >
                                            {deletingIds.has(item.chat_id) ? "删除中..." : "删除"}
                                        </Button>
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}
                </div>
                <div className="card">
                    <div className="card__header">
                        <h3 className="card__title">Document 聊天历史</h3>
                        <span className="pill muted">
                            {history.documents.length > 0 ? `${history.documents.length} 条` : "按 created_at 倒序"}
                        </span>
                    </div>
                    <p className="caption">展示 collection_name &gt; document_title &gt; chat_name。</p>
                    {loading ? (
                        <div className="inline-kv">
                            <span className="status-dot" style={{ background: "var(--color-brand)" }}></span>
                            <strong>加载中...</strong>
                        </div>
                    ) : history.documents.length === 0 ? (
                        <div className="empty-state">暂无 Document 聊天历史。</div>
                    ) : (
                        <div className="list">
                            {history.documents.map((item) => (
                                <button
                                    key={item.chat_id}
                                    type="button"
                                    className="list-item"
                                    onClick={() => navigate(`/documents/${item.document_id}/chat/${item.chat_id}`)}
                                    disabled={deletingIds.has(item.chat_id)}
                                >
                                    <div>
                                        <strong>
                                            {formatCollectionName(item.collection_name, item.collection_id)} &gt;{" "}
                                            {formatDocumentTitle(item.document_title, item.document_id)} ·{" "}
                                            {formatChatTitle(item.chat_title, item.chat_id)}
                                        </strong>
                                        <p className="caption">{formatDateTime(item.created_at)}</p>
                                    </div>
                                    <div className="list-item__meta">
                                        <span className="pill muted">Document</span>
                                        <Button
                                            variant="ghost"
                                            className="danger-link"
                                            style={{ color: "var(--color-danger)" }}
                                            disabled={deletingIds.has(item.chat_id)}
                                            onClick={(event) => {
                                                event.stopPropagation()
                                                handleDelete(item.chat_id)
                                            }}
                                        >
                                            {deletingIds.has(item.chat_id) ? "删除中..." : "删除"}
                                        </Button>
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </>
    )
}
