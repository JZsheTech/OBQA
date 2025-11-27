import { useEffect, useMemo, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import {
    buildDocumentFileUrl,
    getCollectionDetail,
    getDocumentDetail,
    listDocumentChats,
    runRetrieval,
} from "../api/client"
import DebugIdFooter from "../components/DebugIdFooter"
import PageHeader from "../components/layout/PageHeader"
import Button from "../components/ui/Button"
import Drawer from "../components/ui/Drawer"
import StatusPill from "../components/ui/StatusPill"
import { useToast } from "../components/ui/Toast"

const retrievalModes = [
    { label: "混合检索", value: "hybrid" },
    { label: "向量检索", value: "vector" },
    { label: "全文检索", value: "fulltext" },
]

function formatDateTime(value) {
    if (!value) return "--"
    try {
        return new Date(value).toLocaleString()
    } catch (error) {
        console.warn("Failed to format date", error)
        return value
    }
}

function formatFileSize(bytes) {
    if (!bytes && bytes !== 0) return "--"
    const size = Number(bytes)
    if (Number.isNaN(size) || size < 0) return "--"
    if (size < 1024) return `${size} B`
    if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
    return `${(size / (1024 * 1024)).toFixed(2)} MB`
}

function truncate(text, max = 160) {
    if (!text) return ""
    return text.length > max ? `${text.slice(0, max)}...` : text
}

export default function DocumentDetail() {
    const { documentId, collectionId: collectionIdFromRoute } = useParams()
    const navigate = useNavigate()
    const { addToast } = useToast()

    const [document, setDocument] = useState(null)
    const [collection, setCollection] = useState(null)
    const [loadingDocument, setLoadingDocument] = useState(false)
    const [loadingCollection, setLoadingCollection] = useState(false)

    const [chats, setChats] = useState([])
    const [loadingChats, setLoadingChats] = useState(false)

    const [ragQuery, setRagQuery] = useState("")
    const [ragMode, setRagMode] = useState("hybrid")
    const [ragTopK, setRagTopK] = useState(5)
    const [ragResults, setRagResults] = useState([])
    const [ragLoading, setRagLoading] = useState(false)
    const [selectedResult, setSelectedResult] = useState(null)

    useEffect(() => {
        setRagResults([])
        setSelectedResult(null)
        loadDocument()
        loadChats()
    }, [documentId])

    useEffect(() => {
        const targetCollectionId = document?.collection_id ?? collectionIdFromRoute
        if (targetCollectionId) {
            loadCollection(targetCollectionId)
        }
    }, [document?.collection_id, collectionIdFromRoute])

    const pageTitle = useMemo(() => {
        if (document?.title) return document.title
        if (document?.file_name) return document.file_name
        return `Document ${documentId}`
    }, [document?.title, document?.file_name, documentId])

    const collectionName = useMemo(() => {
        if (collection?.name) return collection.name
        if (document?.collection_name) return document.collection_name
        if (collectionIdFromRoute) return `Collection ${collectionIdFromRoute}`
        if (document?.collection_id) return `Collection ${document.collection_id}`
        return "Collection"
    }, [collection?.name, document?.collection_name, document?.collection_id, collectionIdFromRoute])

    async function loadDocument() {
        if (!documentId) return
        setLoadingDocument(true)
        try {
            const data = await getDocumentDetail(documentId)
            setDocument(data)
        } catch (error) {
            addToast({ type: "error", title: "加载文档失败", message: error.message })
        } finally {
            setLoadingDocument(false)
        }
    }

    async function loadCollection(targetId) {
        if (!targetId) return
        setLoadingCollection(true)
        try {
            const data = await getCollectionDetail(targetId)
            setCollection(data)
        } catch (error) {
            addToast({ type: "error", title: "加载 Collection 失败", message: error.message })
        } finally {
            setLoadingCollection(false)
        }
    }

    async function loadChats() {
        if (!documentId) return
        setLoadingChats(true)
        try {
            const data = await listDocumentChats(documentId)
            setChats(Array.isArray(data) ? data : [])
        } catch (error) {
            addToast({ type: "error", title: "加载聊天历史失败", message: error.message })
        } finally {
            setLoadingChats(false)
        }
    }

    function handleOpenPdf() {
        try {
            const url = buildDocumentFileUrl(documentId)
            window.open(url, "_blank", "noopener,noreferrer")
        } catch (error) {
            addToast({ type: "error", title: "无法打开 PDF", message: error.message })
        }
    }

    async function handleRetrieval() {
        const keyword = ragQuery.trim()
        if (!keyword) {
            addToast({ type: "info", title: "请输入检索词", message: "关键词不能为空" })
            return
        }
        const targetCollectionId = document?.collection_id ?? collectionIdFromRoute
        if (!targetCollectionId) {
            addToast({ type: "error", title: "缺少 collection_id", message: "请确认路由或文档信息" })
            return
        }
        const normalizedTopK = Math.min(30, Math.max(1, Number(ragTopK) || 5))
        setRagTopK(normalizedTopK)
        setRagLoading(true)
        try {
            const data = await runRetrieval({
                collectionId: targetCollectionId,
                docId: documentId,
                query: keyword,
                topK: normalizedTopK,
                searchMode: ragMode,
            })
            setRagResults(Array.isArray(data) ? data : [])
        } catch (error) {
            addToast({ type: "error", title: "检索失败", message: error.message })
        } finally {
            setRagLoading(false)
        }
    }

    async function handleCopy(text) {
        if (!text) return
        try {
            await navigator.clipboard.writeText(text)
            addToast({ type: "success", title: "已复制", message: "内容已复制到剪贴板" })
        } catch (error) {
            addToast({ type: "error", title: "复制失败", message: error.message })
        }
    }

    const pageSubtitle = loadingDocument
        ? "加载 document 元信息..."
        : document?.abstract
            ? truncate(document.abstract, 120)
            : "Document 元信息、Abstract 展示、聊天历史与 Document-RAG"
    const parseStatus = document?.parse_status ?? ((document?.element_count || 0) > 0 ? "parsed" : "uploaded")
    const metaInfoText = document?.meta_info ? JSON.stringify(document.meta_info) : "暂无 meta_info"

    return (
        <>
            <PageHeader
                breadcrumbs={[
                    { label: "Home", href: "/" },
                    { label: collectionName, href: document?.collection_id || collectionIdFromRoute ? `/collections/${document?.collection_id ?? collectionIdFromRoute}` : undefined },
                    { label: pageTitle },
                ]}
                title={pageTitle}
                subtitle={pageSubtitle}
                actions={
                    <div className="page-actions">
                        <Button
                            variant="ghost"
                            onClick={() =>
                                navigate(
                                    `/collections/${document?.collection_id ?? collectionIdFromRoute ?? ""}`,
                                )
                            }
                            disabled={!document?.collection_id && !collectionIdFromRoute}
                        >
                            返回 Collection
                        </Button>
                        <Button variant="tonal" onClick={handleOpenPdf}>
                            打开原始 PDF
                        </Button>
                    </div>
                }
            />

            <div className="grid two-column">
                <div className="stack">
                    <div className="card">
                        <div className="card__header">
                            <div>
                                <h3 className="card__title">Document 信息</h3>
                                <p className="caption">来自 /api/documents/{documentId}</p>
                            </div>
                            <StatusPill status={parseStatus} />
                        </div>
                        <div className="info-grid">
                            <div className="info-item">
                                <div className="caption">所属 Collection</div>
                                <strong>{collectionName}</strong>
                                {loadingCollection && <p className="caption">加载 collection 信息...</p>}
                            </div>
                            <div className="info-item">
                                <div className="caption">标题 / 文件名</div>
                                <strong>{document?.title || document?.file_name || `Document ${documentId}`}</strong>
                                <p className="caption">{document?.file_name || "未保存文件名"}</p>
                            </div>
                            <div className="info-item">
                                <div className="caption">创建时间</div>
                                <strong>{formatDateTime(document?.created_at)}</strong>
                            </div>
                            <div className="info-item">
                                <div className="caption">文件大小</div>
                                <strong>{formatFileSize(document?.file_size_bytes)}</strong>
                            </div>
                            <div className="info-item span-2">
                                <div className="caption">meta_info</div>
                                <p className="caption" title={metaInfoText}>
                                    {truncate(metaInfoText, 140)}
                                </p>
                            </div>
                        </div>
                        <div className="section-block__header" style={{ marginTop: "12px" }}>
                            <div className="pill muted">{document?.num_pages ?? "?"} pages</div>
                            <div className="pill muted">{document?.element_count ?? 0} elements</div>
                            <div className="pill muted">Doc #{documentId}</div>
                        </div>
                    </div>

                    <div className="card">
                        <div className="card__header">
                            <div>
                                <h3 className="card__title">Abstract</h3>
                                <p className="caption">来源 MinerU parse 的摘要</p>
                            </div>
                            <span className="pill muted">可滚动</span>
                        </div>
                        {document?.abstract ? (
                            <div
                                style={{
                                    maxHeight: "320px",
                                    overflowY: "auto",
                                    background: "var(--color-surface-muted)",
                                    borderRadius: "var(--radius-sm)",
                                    padding: "14px",
                                    lineHeight: 1.6,
                                }}
                            >
                                {document.abstract}
                            </div>
                        ) : (
                            <div className="empty-state">
                                {loadingDocument ? "正在加载 abstract..." : "暂未生成 Abstract"}
                            </div>
                        )}
                    </div>

                    <div className="card">
                        <div className="card__header">
                            <div>
                                <h3 className="card__title">Document-RAG 检索</h3>
                                <p className="caption">带 doc_id 过滤的 /api/retrieval/test（混合/向量/全文）。</p>
                            </div>
                            <span className="pill muted">TopK {ragTopK}</span>
                        </div>
                        <div className="stack">
                            <textarea
                                className="input"
                                rows={3}
                                value={ragQuery}
                                onChange={(event) => setRagQuery(event.target.value)}
                                placeholder="输入关键词或问题，检索当前 document 的元素"
                            ></textarea>
                            <div className="segmented-control">
                                {retrievalModes.map((mode) => (
                                    <button
                                        key={mode.value}
                                        type="button"
                                        className={`segment${ragMode === mode.value ? " active" : ""}`}
                                        onClick={() => setRagMode(mode.value)}
                                    >
                                        {mode.label}
                                    </button>
                                ))}
                                <input
                                    type="number"
                                    className="segment-input"
                                    min={1}
                                    max={30}
                                    value={ragTopK}
                                    onChange={(event) => setRagTopK(event.target.value)}
                                    title="TopK"
                                />
                                <Button onClick={handleRetrieval} disabled={ragLoading}>
                                    {ragLoading ? "检索中..." : "检索"}
                                </Button>
                            </div>
                            {ragLoading ? (
                                <div className="inline-kv">
                                    <span className="status-dot" style={{ background: "var(--color-brand)" }}></span>
                                    <strong>检索中...</strong>
                                </div>
                            ) : ragResults.length === 0 ? (
                                <div className="empty-state">输入关键词后展示文档级检索结果。</div>
                            ) : (
                                <div className="list">
                                    {ragResults.map((item) => (
                                        <div key={`${item.element_id}-${item.doc_id}`} className="list-item rag-item">
                                            <div className="rag-item__meta">
                                                <span className="pill muted">Elem #{item.element_id}</span>
                                                <span className="pill muted">Doc #{item.doc_id}</span>
                                                <span className="pill muted">{item.elem_type}</span>
                                                <span className="pill muted">score {item.score.toFixed(3)}</span>
                                            </div>
                                            <p className="caption">{truncate(item.text_content, 220) || "无文本内容"}</p>
                                            <div className="rag-item__actions">
                                                <Button variant="ghost" onClick={() => setSelectedResult(item)}>
                                                    查看全文
                                                </Button>
                                                <Button variant="ghost" onClick={() => handleCopy(item.text_content)}>
                                                    复制
                                                </Button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                <div className="stack">
                    <div className="card">
                        <div className="card__header">
                            <div>
                                <h3 className="card__title">Document 聊天历史</h3>
                                <p className="caption">来自 /api/documents/{documentId}/chats</p>
                            </div>
                            <Button variant="ghost" onClick={loadChats} disabled={loadingChats}>
                                {loadingChats ? "刷新中..." : "刷新"}
                            </Button>
                        </div>
                        {loadingChats ? (
                            <div className="inline-kv">
                                <span className="status-dot" style={{ background: "var(--color-brand)" }}></span>
                                <strong>加载中...</strong>
                            </div>
                        ) : chats.length === 0 ? (
                            <div className="empty-state">暂无文档级聊天记录，M5e 将提供创建入口。</div>
                        ) : (
                            <div className="list">
                                {chats.map((chat) => (
                                    <button
                                        key={chat.id}
                                        type="button"
                                        className="list-item"
                                        onClick={() => navigate(`/documents/${documentId}/chat/${chat.id}`)}
                                    >
                                        <div>
                                            <strong>{chat.title || `Chat #${chat.id}`}</strong>
                                            <p className="caption">{formatDateTime(chat.created_at)}</p>
                                        </div>
                                        <span className="pill muted">{chat.type}</span>
                                    </button>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </div>

            <DebugIdFooter
                segments={[
                    { label: "Collection", value: document?.collection_id ?? collectionIdFromRoute },
                    { label: "Document", value: document?.id ?? documentId },
                ]}
            />

            <Drawer
                open={Boolean(selectedResult)}
                title="检索结果详情"
                onClose={() => setSelectedResult(null)}
                footer={
                    <Button variant="ghost" onClick={() => setSelectedResult(null)}>
                        关闭
                    </Button>
                }
            >
                {selectedResult && (
                    <div className="stack">
                        <div className="inline-kv">
                            <strong>Element</strong>
                            <span className="caption">#{selectedResult.element_id}</span>
                        </div>
                        <div className="inline-kv">
                            <strong>Document</strong>
                            <span className="caption">#{selectedResult.doc_id}</span>
                        </div>
                        <div className="inline-kv">
                            <strong>Score</strong>
                            <span className="caption">{selectedResult.score?.toFixed(4)}</span>
                        </div>
                        <div className="inline-kv">
                            <strong>类型</strong>
                            <span className="caption">{selectedResult.elem_type}</span>
                        </div>
                        <div className="code-block">{selectedResult.text_content || "无文本内容"}</div>
                        <Button onClick={() => handleCopy(selectedResult.text_content)}>复制文本</Button>
                    </div>
                )}
            </Drawer>
        </>
    )
}
