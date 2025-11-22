import { useEffect, useMemo, useRef, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import {
    getCollectionDetail,
    listCollectionChats,
    listDocuments,
    runRetrieval,
    uploadDocument,
} from "../api/client"
import PageHeader from "../components/layout/PageHeader"
import Button from "../components/ui/Button"
import Drawer from "../components/ui/Drawer"
import SearchBar from "../components/ui/SearchBar"
import StatusPill from "../components/ui/StatusPill"
import { useToast } from "../components/ui/Toast"

const documentSearchOptions = [
    { label: "按 title", value: "title" },
    { label: "按 abstract", value: "abstract" },
    { label: "按 md_text", value: "md_text" },
]

const retrievalModes = [
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

function truncate(text, max = 160) {
    if (!text) return ""
    return text.length > max ? `${text.slice(0, max)}...` : text
}

export default function CollectionDetail() {
    const { collectionId } = useParams()
    const navigate = useNavigate()
    const { addToast } = useToast()
    const fileInputRef = useRef(null)

    const [collection, setCollection] = useState(null)
    const [loadingCollection, setLoadingCollection] = useState(false)

    const [documents, setDocuments] = useState([])
    const [loadingDocuments, setLoadingDocuments] = useState(false)
    const [searchField, setSearchField] = useState("title")
    const [searchText, setSearchText] = useState("")
    const [searchResults, setSearchResults] = useState([])
    const [searching, setSearching] = useState(false)
    const [hasSearched, setHasSearched] = useState(false)

    const [uploadQueue, setUploadQueue] = useState([])
    const [uploading, setUploading] = useState(false)

    const [chats, setChats] = useState([])
    const [loadingChats, setLoadingChats] = useState(false)

    const [ragQuery, setRagQuery] = useState("")
    const [ragMode, setRagMode] = useState("vector")
    const [ragTopK, setRagTopK] = useState(5)
    const [ragResults, setRagResults] = useState([])
    const [ragLoading, setRagLoading] = useState(false)
    const [selectedResult, setSelectedResult] = useState(null)

    const collectionTitle = useMemo(() => {
        if (collection?.name) return collection.name
        return `Collection ${collectionId}`
    }, [collection?.name, collectionId])

    useEffect(() => {
        if (!collectionId) return
        loadCollection()
        loadDocuments()
        loadChats()
        setSearchResults([])
        setHasSearched(false)
        setSearchText("")
    }, [collectionId])

    async function loadCollection() {
        setLoadingCollection(true)
        try {
            const data = await getCollectionDetail(collectionId)
            setCollection(data)
        } catch (error) {
            addToast({ type: "error", title: "加载 Collection 失败", message: error.message })
        } finally {
            setLoadingCollection(false)
        }
    }

    async function loadDocuments() {
        setLoadingDocuments(true)
        try {
            const data = await listDocuments(collectionId)
            setDocuments(Array.isArray(data) ? data : [])
        } catch (error) {
            addToast({ type: "error", title: "加载文档失败", message: error.message })
        } finally {
            setLoadingDocuments(false)
        }
    }

    async function loadChats() {
        setLoadingChats(true)
        try {
            const data = await listCollectionChats(collectionId)
            setChats(Array.isArray(data) ? data : [])
        } catch (error) {
            addToast({ type: "error", title: "加载聊天历史失败", message: error.message })
        } finally {
            setLoadingChats(false)
        }
    }

    async function handleSearch() {
        const keyword = searchText.trim()
        if (!keyword) {
            addToast({ type: "info", title: "请输入关键字", message: "title/abstract/md_text 关键字不能为空" })
            setHasSearched(false)
            setSearchResults([])
            return
        }
        setSearching(true)
        try {
            const data = await listDocuments(collectionId, { searchField, keyword })
            setSearchResults(Array.isArray(data) ? data : [])
            setHasSearched(true)
        } catch (error) {
            addToast({ type: "error", title: "搜索失败", message: error.message })
        } finally {
            setSearching(false)
        }
    }

    async function handleResetSearch() {
        setSearchText("")
        setHasSearched(false)
        setSearchResults([])
        await loadDocuments()
    }

    function handleFileSelect(event) {
        const files = Array.from(event.target.files ?? [])
        if (!files.length) return
        const queue = files.map((file) => ({
            id: `${file.name}-${file.size}-${file.lastModified}-${Math.random().toString(16).slice(2)}`,
            file,
            status: "pending",
            message: "",
        }))
        setUploadQueue(queue)
        event.target.value = ""
    }

    function updateQueueEntry(id, payload) {
        setUploadQueue((current) => current.map((entry) => (entry.id === id ? { ...entry, ...payload } : entry)))
    }

    async function startUploadQueue() {
        if (!uploadQueue.length) {
            addToast({ type: "info", title: "请先选择文件", message: "支持多选 PDF 后再开始上传" })
            return
        }
        setUploading(true)
        let refreshed = false
        const queueSnapshot = [...uploadQueue]
        for (const entry of queueSnapshot) {
            updateQueueEntry(entry.id, { status: "uploading", message: "" })
            try {
                await uploadDocument(collectionId, entry.file)
                updateQueueEntry(entry.id, { status: "success", message: "已上传" })
                addToast({ type: "success", title: "上传成功", message: entry.file.name })
                refreshed = true
            } catch (error) {
                updateQueueEntry(entry.id, { status: "error", message: error.message })
                addToast({ type: "error", title: "上传失败", message: `${entry.file.name}: ${error.message}` })
            }
        }
        if (refreshed) {
            await loadDocuments()
        }
        setUploading(false)
    }

    async function handleRetrieval() {
        const keyword = ragQuery.trim()
        if (!keyword) {
            addToast({ type: "info", title: "请输入检索词", message: "关键词不能为空" })
            return
        }
        const normalizedTopK = Math.min(30, Math.max(1, Number(ragTopK) || 5))
        setRagTopK(normalizedTopK)
        setRagLoading(true)
        try {
            const data = await runRetrieval({
                collectionId,
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
            addToast({ type: "success", title: "已复制", message: "检索结果内容已复制" })
        } catch (error) {
            addToast({ type: "error", title: "复制失败", message: error.message })
        }
    }

    const allDocCount = documents.length
    const searchCount = searchResults.length

    return (
        <>
            <PageHeader
                breadcrumbs={[
                    { label: "Home", href: "/" },
                    { label: collectionTitle },
                ]}
                title={collectionTitle}
                subtitle={
                    loadingCollection
                        ? "加载 collection 元信息..."
                        : collection?.description || "暂无描述"
                }
                actions={
                    <Button onClick={() => fileInputRef.current?.click()} disabled={uploading}>
                        {uploading ? "上传中..." : "上传文档"}
                    </Button>
                }
            />

            <input
                ref={fileInputRef}
                type="file"
                multiple
                accept="application/pdf"
                className="sr-only"
                onChange={handleFileSelect}
            />

            <div className="grid two-column">
                <div className="stack">
                    <div className="card">
                        <div className="card__header">
                            <div>
                                <h3 className="card__title">Collection 信息</h3>
                                <p className="caption">展示 name/description/created_at 元数据。</p>
                            </div>
                            <span className="pill muted">{loadingCollection ? "加载中..." : "M5c ready"}</span>
                        </div>
                        <div className="info-grid">
                            <div className="info-item">
                                <div className="caption">名称</div>
                                <strong>{collection?.name ?? "—"}</strong>
                            </div>
                            <div className="info-item">
                                <div className="caption">创建时间</div>
                                <strong>{formatDateTime(collection?.created_at)}</strong>
                            </div>
                            <div className="info-item span-2">
                                <div className="caption">描述</div>
                                <p className="caption">{collection?.description || "暂无描述"}</p>
                            </div>
                        </div>
                    </div>

                    <div className="card">
                        <div className="card__header">
                            <div>
                                <h3 className="card__title">文档列表</h3>
                                <p className="caption">全部/搜索视图来自 /api/collections/{collectionId}/documents。</p>
                            </div>
                            <Button variant="ghost" onClick={loadDocuments} disabled={loadingDocuments}>
                                {loadingDocuments ? "刷新中..." : "刷新"}
                            </Button>
                        </div>
                        <SearchBar
                            compact
                            value={searchText}
                            onChange={setSearchText}
                            filterValue={searchField}
                            onFilterChange={setSearchField}
                            filterOptions={documentSearchOptions}
                            onSubmit={handleSearch}
                            onReset={handleResetSearch}
                            placeholder="按 title / abstract / md_text 搜索"
                            loading={searching}
                        />
                        {hasSearched && (
                            <div className="search-meta">
                                <span className="tag">Searched result</span>
                                <span className="caption">
                                    按 {searchField} 搜索 “{searchText.trim()}”，共 {searchCount} 条
                                </span>
                            </div>
                        )}

                        <div className="section-block">
                            <div className="section-block__header">
                                <strong>全部文档</strong>
                                <span className="caption">{allDocCount} 条</span>
                            </div>
                            {loadingDocuments ? (
                                <div className="inline-kv">
                                    <span className="status-dot" style={{ background: "var(--color-brand)" }}></span>
                                    <strong>加载中...</strong>
                                    <span className="caption">正在读取最新列表</span>
                                </div>
                            ) : documents.length === 0 ? (
                                <div className="empty-state">当前 Collection 暂无文档，可上传后刷新查看。</div>
                            ) : (
                                <div className="list">
                                    {documents.map((doc) => (
                                        <button
                                            key={doc.id}
                                            type="button"
                                            className="list-item doc-card"
                                            onClick={() =>
                                                navigate(`/collections/${collectionId}/documents/${doc.id}`)
                                            }
                                        >
                                            <div className="doc-card__main">
                                                <div className="doc-card__title">{doc.title || doc.file_name || "Untitled"}</div>
                                                <p className="caption" title={doc.file_name}>
                                                    {doc.file_name || "未保存文件名"}
                                                </p>
                                                {doc.abstract && <p className="caption muted">摘要：{truncate(doc.abstract, 120)}</p>}
                                            </div>
                                            <div className="doc-card__meta">
                                                <StatusPill status={doc.parse_status} />
                                                <span className="pill muted">{doc.element_count ?? 0} elements</span>
                                                <span className="pill muted">{doc.num_pages ?? "?"} pages</span>
                                                <span className="caption">{formatDateTime(doc.created_at)}</span>
                                            </div>
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>

                        <div className="section-block">
                            <div className="section-block__header">
                                <strong>搜索结果</strong>
                                <span className="caption">{searchCount} 条</span>
                            </div>
                            {searching ? (
                                <div className="inline-kv">
                                    <span className="status-dot" style={{ background: "var(--color-brand)" }}></span>
                                    <strong>搜索中...</strong>
                                </div>
                            ) : !hasSearched ? (
                                <div className="empty-state">输入关键字后显示搜索结果。</div>
                            ) : searchResults.length === 0 ? (
                                <div className="empty-state">未命中文档，尝试更换关键字或字段。</div>
                            ) : (
                                <div className="list">
                                    {searchResults.map((doc) => (
                                        <button
                                            key={`search-${doc.id}`}
                                            type="button"
                                            className="list-item doc-card"
                                            onClick={() =>
                                                navigate(`/collections/${collectionId}/documents/${doc.id}`)
                                            }
                                        >
                                            <div className="doc-card__main">
                                                <div className="doc-card__title">{doc.title || doc.file_name || "Untitled"}</div>
                                                <p className="caption" title={doc.file_name}>
                                                    {doc.file_name || "未保存文件名"}
                                                </p>
                                                {doc.abstract && <p className="caption muted">摘要：{truncate(doc.abstract, 120)}</p>}
                                            </div>
                                            <div className="doc-card__meta">
                                                <StatusPill status={doc.parse_status} />
                                                <span className="pill muted">{doc.element_count ?? 0} elements</span>
                                                <span className="caption">{formatDateTime(doc.created_at)}</span>
                                            </div>
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>

                    <div className="card">
                        <div className="card__header">
                            <div>
                                <h3 className="card__title">上传 PDF（多文件）</h3>
                                <p className="caption">选择多个 PDF 后串行调用 MinerU 入库，状态在队列中展示。</p>
                            </div>
                            <Button variant="ghost" onClick={() => fileInputRef.current?.click()} disabled={uploading}>
                                选择文件
                            </Button>
                        </div>
                        <div className="stack">
                            <Button onClick={startUploadQueue} disabled={uploading || uploadQueue.length === 0}>
                                {uploading ? "上传中..." : "开始上传"}
                            </Button>
                            {uploadQueue.length === 0 ? (
                                <div className="empty-state">等待选择文件，支持多选 PDF。</div>
                            ) : (
                                <ul className="upload-queue">
                                    {uploadQueue.map((entry) => (
                                        <li key={entry.id} className={`upload-queue__item status-${entry.status}`}>
                                            <div>
                                                <strong>{entry.file.name}</strong>
                                                <div className="caption">{(entry.file.size / (1024 * 1024)).toFixed(2)} MB</div>
                                            </div>
                                            <div className="upload-queue__status">
                                                <span className="pill muted">{entry.status}</span>
                                                {entry.message && <span className="caption">{entry.message}</span>}
                                            </div>
                                        </li>
                                    ))}
                                </ul>
                            )}
                        </div>
                    </div>
                </div>

                <div className="stack">
                    <div className="card">
                        <div className="card__header">
                            <div>
                                <h3 className="card__title">Collection 聊天历史</h3>
                                <p className="caption">来自 /api/collections/{collectionId}/chats，点击跳转聊天页。</p>
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
                            <div className="empty-state">暂无聊天记录，M5e 将提供创建聊天的入口。</div>
                        ) : (
                            <div className="list">
                                {chats.map((chat) => (
                                    <button
                                        key={chat.id}
                                        type="button"
                                        className="list-item"
                                        onClick={() => navigate(`/collections/${collectionId}/chat/${chat.id}`)}
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

                    <div className="card">
                        <div className="card__header">
                            <div>
                                <h3 className="card__title">简单 Collection-RAG</h3>
                                <p className="caption">复用 /api/retrieval/test，支持向量/全文模式。</p>
                            </div>
                            <span className="pill muted">TopK {ragTopK}</span>
                        </div>
                        <div className="stack">
                            <textarea
                                className="input"
                                rows={3}
                                value={ragQuery}
                                onChange={(event) => setRagQuery(event.target.value)}
                                placeholder="输入关键词或问题，检索 collection 内的元素"
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
                                <div className="empty-state">输入关键词后展示检索结果。</div>
                            ) : (
                                <div className="list">
                                    {ragResults.map((item) => (
                                        <div key={item.element_id} className="list-item rag-item">
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
            </div>

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
