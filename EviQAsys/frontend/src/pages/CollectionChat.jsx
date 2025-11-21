import { useParams } from "react-router-dom"
import PageHeader from "../components/layout/PageHeader"
import Button from "../components/ui/Button"

export default function CollectionChat() {
    const { collectionId, chatId } = useParams()

    return (
        <>
            <PageHeader
                breadcrumbs={[
                    { label: "Home", href: "/" },
                    { label: `Collection ${collectionId}`, href: `/collections/${collectionId}` },
                    { label: `Chat ${chatId ?? "new"}` },
                ]}
                title={`Collection Chat ${chatId ?? ""}`}
                subtitle="三栏布局骨架：左侧聊天流，中间 PDF 预览，右侧聊天历史/证据信息栏。"
                actions={<Button variant="tonal">新建聊天（M5e）</Button>}
            />

            <div className="grid three-column">
                <div className="card">
                    <div className="card__header">
                        <h3 className="card__title">聊天记录</h3>
                        <span className="pill muted">待接入</span>
                    </div>
                    <div className="stack">
                        <div className="list-item">
                            <div>
                                <strong>用户提问</strong>
                                <p className="caption">“示例：本文的研究方法是什么？”</p>
                            </div>
                        </div>
                        <div className="list-item">
                            <div>
                                <strong>系统回答</strong>
                                <p className="caption">
                                    将在后续阶段渲染包含 <code>[Evidence#no]</code> 的气泡并支持复制。
                                </p>
                            </div>
                        </div>
                    </div>
                </div>

                <div className="card">
                    <div className="card__header">
                        <h3 className="card__title">PDF 预览</h3>
                        <span className="pill muted">M5e</span>
                    </div>
                    <p className="caption">
                        预留文档下拉、页码跳转与 bbox 高亮区域；后续接入 <code>/api/documents/{{doc_id}}/file</code>。
                    </p>
                    <div className="empty-state">PDF Viewer 占位</div>
                </div>

                <div className="card">
                    <div className="card__header">
                        <h3 className="card__title">聊天历史 & 证据</h3>
                        <span className="pill muted">骨架</span>
                    </div>
                    <p className="caption">侧边栏将在 M5e 展示聊天列表与 `[Elem#id] → [Evidence#no]` 映射。</p>
                    <div className="empty-state">等待后端锚点数据</div>
                </div>
            </div>
        </>
    )
}
