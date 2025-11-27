import { useParams } from "react-router-dom"
import DebugIdFooter from "../components/DebugIdFooter"
import PageHeader from "../components/layout/PageHeader"
import Button from "../components/ui/Button"

export default function DocumentChat() {
    const { documentId, chatId } = useParams()

    return (
        <>
            <PageHeader
                breadcrumbs={[
                    { label: "Home", href: "/" },
                    { label: `Document ${documentId}` },
                    { label: `Chat ${chatId ?? "new"}` },
                ]}
                title={`Document Chat ${chatId ?? ""}`}
                subtitle="两栏布局：左侧问答，右侧固定 PDF 预览与证据高亮。"
                actions={<Button variant="tonal">发送问题（占位）</Button>}
            />

            <div className="grid two-column">
                <div className="card">
                    <div className="card__header">
                        <h3 className="card__title">聊天流</h3>
                        <span className="pill muted">M5f</span>
                    </div>
                    <div className="empty-state">等待聊天 API</div>
                </div>
                <div className="card">
                    <div className="card__header">
                        <h3 className="card__title">PDF 高亮</h3>
                        <span className="pill muted">固定 doc_id</span>
                    </div>
                    <div className="empty-state">展示 bbox 与页码的 viewer 占位</div>
                </div>
            </div>

            <DebugIdFooter
                segments={[
                    { label: "Document", value: documentId },
                    { label: "Chat", value: chatId ?? "new" },
                ]}
            />
        </>
    )
}
