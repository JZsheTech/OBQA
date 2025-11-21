import { useParams } from "react-router-dom"
import { useState } from "react"
import PageHeader from "../components/layout/PageHeader"
import Button from "../components/ui/Button"
import SearchBar from "../components/ui/SearchBar"

export default function CollectionDetail() {
    const { collectionId } = useParams()
    const [pendingSearch, setPendingSearch] = useState("")
    const [searchScope, setSearchScope] = useState("title")

    return (
        <>
            <PageHeader
                breadcrumbs={[
                    { label: "Home", href: "/" },
                    { label: `Collection ${collectionId}` },
                ]}
                title={`Collection ${collectionId}`}
                subtitle="双列布局：左侧文档列表/搜索，右侧聊天历史与 RAG，占位骨架已就绪。"
                actions={<Button variant="tonal">上传文档（M5c）</Button>}
            />

            <div className="grid two-column">
                <div className="stack">
                    <div className="card">
                        <div className="card__header">
                            <h3 className="card__title">文档列表</h3>
                            <span className="pill muted">M5c 对接</span>
                        </div>
                        <p className="caption">
                            这里将展示 collection 下的全部文档，支持 title/abstract/md_text 搜索与上传入口。
                        </p>
                        <SearchBar
                            compact
                            value={pendingSearch}
                            onChange={setPendingSearch}
                            filterValue={searchScope}
                            onFilterChange={setSearchScope}
                            onSubmit={() => {}}
                            placeholder="搜索文档（待对接接口）"
                            filterOptions={[
                                { label: "按 title", value: "title" },
                                { label: "按 abstract", value: "abstract" },
                                { label: "按 md_text", value: "md_text" },
                            ]}
                        />
                        <div className="empty-state">文档数据将在 M5c 时连接真实接口。</div>
                    </div>
                </div>

                <div className="stack">
                    <div className="card">
                        <div className="card__header">
                            <h3 className="card__title">Collection 聊天历史</h3>
                            <span className="pill muted">骨架</span>
                        </div>
                        <p className="caption">
                            预留聊天历史列表与跳转逻辑；当前为空态，后续对接 /api/collections/{collectionId}/chats。
                        </p>
                        <div className="empty-state">暂无聊天记录</div>
                    </div>
                    <div className="card">
                        <div className="card__header">
                            <h3 className="card__title">简单 Collection-RAG</h3>
                            <span className="pill muted">骨架</span>
                        </div>
                        <p className="caption">关键词检索 + 结果列表 + 详情弹窗将在 M5c 交付。</p>
                        <div className="empty-state">等待向量化与检索接口</div>
                    </div>
                </div>
            </div>
        </>
    )
}
