import PageHeader from "../components/layout/PageHeader"
import Button from "../components/ui/Button"

export default function ChatHistory() {
    return (
        <>
            <PageHeader
                breadcrumbs={[
                    { label: "Home", href: "/" },
                    { label: "Chat 历史" },
                ]}
                title="Chat 历史"
                subtitle="聚合 collection/document 聊天记录的过滤器与列表骨架。"
                actions={<Button variant="tonal">筛选（占位）</Button>}
            />

            <div className="grid two-column">
                <div className="card">
                    <div className="card__header">
                        <h3 className="card__title">Collection 聊天历史</h3>
                        <span className="pill muted">待接入</span>
                    </div>
                    <p className="caption">将按 created_at 排序，可跳转到 Collection Chat 三栏页面。</p>
                    <div className="empty-state">暂无数据</div>
                </div>
                <div className="card">
                    <div className="card__header">
                        <h3 className="card__title">Document 聊天历史</h3>
                        <span className="pill muted">待接入</span>
                    </div>
                    <p className="caption">展示 collection_name &gt; document_title &gt; chat_name。</p>
                    <div className="empty-state">暂无数据</div>
                </div>
            </div>
        </>
    )
}
