import { useEffect, useMemo, useState } from "react"
import { useNavigate } from "react-router-dom"
import { createCollection, healthCheck, listCollections } from "../api/client"
import PageHeader from "../components/layout/PageHeader"
import Button from "../components/ui/Button"
import Modal from "../components/ui/Modal"
import SearchBar from "../components/ui/SearchBar"
import { useToast } from "../components/ui/Toast"

const searchOptions = [
    { label: "按 name 搜索", value: "name" },
    { label: "按 description 搜索", value: "description" },
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

function formatBaseLabel(base) {
    if (!base) return "API 未配置"
    try {
        const url = new URL(base)
        return url.host ?? base
    } catch (error) {
        return base
    }
}

export default function CollectionsHome() {
    const navigate = useNavigate()
    const { addToast } = useToast()

    const [collections, setCollections] = useState([])
    const [loadingCollections, setLoadingCollections] = useState(false)
    const [searchText, setSearchText] = useState("")
    const [searchField, setSearchField] = useState("name")
    const [activeQuery, setActiveQuery] = useState(null)

    const [showModal, setShowModal] = useState(false)
    const [createForm, setCreateForm] = useState({ name: "", description: "" })
    const [creating, setCreating] = useState(false)

    const [healthStatus, setHealthStatus] = useState({ state: "idle", message: "等待检查" })
    const apiBase = (import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:9075/api").replace(/\/+$/, "")

    const healthTone = useMemo(() => {
        if (healthStatus.state === "ok") return "success"
        if (healthStatus.state === "error") return "danger"
        if (healthStatus.state === "checking") return "warn"
        return "muted"
    }, [healthStatus.state])

    useEffect(() => {
        loadCollections()
        runHealthCheck()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [])

    async function loadCollections(params = {}) {
        setLoadingCollections(true)
        try {
            const data = await listCollections(params)
            setCollections(Array.isArray(data) ? data : [])
            if (params.keyword) {
                setActiveQuery({ field: params.searchField || "name", keyword: params.keyword })
            } else {
                setActiveQuery(null)
            }
        } catch (error) {
            addToast({ type: "error", title: "加载 Collection 失败", message: error.message })
        } finally {
            setLoadingCollections(false)
        }
    }

    async function runHealthCheck() {
        setHealthStatus({ state: "checking", message: "检查中..." })
        try {
            const result = await healthCheck()
            if (result?.ok) {
                setHealthStatus({ state: "ok", message: "后端健康" })
            } else {
                setHealthStatus({ state: "error", message: "健康检查未通过" })
                addToast({ type: "error", title: "健康检查失败", message: "返回结果中 ok 未为 true" })
            }
        } catch (error) {
            setHealthStatus({ state: "error", message: error.message })
            addToast({ type: "error", title: "健康检查失败", message: error.message })
        }
    }

    async function handleSearch() {
        const keyword = searchText.trim()
        if (!keyword) {
            addToast({ type: "info", title: "请输入关键字", message: "搜索前请输入 name/description 关键字" })
            setActiveQuery(null)
            await loadCollections()
            return
        }
        await loadCollections({ searchField, keyword })
    }

    async function handleReset() {
        setSearchText("")
        setActiveQuery(null)
        await loadCollections()
    }

    async function handleCreateCollection() {
        setCreating(true)
        try {
            const result = await createCollection(createForm)
            addToast({
                type: "success",
                title: "创建成功",
                message: `已创建 Collection ${result?.name ?? createForm.name}`,
            })
            setShowModal(false)
            setCreateForm({ name: "", description: "" })
            const query = activeQuery ? { searchField: activeQuery.field, keyword: activeQuery.keyword } : {}
            await loadCollections(query)
        } catch (error) {
            addToast({ type: "error", title: "创建失败", message: error.message })
        } finally {
            setCreating(false)
        }
    }

    const isEmpty = !loadingCollections && (collections?.length ?? 0) === 0

    return (
        <>
            <PageHeader
                breadcrumbs={[{ label: "Home" }]}
                title="知识库主页"
                subtitle="按 name/description 搜索或创建 Collection，真实数据来源于后端 /api/collections。"
                actions={
                    <Button onClick={() => setShowModal(true)}>
                        + 新建 Collection
                    </Button>
                }
            />

            <div className="grid two-column">
                <div className="stack">
                    <div className="card splash">
                        <div className="card__header">
                            <div>
                                <h3 className="card__title">查找 Collection</h3>
                                <p className="caption">支持按 name/description 模糊搜索，结果与后端保持一致。</p>
                            </div>
                            <span className="tag">M5b DoD</span>
                        </div>
                        <SearchBar
                            value={searchText}
                            onChange={setSearchText}
                            filterValue={searchField}
                            onFilterChange={setSearchField}
                            filterOptions={searchOptions}
                            onSubmit={handleSearch}
                            onReset={handleReset}
                            placeholder="按 name / description 搜索 Collection"
                            loading={loadingCollections}
                        />
                        {activeQuery && (
                            <div className="search-meta">
                                <span className="tag">Searched result</span>
                                <span className="caption">
                                    按 {activeQuery.field} 搜索 “{activeQuery.keyword}”，共 {collections.length} 条
                                </span>
                            </div>
                        )}
                    </div>

                    {loadingCollections && (
                        <div className="card">
                            <div className="inline-kv">
                                <span className="status-dot" style={{ background: "var(--color-brand)" }}></span>
                                <strong>加载中...</strong>
                                <span className="caption">正在读取最新的 collections 列表</span>
                            </div>
                        </div>
                    )}

                    {isEmpty && (
                        <div className="card">
                            <div className="empty-state">
                                <p>暂无 Collection，可点击右上角“新建 Collection”完成首次创建。</p>
                                <Button onClick={() => setShowModal(true)}>去创建</Button>
                            </div>
                        </div>
                    )}

                    {!loadingCollections && collections.length > 0 && (
                        <div className="collection-grid">
                            {collections.map((item) => (
                                <button
                                    key={item.id}
                                    type="button"
                                    className="collection-card"
                                    onClick={() => navigate(`/collections/${item.id}`)}
                                >
                                    <div className="collection-card__meta">
                                        <div className="collection-card__name" title={item.name}>
                                            {item.name}
                                        </div>
                                        <div className="caption" title={item.created_at}>
                                            {formatDateTime(item.created_at)}
                                        </div>
                                    </div>
                                    <p className="collection-card__desc" title={item.description || "暂无描述"}>
                                        {item.description || "暂无描述"}
                                    </p>
                                    <div className="collection-card__footer">
                                        <span className="status-dot" style={{ background: "var(--color-brand)" }}></span>
                                        <span className="caption">点击进入 Collection 管理页</span>
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                <div className="stack">
                    <div className="card">
                        <div className="card__header">
                            <div>
                                <h3 className="card__title">系统状态</h3>
                                <p className="caption">健康检查旁路 /healthz，显示当前 API 基址。</p>
                            </div>
                            <Button variant="ghost" onClick={runHealthCheck}>
                                重新检查
                            </Button>
                        </div>
                        <div className="inline-kv" style={{ marginBottom: "var(--space-2)" }}>
                            <span
                                className="status-dot"
                                style={{
                                    background:
                                        healthTone === "success"
                                            ? "var(--color-success)"
                                            : healthTone === "danger"
                                            ? "var(--color-danger)"
                                            : healthTone === "warn"
                                            ? "var(--color-warning)"
                                            : "var(--color-ink-soft)",
                                }}
                            ></span>
                            <strong>{healthStatus.state === "ok" ? "Backend OK" : "Backend"}</strong>
                            <span className="caption">{healthStatus.message || "等待检查"}</span>
                        </div>
                        <div className="stack">
                            <div className="inline-kv">
                                <strong>API Base</strong>
                                <span className="caption">{formatBaseLabel(apiBase)}</span>
                            </div>
                            <div className="inline-kv">
                                <strong>搜索提示</strong>
                                <span className="caption">支持 name / description 模糊匹配，Reset 恢复全量列表。</span>
                            </div>
                        </div>
                    </div>

                    <div className="card">
                        <div className="card__header">
                            <div>
                                <h3 className="card__title">设计稿对齐</h3>
                                <p className="caption">依照 dependency/frontUI_design 的信息架构与色板落地。</p>
                            </div>
                        </div>
                        <ul className="list">
                            <li className="list-item">
                                <div>
                                    <strong>列表真实读取</strong>
                                    <p className="caption">从 /api/collections 获取最新数据，含 created_at/description 截断展示。</p>
                                </div>
                                <span className="pill success">已完成</span>
                            </li>
                            <li className="list-item">
                                <div>
                                    <strong>搜索 + Reset</strong>
                                    <p className="caption">显示 “Searched result” 标签，Reset 清除过滤并重新请求。</p>
                                </div>
                                <span className="pill success">可用</span>
                            </li>
                            <li className="list-item">
                                <div>
                                    <strong>新建 Collection</strong>
                                    <p className="caption">Modal 校验必填，提交后 toast 提示并刷新列表。</p>
                                </div>
                                <span className="pill success">联通</span>
                            </li>
                        </ul>
                    </div>
                </div>
            </div>

            <Modal
                open={showModal}
                title="新建 Collection"
                description="填写名称与描述后提交，后端将返回新的 collection 记录。"
                onClose={() => !creating && setShowModal(false)}
                footer={
                    <>
                        <Button type="button" variant="ghost" onClick={() => setShowModal(false)} disabled={creating}>
                            取消
                        </Button>
                        <Button type="button" onClick={handleCreateCollection} disabled={creating || !createForm.name.trim()}>
                            {creating ? "创建中..." : "创建"}
                        </Button>
                    </>
                }
            >
                <div className="stack">
                    <label className="caption" htmlFor="newCollectionName">
                        Collection name
                    </label>
                    <input
                        id="newCollectionName"
                        className="input"
                        value={createForm.name}
                        onChange={(event) => setCreateForm((prev) => ({ ...prev, name: event.target.value }))}
                        placeholder="必填"
                        required
                    />
                    <label className="caption" htmlFor="newCollectionDesc">
                        Description
                    </label>
                    <textarea
                        id="newCollectionDesc"
                        className="input"
                        rows={3}
                        value={createForm.description}
                        onChange={(event) =>
                            setCreateForm((prev) => ({ ...prev, description: event.target.value }))
                        }
                        placeholder="用于展示与搜索的摘要"
                    ></textarea>
                </div>
            </Modal>
        </>
    )
}
