import { useEffect, useMemo, useState } from "react"
import { healthCheck, listDocuments, uploadDocument } from "../api/client"
import UploadForm from "../components/UploadForm"
import DocumentList from "../components/DocumentList"
import PageHeader from "../components/layout/PageHeader"
import Button from "../components/ui/Button"
import Drawer from "../components/ui/Drawer"
import Modal from "../components/ui/Modal"
import SearchBar from "../components/ui/SearchBar"
import { useToast } from "../components/ui/Toast"

const skeletonRoutes = [
    { label: "Collection 管理页", path: "/collections/:collectionId" },
    { label: "Document 管理页", path: "/collections/:collectionId/documents/:documentId" },
    { label: "Collection Chat", path: "/collections/:collectionId/chat/:chatId" },
    { label: "Document Chat", path: "/documents/:documentId/chat/:chatId" },
    { label: "Chat 历史", path: "/chat-history" },
]

export default function CollectionsHome() {
    const [healthStatus, setHealthStatus] = useState({ state: "idle", message: "" })
    const [collectionId, setCollectionId] = useState("")
    const [documents, setDocuments] = useState([])
    const [isLoadingDocs, setIsLoadingDocs] = useState(false)
    const [isUploading, setIsUploading] = useState(false)
    const [searchText, setSearchText] = useState("")
    const [searchFilter, setSearchFilter] = useState("name")
    const [showModal, setShowModal] = useState(false)
    const [showDrawer, setShowDrawer] = useState(false)
    const [newCollectionForm, setNewCollectionForm] = useState({ name: "", description: "" })
    const { addToast } = useToast()

    const quickStatusTone = useMemo(() => {
        if (healthStatus.state === "ok") return "success"
        if (healthStatus.state === "error") return "danger"
        if (healthStatus.state === "checking") return "warn"
        return "muted"
    }, [healthStatus.state])

    useEffect(() => {
        runHealthCheck()
    }, [])

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

    async function refreshDocuments() {
        if (!collectionId) {
            addToast({ type: "error", title: "缺少 Collection ID", message: "请输入 Collection ID 后重试" })
            return
        }
        setIsLoadingDocs(true)
        try {
            const data = await listDocuments(collectionId)
            setDocuments(data ?? [])
            if (!data || data.length === 0) {
                addToast({ type: "info", title: "暂无文档", message: "列表为空，尝试上传一个 PDF" })
            }
        } catch (error) {
            addToast({ type: "error", title: "加载文档失败", message: error.message })
        } finally {
            setIsLoadingDocs(false)
        }
    }

    async function handleUpload(file) {
        if (!collectionId) {
            addToast({ type: "error", title: "缺少 Collection ID", message: "上传前请先输入 Collection ID" })
            return
        }
        setIsUploading(true)
        try {
            const result = await uploadDocument(collectionId, file)
            addToast({
                type: "success",
                title: "上传完成",
                message: `已上传 ${result?.file_name ?? file.name}`,
            })
            await refreshDocuments()
        } catch (error) {
            addToast({ type: "error", title: "上传失败", message: error.message })
        } finally {
            setIsUploading(false)
        }
    }

    function handlePlanSearch() {
        addToast({
            type: "info",
            title: "规划中的功能",
            message: `将在 M5b 对接 ${searchFilter} 搜索，当前输入：${searchText || "空"}`,
        })
    }

    function handleCreateCollection() {
        setShowModal(false)
        addToast({
            type: "info",
            title: "占位提交",
            message: "创建 Collection 的后端接口将在 M5b 对接",
        })
        setNewCollectionForm({ name: "", description: "" })
    }

    return (
        <>
            <PageHeader
                breadcrumbs={[{ label: "Home" }]}
                title="知识库主页"
                subtitle="统一 AppShell、主题与请求封装的落地版本，后续页面将在此基础上扩展。"
                actions={
                    <div className="page-actions">
                        <Button variant="tonal" onClick={() => setShowDrawer(true)}>
                            查看页面骨架
                        </Button>
                        <Button onClick={() => setShowModal(true)}>新建 Collection</Button>
                    </div>
                }
            />

            <div className="grid two-column">
                <div className="stack">
                    <div className="card splash">
                        <div className="card__header">
                            <div>
                                <h3 className="card__title">设计系统与主题</h3>
                                <p className="caption">
                                    色板、字体、间距、按钮、搜索条、卡片、面包屑均已根据 Figma 导出样式重新命名与微调。
                                </p>
                            </div>
                            <span className="tag">8px grid</span>
                        </div>
                        <p className="page-subtitle">
                            AppShell 顶栏 + 标签栏 + 面包屑覆盖全部路由；全局 fetch 封装处理 envelope
                            <code style={{ marginLeft: 6, background: "var(--color-brand-weak)", padding: "2px 6px", borderRadius: "8px" }}>
                                {"{code:\"OK\"}"}
                            </code>{" "}
                            ，异常统一 toast。
                        </p>
                        <SearchBar
                            value={searchText}
                            onChange={setSearchText}
                            filterValue={searchFilter}
                            onFilterChange={setSearchFilter}
                            onSubmit={handlePlanSearch}
                            onReset={() => setSearchText("")}
                            placeholder="按 name / description 搜索 Collection（M5b 对接 API）"
                            filterOptions={[
                                { label: "按 name 搜索", value: "name" },
                                { label: "按 description 搜索", value: "description" },
                            ]}
                            loading={false}
                        />
                        <div className="divider"></div>
                        <div className="list">
                            <div className="list-item">
                                <div>
                                    <strong>全局样式 token</strong>
                                    <p className="caption">色板 / 字体 / 间距 / 圆角 / 阴影 / 滚动条</p>
                                </div>
                                <span className="pill success">已落地</span>
                            </div>
                            <div className="list-item">
                                <div>
                                    <strong>基础组件</strong>
                                    <p className="caption">按钮、搜索条、Modal、Drawer、Toast、卡片</p>
                                </div>
                                <span className="pill success">可复用</span>
                            </div>
                            <div className="list-item">
                                <div>
                                    <strong>路由骨架</strong>
                                    <p className="caption">6 个页面路径已预留，Chat 历史同标签栏联动</p>
                                </div>
                                <span className="pill success">已搭建</span>
                            </div>
                        </div>
                    </div>

                    <div className="card">
                        <div className="card__header">
                            <div>
                                <h3 className="card__title">页面骨架</h3>
                                <p className="caption">按照《前端页面组织逻辑设计》预置的路由与面包屑提示</p>
                            </div>
                            <Button variant="ghost" onClick={() => setShowDrawer(true)}>
                                查看
                            </Button>
                        </div>
                        <ul className="list">
                            {skeletonRoutes.map((route) => (
                                <li key={route.path} className="list-item">
                                    <div>
                                        <div className="inline-kv">
                                            <span className="status-dot" style={{ background: "var(--color-brand)" }}></span>
                                            <strong>{route.label}</strong>
                                        </div>
                                        <p className="caption">{route.path}</p>
                                    </div>
                                    <span className="pill muted">骨架就绪</span>
                                </li>
                            ))}
                        </ul>
                    </div>
                </div>

                <div className="stack">
                    <div className="card">
                        <div className="card__header">
                            <div>
                                <h3 className="card__title">健康检查</h3>
                                <p className="caption">调用 /healthz 验证后端可用性</p>
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
                                        quickStatusTone === "success"
                                            ? "var(--color-success)"
                                            : quickStatusTone === "danger"
                                            ? "var(--color-danger)"
                                            : quickStatusTone === "warn"
                                            ? "var(--color-warning)"
                                            : "var(--color-ink-soft)",
                                }}
                            ></span>
                            <strong>{healthStatus.state === "ok" ? "Backend OK" : "Backend"}</strong>
                            <span className="caption">{healthStatus.message || "等待检查"}</span>
                        </div>
                        <p className="caption">错误与 envelope 解析错误会在全局 toast 中弹出。</p>
                    </div>

                    <div className="card">
                        <div className="card__header">
                            <div>
                                <h3 className="card__title">快速文档台</h3>
                                <p className="caption">使用 collectionId 查询/上传文档，验证 MinerU 入库链路</p>
                            </div>
                            <span className="pill muted">同步调用</span>
                        </div>
                        <div className="stack">
                            <label className="caption" htmlFor="collectionIdInput">
                                Collection ID
                            </label>
                            <input
                                id="collectionIdInput"
                                className="input"
                                type="number"
                                value={collectionId}
                                onChange={(event) => setCollectionId(event.target.value)}
                                placeholder="输入 Collection ID"
                            />
                            <div className="search-bar__actions">
                                <Button variant="tonal" onClick={refreshDocuments} disabled={!collectionId || isLoadingDocs}>
                                    {isLoadingDocs ? "加载中..." : "加载文档"}
                                </Button>
                                <Button type="button" variant="ghost" onClick={() => setShowDrawer(true)}>
                                    查看路由
                                </Button>
                            </div>
                        </div>
                    </div>

                    <UploadForm onUpload={handleUpload} isUploading={isUploading} />
                    <DocumentList documents={documents} isLoading={isLoadingDocs} onRefresh={refreshDocuments} />
                </div>
            </div>

            <Modal
                open={showModal}
                title="新建 Collection"
                description="对接 API 将在 M5b 实装，当前仅展示组件与表单样式。"
                onClose={() => setShowModal(false)}
                footer={
                    <>
                        <Button type="button" variant="ghost" onClick={() => setShowModal(false)}>
                            取消
                        </Button>
                        <Button type="button" onClick={handleCreateCollection} disabled={!newCollectionForm.name}>
                            占位提交
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
                        value={newCollectionForm.name}
                        onChange={(event) => setNewCollectionForm((prev) => ({ ...prev, name: event.target.value }))}
                        placeholder="必填"
                    />
                    <label className="caption" htmlFor="newCollectionDesc">
                        Description
                    </label>
                    <textarea
                        id="newCollectionDesc"
                        className="input"
                        rows={3}
                        value={newCollectionForm.description}
                        onChange={(event) =>
                            setNewCollectionForm((prev) => ({ ...prev, description: event.target.value }))
                        }
                        placeholder="用于展示与搜索的摘要"
                    ></textarea>
                </div>
            </Modal>

            <Drawer open={showDrawer} onClose={() => setShowDrawer(false)} title="页面路由与面包屑">
                <p className="caption">AppShell 顶部标签栏在下列路由间保持高亮与面包屑一致性。</p>
                <div className="list">
                    {skeletonRoutes.map((route) => (
                        <div key={route.path} className="list-item">
                            <div>
                                <strong>{route.label}</strong>
                                <p className="caption">{route.path}</p>
                            </div>
                            <span className="pill muted">占位</span>
                        </div>
                    ))}
                </div>
            </Drawer>
        </>
    )
}
