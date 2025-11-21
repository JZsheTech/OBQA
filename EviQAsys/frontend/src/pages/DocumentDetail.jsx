import { useParams } from "react-router-dom"
import PageHeader from "../components/layout/PageHeader"
import Button from "../components/ui/Button"

export default function DocumentDetail() {
    const { documentId, collectionId } = useParams()

    return (
        <>
            <PageHeader
                breadcrumbs={[
                    { label: "Home", href: "/" },
                    { label: `Collection ${collectionId}`, href: `/collections/${collectionId}` },
                    { label: `Document ${documentId}` },
                ]}
                title={`Document ${documentId}`}
                subtitle="Document 元信息、Abstract 展示、聊天历史与 Document-RAG 的容器已搭建。"
                actions={<Button variant="tonal">打开原始 PDF（占位）</Button>}
            />

            <div className="grid two-column">
                <div className="stack">
                    <div className="card">
                        <div className="card__header">
                            <h3 className="card__title">元信息</h3>
                            <span className="pill muted">待拉取</span>
                        </div>
                        <p className="caption">num_pages / element_count / title / file_name 将在后续阶段展示。</p>
                        <div className="empty-state">M5d 将接入真实数据</div>
                    </div>
                    <div className="card">
                        <div className="card__header">
                            <h3 className="card__title">Abstract</h3>
                            <span className="pill muted">滚动展示</span>
                        </div>
                        <div className="empty-state">等待后端 abstract 字段</div>
                    </div>
                </div>

                <div className="stack">
                    <div className="card">
                        <div className="card__header">
                            <h3 className="card__title">Document 聊天历史</h3>
                            <span className="pill muted">骨架</span>
                        </div>
                        <div className="empty-state">列表将在 M5d 对接 /api/documents/{documentId}/chats</div>
                    </div>
                    <div className="card">
                        <div className="card__header">
                            <h3 className="card__title">Document-RAG 检索</h3>
                            <span className="pill muted">骨架</span>
                        </div>
                        <div className="empty-state">搜索输入与结果列表等待 RAG 接口</div>
                    </div>
                </div>
            </div>
        </>
    )
}
