import { useEffect, useMemo, useState } from "react"
import {
    deleteArxivFavorite,
    importArxivFavorite,
    listArxivFavorites,
    listCollections,
    updateArxivFavorite,
} from "../api/client"
import PageHeader from "../components/layout/PageHeader"
import Button from "../components/ui/Button"
import Modal from "../components/ui/Modal"
import { useToast } from "../components/ui/Toast"

const sortOptions = [
    { label: "创建时间", value: "created_at" },
    { label: "发布时间", value: "published" },
    { label: "更新时间", value: "updated" },
]

function formatDate(value) {
    if (!value) return "—"
    try {
        return new Date(value).toLocaleString()
    } catch {
        return value
    }
}

function formatList(list) {
    if (!list || list.length === 0) return "—"
    return list.join(", ")
}

function truncateText(text, length = 140) {
    const normalized = normalizeText(text)
    if (!normalized) return "—"
    return normalized.length > length ? `${normalized.slice(0, length)}…` : normalized
}

function formatAuthorsCompact(list, length = 140) {
    if (!list || list.length === 0) return "—"
    return truncateText(list.join(", "), length)
}

function normalizeText(value) {
    if (typeof value !== "string") return ""
    return value.replace(/\s+/g, " ").trim()
}

function summarize(text, length = 180) {
    const normalized = normalizeText(text)
    if (!normalized) return "暂无摘要"
    return normalized.length > length ? `${normalized.slice(0, length)}…` : normalized
}

export default function ArxivFavorites() {
    const { addToast } = useToast()
    const [favorites, setFavorites] = useState([])
    const [pageInfo, setPageInfo] = useState({ page: 1, pageSize: 10, total: 0 })
    const [filters, setFilters] = useState({
        keyword: "",
        author: "",
        category: "",
        tag: "",
        sortBy: "created_at",
        sortOrder: "desc",
    })
    const [editMap, setEditMap] = useState({})
    const [loading, setLoading] = useState(false)
    const [importingId, setImportingId] = useState(null)
    const [savingId, setSavingId] = useState(null)
    const [collections, setCollections] = useState([])
    const [targetCollectionId, setTargetCollectionId] = useState("")
    const [detailPaper, setDetailPaper] = useState(null)

    const totalPages = useMemo(() => {
        if (!pageInfo.pageSize) return 1
        return Math.max(1, Math.ceil(pageInfo.total / pageInfo.pageSize))
    }, [pageInfo.pageSize, pageInfo.total])

    useEffect(() => {
        loadCollections()
        loadFavorites(1)
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    async function loadCollections() {
        try {
            const data = await listCollections()
            setCollections(Array.isArray(data) ? data : [])
            if (!targetCollectionId && Array.isArray(data) && data.length > 0) {
                setTargetCollectionId(data[0].id)
            }
        } catch (error) {
            addToast({ type: "error", title: "加载 Collection 失败", message: error.message })
        }
    }

    async function loadFavorites(page = pageInfo.page) {
        setLoading(true)
        try {
            const data = await listArxivFavorites({
                page,
                pageSize: pageInfo.pageSize,
                keyword: filters.keyword.trim() || undefined,
                author: filters.author.trim() || undefined,
                category: filters.category.trim() || undefined,
                tag: filters.tag.trim() || undefined,
                sortBy: filters.sortBy,
                sortOrder: filters.sortOrder,
            })
            setFavorites(data?.items || [])
            setPageInfo({
                page: data?.page ?? page,
                pageSize: data?.page_size ?? pageInfo.pageSize,
                total: data?.total ?? 0,
            })
            const nextEdit = {}
            ;(data?.items || []).forEach((item) => {
                nextEdit[item.id] = { tags: item.tags ?? "", note: item.note ?? "" }
            })
            setEditMap(nextEdit)
        } catch (error) {
            addToast({ type: "error", title: "加载收藏夹失败", message: error.message })
        } finally {
            setLoading(false)
        }
    }

    function handleFilterChange(field, value) {
        setFilters((prev) => ({ ...prev, [field]: value }))
    }

    async function handleApplyFilters() {
        await loadFavorites(1)
    }

    async function handleResetFilters() {
        setFilters({
            keyword: "",
            author: "",
            category: "",
            tag: "",
            sortBy: "created_at",
            sortOrder: "desc",
        })
        await loadFavorites(1)
    }

    async function handleSaveMeta(itemId) {
        const payload = editMap[itemId] ?? {}
        if (payload.tags === undefined && payload.note === undefined) {
            addToast({ type: "info", title: "无需保存", message: "未修改 tags 或 note" })
            return
        }
        setSavingId(itemId)
        try {
            await updateArxivFavorite(itemId, { tags: payload.tags, note: payload.note })
            addToast({ type: "success", title: "已保存备注", message: `#${itemId}` })
            await loadFavorites(pageInfo.page)
        } catch (error) {
            addToast({ type: "error", title: "保存失败", message: error.message })
        } finally {
            setSavingId(null)
        }
    }

    async function handleDelete(item) {
        const confirmed = window.confirm(`确定删除收藏的论文 "${item.title}" 吗？`)
        if (!confirmed) return
        try {
            await deleteArxivFavorite(item.id)
            addToast({ type: "success", title: "已删除收藏", message: item.title })
            await loadFavorites(1)
        } catch (error) {
            addToast({ type: "error", title: "删除失败", message: error.message })
        }
    }

    async function handleImport(item) {
        if (item.document_id) {
            addToast({ type: "info", title: "已导入", message: `Document #${item.document_id}` })
            return
        }
        const collectionId = Number(targetCollectionId)
        if (!Number.isFinite(collectionId)) {
            addToast({ type: "warning", title: "请选择 Collection", message: "导入前请先选择集合" })
            return
        }
        setImportingId(item.id)
        try {
            await importArxivFavorite(item.id, { collectionId })
            addToast({
                type: "success",
                title: "导入已提交",
                message: `已导入到 Collection #${collectionId}`,
            })
            await loadFavorites(pageInfo.page)
        } catch (error) {
            addToast({ type: "error", title: "导入失败", message: error.message })
        } finally {
            setImportingId(null)
        }
    }

    function handleCardClick(event, paper) {
        if (event.target.closest("button, a, input, textarea, select")) return
        setDetailPaper(paper)
    }

    function renderPagination() {
        return (
            <div className="list-item__meta" style={{ justifyContent: "flex-end" }}>
                <span>
                    第 {pageInfo.page} / {totalPages} 页 · 共 {pageInfo.total} 条
                </span>
                <div className="search-bar__actions">
                    <Button
                        variant="ghost"
                        onClick={() => loadFavorites(Math.max(1, pageInfo.page - 1))}
                        disabled={loading || pageInfo.page <= 1}
                    >
                        上一页
                    </Button>
                    <Button
                        variant="ghost"
                        onClick={() => loadFavorites(pageInfo.page + 1)}
                        disabled={loading || pageInfo.page >= totalPages}
                    >
                        下一页
                    </Button>
                </div>
            </div>
        )
    }

    return (
        <>
            <PageHeader
                breadcrumbs={[
                    { label: "Home", to: "/" },
                    { label: "arXiv 收藏夹" },
                ]}
                title="arXiv 收藏夹"
                subtitle="管理已收藏的 arXiv 论文，并将其导入到问答系统"
            />

            <div className="grid two-column">
                <div className="card">
                    <div className="card__header">
                        <div>
                            <h3 className="card__title">筛选与排序</h3>
                            <p className="caption">按关键词、作者、标签快速定位收藏</p>
                        </div>
                        <div className="search-bar__actions">
                            <Button variant="ghost" onClick={handleResetFilters} disabled={loading}>
                                重置
                            </Button>
                            <Button onClick={handleApplyFilters} disabled={loading}>
                                应用筛选
                            </Button>
                        </div>
                    </div>
                    <div className="form-grid">
                        <label className="form-field">
                            <span className="form-label">关键词（标题/摘要）</span>
                            <input
                                type="text"
                                value={filters.keyword}
                                onChange={(event) => handleFilterChange("keyword", event.target.value)}
                                placeholder="支持模糊搜索"
                            />
                        </label>
                        <label className="form-field">
                            <span className="form-label">作者包含</span>
                            <input
                                type="text"
                                value={filters.author}
                                onChange={(event) => handleFilterChange("author", event.target.value)}
                                placeholder="作者子串"
                            />
                        </label>
                        <label className="form-field">
                            <span className="form-label">分类包含</span>
                            <input
                                type="text"
                                value={filters.category}
                                onChange={(event) => handleFilterChange("category", event.target.value)}
                                placeholder="如：cs.AI"
                            />
                        </label>
                        <label className="form-field">
                            <span className="form-label">标签包含</span>
                            <input
                                type="text"
                                value={filters.tag}
                                onChange={(event) => handleFilterChange("tag", event.target.value)}
                                placeholder="收藏 tags/note"
                            />
                        </label>
                        <label className="form-field">
                            <span className="form-label">排序字段</span>
                            <select
                                value={filters.sortBy}
                                onChange={(event) => handleFilterChange("sortBy", event.target.value)}
                            >
                                {sortOptions.map((option) => (
                                    <option key={option.value} value={option.value}>
                                        {option.label}
                                    </option>
                                ))}
                            </select>
                        </label>
                        <label className="form-field">
                            <span className="form-label">排序方向</span>
                            <select
                                value={filters.sortOrder}
                                onChange={(event) => handleFilterChange("sortOrder", event.target.value)}
                            >
                                <option value="desc">降序</option>
                                <option value="asc">升序</option>
                            </select>
                        </label>
                    </div>
                    <div className="card__footer">
                        <div className="inline-kv">
                            <strong>导入目标 Collection</strong>
                            <select
                                className="input"
                                value={targetCollectionId}
                                onChange={(event) => setTargetCollectionId(event.target.value)}
                            >
                                {collections.length === 0 && <option value="">暂无 Collection</option>}
                                {collections.map((col) => (
                                    <option key={col.id} value={col.id}>
                                        #{col.id} · {col.name}
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>
                </div>

                <div className="card">
                    <div className="card__header">
                        <div>
                            <h3 className="card__title">收藏列表</h3>
                            <p className="caption">共 {pageInfo.total} 条收藏</p>
                        </div>
                        {renderPagination()}
                    </div>

                    {loading ? (
                        <div className="empty-state">加载中...</div>
                    ) : favorites.length === 0 ? (
                        <div className="empty-state">暂无收藏，先在“arXiv 搜索”中添加吧。</div>
                    ) : (
                        <div className="stack">
                            {favorites.map((item) => (
                                <article
                                    key={item.id}
                                    className="list-card list-card--clickable"
                                    role="button"
                                    tabIndex={0}
                                    onClick={(event) => handleCardClick(event, item)}
                                    onKeyDown={(event) => {
                                        if (event.key === "Enter" && !event.target.closest("button, a, input, textarea, select")) {
                                            setDetailPaper(item)
                                        }
                                    }}
                                >
                                    <header className="list-card__header">
                                        <div>
                                            <div className="badge">#{item.arxiv_id}</div>
                                            <h4 className="list-card__title">{item.title}</h4>
                                            <p className="caption">
                                                {item.primary_category || "未分组"} · {formatDate(item.published)}
                                            </p>
                                        </div>
                                        <div className="list-card__actions">
                                            <Button
                                                variant="tonal"
                                                onClick={() => handleImport(item)}
                                                disabled={importingId === item.id || item.document_id}
                                            >
                                                {item.document_id
                                                    ? `已导入 Doc #${item.document_id}`
                                                    : importingId === item.id
                                                        ? "导入中..."
                                                        : "导入到 Collection"}
                                            </Button>
                                            <Button
                                                variant="ghost"
                                                onClick={() => handleDelete(item)}
                                            >
                                                删除
                                            </Button>
                                        </div>
                                    </header>
                                    <div className="list-card__meta">
                                        <span>作者：{formatAuthorsCompact(item.authors)}</span>
                                        <span>分类：{formatList(item.categories)}</span>
                                        <span>更新：{formatDate(item.updated)}</span>
                                        {item.document_id && (
                                            <span className="pill success">
                                                已关联 Document #{item.document_id}
                                                {item.document_collection_id ? ` · Collection #${item.document_collection_id}` : ""}
                                            </span>
                                        )}
                                    </div>
                                    <p className="list-card__summary">{summarize(item.summary)}</p>
                                    <div className="form-grid" style={{ marginTop: "12px" }}>
                                        <label className="form-field">
                                            <span className="form-label">Tags</span>
                                            <input
                                                type="text"
                                                value={editMap[item.id]?.tags ?? ""}
                                                onChange={(event) =>
                                                    setEditMap((prev) => ({
                                                        ...prev,
                                                        [item.id]: {
                                                            ...prev[item.id],
                                                            tags: event.target.value,
                                                        },
                                                    }))
                                                }
                                            />
                                        </label>
                                        <label className="form-field" style={{ gridColumn: "span 2" }}>
                                            <span className="form-label">Note</span>
                                            <textarea
                                                value={editMap[item.id]?.note ?? ""}
                                                onChange={(event) =>
                                                    setEditMap((prev) => ({
                                                        ...prev,
                                                        [item.id]: {
                                                            ...prev[item.id],
                                                            note: event.target.value,
                                                        },
                                                    }))
                                                }
                                            />
                                        </label>
                                    </div>
                                    <div className="list-card__actions">
                                        <Button
                                            variant="tonal"
                                            onClick={() => handleSaveMeta(item.id)}
                                            disabled={savingId === item.id}
                                        >
                                            {savingId === item.id ? "保存中..." : "保存备注"}
                                        </Button>
                                        {item.abs_url && (
                                            <a
                                                className="btn btn-ghost"
                                                href={item.abs_url}
                                                target="_blank"
                                                rel="noreferrer"
                                            >
                                                查看 arXiv
                                            </a>
                                        )}
                                        {item.pdf_url && (
                                            <a
                                                className="btn btn-tonal"
                                                href={item.pdf_url}
                                                target="_blank"
                                                rel="noreferrer"
                                            >
                                                PDF
                                            </a>
                                        )}
                                    </div>
                                </article>
                            ))}
                        </div>
                    )}
                </div>
            </div>
            <Modal
                open={!!detailPaper}
                title={detailPaper?.title || detailPaper?.arxiv_id || "论文详情"}
                description={detailPaper?.arxiv_id ? `arXiv ID: ${detailPaper.arxiv_id}` : undefined}
                onClose={() => setDetailPaper(null)}
                footer={
                    detailPaper && (
                        <>
                            {detailPaper.abs_url && (
                                <a className="btn btn-ghost" href={detailPaper.abs_url} target="_blank" rel="noreferrer">
                                    查看 arXiv
                                </a>
                            )}
                            {detailPaper.pdf_url && (
                                <a className="btn btn-tonal" href={detailPaper.pdf_url} target="_blank" rel="noreferrer">
                                    PDF
                                </a>
                            )}
                            <Button onClick={() => setDetailPaper(null)}>关闭</Button>
                        </>
                    )
                }
            >
                {detailPaper && (
                    <div className="stack">
                        <div className="list-card__meta" style={{ marginTop: 0 }}>
                            <span>分类：{formatList(detailPaper.categories)}</span>
                        </div>
                        <div className="list-card__meta" style={{ marginTop: 0 }}>
                            <span>发布时间：{formatDate(detailPaper.published)}</span>
                            <span>更新：{formatDate(detailPaper.updated)}</span>
                        </div>
                        <p className="muted" style={{ margin: 0 }}>作者</p>
                        <div className="modal__authors">
                            {formatList(detailPaper.authors)}
                        </div>
                        <p className="muted" style={{ margin: 0 }}>摘要</p>
                        <div className="modal__summary">
                            {detailPaper.summary || "暂无摘要"}
                        </div>
                    </div>
                )}
            </Modal>
        </>
    )
}
