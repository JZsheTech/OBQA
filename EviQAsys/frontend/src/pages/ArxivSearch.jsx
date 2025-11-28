import { useMemo, useState } from "react"
import { searchArxiv, saveArxivFavorite } from "../api/client"
import PageHeader from "../components/layout/PageHeader"
import Button from "../components/ui/Button"
import Modal from "../components/ui/Modal"
import { useToast } from "../components/ui/Toast"

const sortOptions = [
    { label: "相关性", value: "relevance" },
    { label: "提交时间", value: "submittedDate" },
    { label: "更新时间", value: "lastUpdatedDate" },
]

function formatDate(value) {
    if (!value) return "—"
    try {
        return new Date(value).toLocaleDateString()
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

function parseArxivFromValue(value) {
    if (!value) return { id: "", version: null }
    const str = String(value)
    const modern = str.match(/(?<id>\d{4}\.\d{4,5})(?<ver>v\d+)?/)
    if (modern?.groups?.id) {
        return { id: modern.groups.id, version: modern.groups.ver || null }
    }
    const legacy = str.match(/(?<id>[a-z-]+\/\d{7})(?<ver>v\d+)?/i)
    if (legacy?.groups?.id) {
        return { id: legacy.groups.id, version: legacy.groups.ver || null }
    }
    return { id: "", version: null }
}

function buildAbsUrl(arxivId, version) {
    if (!arxivId) return null
    return `https://arxiv.org/abs/${arxivId}${version ?? ""}`
}

function buildPdfUrl(arxivId, version) {
    if (!arxivId) return null
    return `https://arxiv.org/pdf/${arxivId}${version ?? ""}`
}

function normalizePaper(raw) {
    const baseId = normalizeText(raw?.arxiv_id) || ""
    const parsedFromId = parseArxivFromValue(baseId)
    const parsedFromLink = parseArxivFromValue(raw?.abs_url || raw?.pdf_url || raw?.id)
    const arxivId = parsedFromId.id || parsedFromLink.id || ""
    const version = raw?.version || parsedFromId.version || parsedFromLink.version || null
    const title = normalizeText(raw?.title) || raw?.title || ""
    const summary = normalizeText(raw?.summary)
    const absUrl = raw?.abs_url || buildAbsUrl(arxivId, version) || null
    const pdfUrl = raw?.pdf_url || buildPdfUrl(arxivId, version) || null
    return {
        ...raw,
        arxiv_id: arxivId,
        version,
        title,
        summary,
        abs_url: absUrl,
        pdf_url: pdfUrl,
    }
}

function summarize(text, length = 180) {
    const normalized = normalizeText(text)
    if (!normalized) return "暂无摘要"
    return normalized.length > length ? `${normalized.slice(0, length)}…` : normalized
}

export default function ArxivSearch() {
    const { addToast } = useToast()
    const [form, setForm] = useState({
        allTerms: "",
        title: "",
        abstract: "",
        author: "",
        categories: "",
        dateMode: "",
        dateFrom: "",
        dateTo: "",
        sortBy: "relevance",
        sortOrder: "descending",
        maxResults: 10,
    })
    const [results, setResults] = useState([])
    const [loading, setLoading] = useState(false)
    const [savingId, setSavingId] = useState(null)
    const [lastQuery, setLastQuery] = useState(null)
    const [detailPaper, setDetailPaper] = useState(null)

    const hasQuery = useMemo(() => {
        return (
            form.allTerms.trim() ||
            form.title.trim() ||
            form.abstract.trim() ||
            form.author.trim() ||
            form.categories.trim()
        )
    }, [form.abstract, form.allTerms, form.author, form.categories, form.title])

    function updateForm(field, value) {
        setForm((prev) => ({ ...prev, [field]: value }))
    }

    async function handleSearch() {
        const categories = form.categories
            .split(",")
            .map((entry) => entry.trim())
            .filter(Boolean)
        const payload = {
            allTerms: form.allTerms.trim(),
            title: form.title.trim(),
            abstract: form.abstract.trim(),
            author: form.author.trim(),
            categories,
            dateMode: form.dateMode || null,
            dateFrom: form.dateFrom || null,
            dateTo: form.dateTo || null,
            sortBy: form.sortBy,
            sortOrder: form.sortOrder,
            maxResults: Number(form.maxResults) || 10,
        }
        setLoading(true)
        try {
            const data = await searchArxiv(payload)
            const normalized = (data?.items || []).map(normalizePaper)
            setResults(normalized)
            setLastQuery({
                keyword:
                    payload.allTerms ||
                    payload.title ||
                    payload.abstract ||
                    payload.author ||
                    payload.categories?.join(", "),
                count: normalized.length ?? 0,
            })
        } catch (error) {
            addToast({ type: "error", title: "arXiv 搜索失败", message: error.message })
        } finally {
            setLoading(false)
        }
    }

    async function handleSaveFavorite(paper) {
        if (!paper?.arxiv_id) {
            addToast({ type: "error", title: "收藏失败", message: "缺少 arxiv_id" })
            return
        }
        setSavingId(paper.arxiv_id)
        try {
            await saveArxivFavorite({ paper })
            addToast({ type: "success", title: "已加入收藏夹", message: paper.title })
        } catch (error) {
            addToast({ type: "error", title: "收藏失败", message: error.message })
        } finally {
            setSavingId(null)
        }
    }

    function handleCardClick(event, paper) {
        if (event.target.closest("button, a")) return
        setDetailPaper(paper)
    }

    return (
        <>
            <PageHeader
                breadcrumbs={[
                    { label: "Home", to: "/" },
                    { label: "arXiv 搜索" },
                ]}
                title="arXiv 论文检索"
                subtitle="按标题、作者或分类检索 arXiv，并将结果收藏到本地收藏夹"
            />

            <div className="grid two-column">
                <div className="card">
                    <div className="card__header">
                        <div>
                            <h3 className="card__title">检索条件</h3>
                            <p className="caption">支持组合字段检索，未填写时默认按“all”检索</p>
                        </div>
                        <Button onClick={handleSearch} disabled={loading}>
                            {loading ? "搜索中..." : "搜索"}
                        </Button>
                    </div>
                    <div className="form-grid">
                        <label className="form-field">
                            <span className="form-label">关键词（all:）</span>
                            <input
                                type="text"
                                value={form.allTerms}
                                onChange={(event) => updateForm("allTerms", event.target.value)}
                                placeholder="如：large language model"
                            />
                        </label>
                        <label className="form-field">
                            <span className="form-label">标题包含（ti:）</span>
                            <input
                                type="text"
                                value={form.title}
                                onChange={(event) => updateForm("title", event.target.value)}
                                placeholder="可选：精确匹配标题片段"
                            />
                        </label>
                        <label className="form-field">
                            <span className="form-label">摘要包含（abs:）</span>
                            <input
                                type="text"
                                value={form.abstract}
                                onChange={(event) => updateForm("abstract", event.target.value)}
                                placeholder="可选：按摘要关键词检索"
                            />
                        </label>
                        <label className="form-field">
                            <span className="form-label">作者（au:）</span>
                            <input
                                type="text"
                                value={form.author}
                                onChange={(event) => updateForm("author", event.target.value)}
                                placeholder="例如：Yann LeCun"
                            />
                        </label>
                        <label className="form-field">
                            <span className="form-label">分类（cat:，逗号分隔）</span>
                            <input
                                type="text"
                                value={form.categories}
                                onChange={(event) => updateForm("categories", event.target.value)}
                                placeholder="如：cs.AI, cs.CL"
                            />
                        </label>
                        <label className="form-field">
                            <span className="form-label">时间模式</span>
                            <select
                                value={form.dateMode}
                                onChange={(event) => updateForm("dateMode", event.target.value)}
                            >
                                <option value="">不限</option>
                                <option value="submitted">提交日期</option>
                                <option value="updated">更新日期</option>
                            </select>
                        </label>
                        <label className="form-field">
                            <span className="form-label">开始日期</span>
                            <input
                                type="date"
                                value={form.dateFrom}
                                onChange={(event) => updateForm("dateFrom", event.target.value)}
                            />
                        </label>
                        <label className="form-field">
                            <span className="form-label">结束日期</span>
                            <input
                                type="date"
                                value={form.dateTo}
                                onChange={(event) => updateForm("dateTo", event.target.value)}
                            />
                        </label>
                        <label className="form-field">
                            <span className="form-label">排序</span>
                            <select
                                value={form.sortBy}
                                onChange={(event) => updateForm("sortBy", event.target.value)}
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
                                value={form.sortOrder}
                                onChange={(event) => updateForm("sortOrder", event.target.value)}
                            >
                                <option value="descending">降序</option>
                                <option value="ascending">升序</option>
                            </select>
                        </label>
                        <label className="form-field">
                            <span className="form-label">最大返回条数</span>
                            <input
                                type="number"
                                min={1}
                                max={50}
                                value={form.maxResults}
                                onChange={(event) => updateForm("maxResults", event.target.value)}
                            />
                        </label>
                    </div>
                    <div className="card__footer">
                        <div className="muted">
                            {!hasQuery
                                ? "未填写检索条件时，将使用默认 all:electron 查询"
                                : "可组合多字段提升精确度"}
                        </div>
                    </div>
                </div>

                <div className="card">
                    <div className="card__header">
                        <div>
                            <h3 className="card__title">检索结果</h3>
                            <p className="caption">
                                {lastQuery ? `当前展示 ${lastQuery.count} 条结果` : "等待检索..."}
                            </p>
                        </div>
                    </div>

                    {loading ? (
                        <div className="empty-state">正在从 arXiv 获取结果，请稍候...</div>
                    ) : results.length === 0 ? (
                        <div className="empty-state">
                            {hasQuery ? "尚无匹配结果，请调整检索条件。" : "填写条件后点击“搜索”开始检索。"}
                        </div>
                    ) : (
                        <div className="stack">
                            {results.map((paper, index) => (
                                <article
                                    key={`${paper.arxiv_id || paper.id || paper.abs_url || index}-${paper.version || ""}`}
                                    className="list-card list-card--clickable"
                                    role="button"
                                    tabIndex={0}
                                    onClick={(event) => handleCardClick(event, paper)}
                                    onKeyDown={(event) => {
                                        if (event.key === "Enter" && !event.target.closest("button, a")) {
                                            setDetailPaper(paper)
                                        }
                                    }}
                                >
                                    <header className="list-card__header">
                                        <div>
                                            <div className="badge">{paper.primary_category || "未分组"}</div>
                                            <h4 className="list-card__title">{paper.title || paper.arxiv_id || "未提供标题"}</h4>
                                            <p className="muted">
                                                {paper.arxiv_id}
                                                {paper.version ? ` · ${paper.version}` : ""}
                                            </p>
                                        </div>
                                        <div className="list-card__actions">
                                            {paper.pdf_url && (
                                                <a
                                                    className="btn btn-tonal"
                                                    href={paper.pdf_url}
                                                    target="_blank"
                                                    rel="noreferrer"
                                                >
                                                    PDF
                                                </a>
                                            )}
                                            {paper.abs_url && (
                                                <a
                                                    className="btn btn-ghost"
                                                    href={paper.abs_url}
                                                    target="_blank"
                                                    rel="noreferrer"
                                                >
                                                    arXiv
                                                </a>
                                            )}
                                            <Button
                                                onClick={(event) => {
                                                    event.stopPropagation()
                                                    handleSaveFavorite(paper)
                                                }}
                                                disabled={savingId === paper.arxiv_id}
                                            >
                                                {savingId === paper.arxiv_id ? "处理中..." : "加入收藏夹"}
                                            </Button>
                                        </div>
                                    </header>
                                    <div className="list-card__meta">
                                        <span>作者：{formatAuthorsCompact(paper.authors)}</span>
                                        <span>分类：{formatList(paper.categories)}</span>
                                        <span>
                                            发布时间：{formatDate(paper.published)} · 更新：{formatDate(paper.updated)}
                                        </span>
                                    </div>
                                    <p className="list-card__summary">
                                        {summarize(paper.summary)}
                                    </p>
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
