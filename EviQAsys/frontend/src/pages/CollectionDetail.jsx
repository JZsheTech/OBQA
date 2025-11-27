import { useEffect, useMemo, useRef, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import {
    getCollectionDetail,
    listCollectionChats,
    listDocuments,
    runRetrieval,
    createCollectionChat,
    createDocumentChat,
    uploadDocument,
    deleteDocument,
    deleteChat,
    updateCollection,
} from "../api/client"
import DebugIdFooter from "../components/DebugIdFooter"
import PageHeader from "../components/layout/PageHeader"
import Button from "../components/ui/Button"
import Drawer from "../components/ui/Drawer"
import Modal from "../components/ui/Modal"
import SearchBar from "../components/ui/SearchBar"
import StatusPill from "../components/ui/StatusPill"
import { useToast } from "../components/ui/Toast"

const documentSearchOptions = [
    { label: "按 title", value: "title" },
    { label: "按 abstract", value: "abstract" },
    { label: "按 md_text", value: "md_text" },
]

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
    const [showEditModal, setShowEditModal] = useState(false)
    const [editForm, setEditForm] = useState({ name: "", description: "" })
    const [savingCollection, setSavingCollection] = useState(false)

    const [documents, setDocuments] = useState([])
    const [loadingDocuments, setLoadingDocuments] = useState(false)
    const [searchField, setSearchField] = useState("title")
    const [searchText, setSearchText] = useState("")
    const [searchResults, setSearchResults] = useState([])
    const [searching, setSearching] = useState(false)
    const [hasSearched, setHasSearched] = useState(false)
    const [deletingDocumentIds, setDeletingDocumentIds] = useState(new Set())

    const [uploadQueue, setUploadQueue] = useState([])
    const [uploading, setUploading] = useState(false)

    const [chats, setChats] = useState([])
    const [loadingChats, setLoadingChats] = useState(false)
    const [creatingChat, setCreatingChat] = useState(false)
    const [deletingChatIds, setDeletingChatIds] = useState(new Set())
    const [creatingDocChatIds, setCreatingDocChatIds] = useState(new Set())

    const [ragQuery, setRagQuery] = useState("")
    const [ragMode, setRagMode] = useState("hybrid")
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
            setEditForm({
                name: data?.name ?? "",
                description: data?.description ?? "",
            })
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

    async function handleCreateChat() {
        if (!collectionId) return
        setCreatingChat(true)
        try {
            const result = await createCollectionChat(collectionId, { title: "" })
            const newId = result?.id ?? result?.data?.id
            await loadChats()
            if (newId) {
                navigate(`/collections/${collectionId}/chat/${newId}`)
                addToast({ type: "success", title: "已创建聊天", message: `Chat #${newId}` })
            } else {
                addToast({ type: "info", title: "聊天已创建", message: "请从列表选择" })
            }
        } catch (error) {
            addToast({ type: "error", title: "创建聊天失败", message: error.message })
        } finally {
            setCreatingChat(false)
        }
    }

    async function handleDeleteChat(event, chat) {
        event.stopPropagation()
        const targetId = chat?.id
        if (!targetId) return
        const confirmed = window.confirm(
            `确定删除聊天 “${chat.title || `Chat #${targetId}`}” 吗？历史对话将被清除。`,
        )
        if (!confirmed) return
        setDeletingChatIds((prev) => {
            const next = new Set(prev)
            next.add(targetId)
            return next
        })
        try {
            await deleteChat(targetId)
            addToast({ type: "success", title: "已删除聊天", message: chat.title || `Chat #${targetId}` })
            await loadChats()
        } catch (error) {
            addToast({ type: "error", title: "删除聊天失败", message: error.message })
        } finally {
            setDeletingChatIds((prev) => {
                const next = new Set(prev)
                next.delete(targetId)
                return next
            })
        }
    }

    function openEditModal() {
        setEditForm({
            name: collection?.name ?? "",
            description: collection?.description ?? "",
        })
        setShowEditModal(true)
    }

    async function handleUpdateCollection() {
        if (!collectionId) return
        const trimmedName = (editForm.name ?? "").trim()
        if (!trimmedName) {
            addToast({ type: "error", title: "名称必填", message: "Collection name 不能为空" })
            return
        }
        setSavingCollection(true)
        try {
            await updateCollection(collectionId, {
                name: trimmedName,
                description: (editForm.description ?? "").trim(),
            })
            addToast({ type: "success", title: "已更新 Collection", message: trimmedName })
            setShowEditModal(false)
            await loadCollection()
        } catch (error) {
            addToast({ type: "error", title: "更新失败", message: error.message })
        } finally {
            setSavingCollection(false)
        }
    }

    function handleChatCardKeyDown(event, chatId) {
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault()
            navigate(`/collections/${collectionId}/chat/${chatId}`)
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

    async function refreshSearchResultsAfterChange() {
        const keyword = searchText.trim()
        if (hasSearched && keyword) {
            try {
                const data = await listDocuments(collectionId, { searchField, keyword })
                setSearchResults(Array.isArray(data) ? data : [])
            } catch (error) {
                addToast({ type: "error", title: "刷新搜索结果失败", message: error.message })
            }
        } else if (hasSearched && !keyword) {
            setHasSearched(false)
            setSearchResults([])
        }
    }

    async function handleDeleteDocument(event, doc) {
        event.stopPropagation()
        const targetId = doc?.id
        if (!targetId) return
        const label = doc.title || doc.file_name || `Doc #${targetId}`
        const confirmed = window.confirm(`确定删除文档 “${label}” 吗？该操作会清除其解析内容和聊天记录。`)
        if (!confirmed) return
        setDeletingDocumentIds((prev) => {
            const next = new Set(prev)
            next.add(targetId)
            return next
        })
        try {
            await deleteDocument(targetId)
            addToast({ type: "success", title: "已删除文档", message: label })
            await loadDocuments()
            await refreshSearchResultsAfterChange()
        } catch (error) {
            addToast({ type: "error", title: "删除文档失败", message: error.message })
        } finally {
            setDeletingDocumentIds((prev) => {
                const next = new Set(prev)
                next.delete(targetId)
                return next
            })
        }
    }

    async function handleCreateDocumentChat(event, doc) {
        if (event?.stopPropagation) event.stopPropagation()
        if (event?.preventDefault) event.preventDefault()
        if (!doc?.id || !collectionId) return
        const docId = doc.id
        setCreatingDocChatIds((prev) => {
            const next = new Set(prev)
            next.add(docId)
            return next
        })
        try {
            const result = await createDocumentChat({
                documentId: docId,
                collectionId,
                title: doc.title || doc.file_name || null,
            })
            const newChatId = result?.id ?? result?.data?.id
            if (newChatId) {
                navigate(`/documents/${docId}/chat/${newChatId}`)
                addToast({ type: "success", title: "已创建文档聊天", message: `Chat #${newChatId}` })
            } else {
                addToast({ type: "info", title: "聊天已创建", message: "请在聊天列表中选择" })
            }
        } catch (error) {
            addToast({ type: "error", title: "创建文档聊天失败", message: error.message })
        } finally {
            setCreatingDocChatIds((prev) => {
                const next = new Set(prev)
                next.delete(docId)
                return next
            })
        }
    }

    function handleDocKeyDown(event, docId) {
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault()
            navigate(`/collections/${collectionId}/documents/${docId}`)
        }
    }

    function handleDocCardClick(event, docId) {
        if (event?.defaultPrevented) return
        const isAction = event?.target?.closest?.(".doc-card__action")
        if (isAction) return
        navigate(`/collections/${collectionId}/documents/${docId}`)
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

    const renderDocumentCard = (doc, keyPrefix = "doc") => {
        const deleting = deletingDocumentIds.has(doc.id)
        const creatingDocChat = creatingDocChatIds.has(doc.id)
        return (
            <div
                key={`${keyPrefix}-${doc.id}`}
                role="button"
                tabIndex={0}
                className="list-item doc-card"
                onClick={(event) => handleDocCardClick(event, doc.id)}
                onKeyDown={(event) => handleDocKeyDown(event, doc.id)}
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
                    <Button
                        variant="tonal"
                        className="doc-card__action"
                        onClick={(event) => handleCreateDocumentChat(event, doc)}
                        disabled={creatingDocChat}
                    >
                        {creatingDocChat ? "创建中..." : "新建 Document Chat"}
                    </Button>
                    <Button
                        variant="ghost"
                        className="doc-card__action danger-link"
                        style={{ color: "var(--color-danger)" }}
                        disabled={deleting}
                        onClick={(event) => handleDeleteDocument(event, doc)}
                    >
                        {deleting ? "删除中..." : "删除"}
                    </Button>
                </div>
            </div>
        )
    }

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
                            </div>
                            <div className="segmented-control">
                                <Button variant="ghost" onClick={openEditModal} disabled={loadingCollection}>
                                    编辑
                                </Button>
                            </div>
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
                                    {documents.map((doc) => renderDocumentCard(doc))}
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
                                    {searchResults.map((doc) => renderDocumentCard(doc, "search"))}
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
                            <div className="segmented-control">
                                <Button variant="ghost" onClick={loadChats} disabled={loadingChats || creatingChat}>
                                    {loadingChats ? "刷新中..." : "刷新"}
                                </Button>
                                <Button onClick={handleCreateChat} disabled={creatingChat || loadingChats}>
                                    {creatingChat ? "创建中..." : "新建聊天"}
                                </Button>
                            </div>
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
                                {chats.map((chat) => {
                                    const deleting = deletingChatIds.has(chat.id)
                                    return (
                                        <div
                                            key={chat.id}
                                            role="button"
                                            tabIndex={0}
                                            className="list-item"
                                            onClick={() => navigate(`/collections/${collectionId}/chat/${chat.id}`)}
                                            onKeyDown={(event) => handleChatCardKeyDown(event, chat.id)}
                                        >
                                            <div>
                                                <strong>{chat.title || `Chat #${chat.id}`}</strong>
                                                <p className="caption">{formatDateTime(chat.created_at)}</p>
                                            </div>
                                            <div className="list-item__meta">
                                                <span className="pill muted">{chat.type}</span>
                                                <Button
                                                    variant="ghost"
                                                    className="danger-link"
                                                    style={{ color: "var(--color-danger)" }}
                                                    disabled={deleting}
                                                    onClick={(event) => handleDeleteChat(event, chat)}
                                                >
                                                    {deleting ? "删除中..." : "删除"}
                                                </Button>
                                            </div>
                                        </div>
                                    )
                                })}
                            </div>
                        )}
                    </div>

                    <div className="card">
                        <div className="card__header">
                            <div>
                                <h3 className="card__title">简单 Collection-RAG</h3>
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

            <DebugIdFooter segments={[{ label: "Collection", value: collection?.id ?? collectionId }]} />

            <Modal
                open={showEditModal}
                title="编辑 Collection"
                onClose={() => setShowEditModal(false)}
                footer={
                    <div className="segmented-control">
                        <Button variant="ghost" onClick={() => setShowEditModal(false)} disabled={savingCollection}>
                            取消
                        </Button>
                        <Button onClick={handleUpdateCollection} disabled={savingCollection}>
                            {savingCollection ? "保存中..." : "保存"}
                        </Button>
                    </div>
                }
            >
                <div className="stack">
                    <label className="input-group">
                        <span className="caption">名称</span>
                        <input
                            className="input"
                            value={editForm.name}
                            onChange={(event) => setEditForm((prev) => ({ ...prev, name: event.target.value }))}
                            placeholder="请输入 Collection 名称"
                        />
                    </label>
                    <label className="input-group">
                        <span className="caption">描述</span>
                        <textarea
                            className="input"
                            rows={3}
                            value={editForm.description}
                            onChange={(event) =>
                                setEditForm((prev) => ({ ...prev, description: event.target.value }))
                            }
                            placeholder="请输入描述（可选）"
                        ></textarea>
                    </label>
                </div>
            </Modal>

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
