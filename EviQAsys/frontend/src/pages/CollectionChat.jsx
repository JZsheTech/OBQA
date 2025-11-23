import { useEffect, useMemo, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { Viewer, Worker } from "@react-pdf-viewer/core"
import { pageNavigationPlugin } from "@react-pdf-viewer/page-navigation"
import "@react-pdf-viewer/core/lib/styles/index.css"
import workerSrc from "pdfjs-dist/build/pdf.worker.min.js?url"

import {
    buildDocumentFileUrl,
    createCollectionChat,
    createTurn,
    getChatDetail,
    getTurnEvidences,
    listCollectionChats,
    listDocuments,
} from "../api/client"
import Breadcrumbs from "../components/ui/Breadcrumbs"
import Button from "../components/ui/Button"
import Drawer from "../components/ui/Drawer"
import Modal from "../components/ui/Modal"
import { useToast } from "../components/ui/Toast"

function formatDateTime(value) {
    if (!value) return "--"
    try {
        return new Date(value).toLocaleString()
    } catch (error) {
        console.warn("Failed to format date", error)
        return value
    }
}

function normalizeBBoxes(rawBBox) {
    if (!rawBBox) return []
    if (!Array.isArray(rawBBox)) return []
    const entries = Array.isArray(rawBBox[0]) ? rawBBox : [rawBBox]
    return entries
        .map((coords) => {
            if (!Array.isArray(coords)) return null
            const numeric = coords.map((value) => Number(value))
            if (numeric.length !== 4 || numeric.some((value) => !Number.isFinite(value))) return null
            const [x0, y0, x1, y1] = numeric
            return [Math.min(x0, x1), Math.min(y0, y1), Math.max(x0, x1), Math.max(y0, y1)]
        })
        .filter(Boolean)
}

function getPageOriginalSize(page, width, height, scale) {
    const view = page?.view
    const [, , rawWidth, rawHeight] = Array.isArray(view) ? view : []
    const originalWidth = Number(rawWidth)
    const originalHeight = Number(rawHeight)
    if (Number.isFinite(originalWidth) && Number.isFinite(originalHeight) && originalWidth > 0 && originalHeight > 0) {
        return { originalWidth, originalHeight }
    }
    const fallbackWidth = Number.isFinite(width) && Number.isFinite(scale) && scale !== 0 ? width / scale : null
    const fallbackHeight = Number.isFinite(height) && Number.isFinite(scale) && scale !== 0 ? height / scale : null
    if (
        Number.isFinite(fallbackWidth) &&
        Number.isFinite(fallbackHeight) &&
        fallbackWidth > 0 &&
        fallbackHeight > 0
    ) {
        return { originalWidth: fallbackWidth, originalHeight: fallbackHeight }
    }
    return { originalWidth: null, originalHeight: null }
}

function resolveBBoxToRect(bbox, originalWidth, originalHeight) {
    if (!bbox || bbox.length !== 4) return null
    let [x0, y0, x1, y1] = bbox
    const hasPageSize =
        Number.isFinite(originalWidth) && Number.isFinite(originalHeight) && originalWidth > 0 && originalHeight > 0
    if (!hasPageSize) return null

    const isNormalized = [x0, y0, x1, y1].every((value) => value >= 0 && value <= 1)

    if (isNormalized) {
        console.debug("Normalized bbox detected; converting to PDF points", {
            bbox,
            originalWidth,
            originalHeight,
        })
        x0 *= originalWidth
        x1 *= originalWidth
        y0 *= originalHeight
        y1 *= originalHeight
    }

    const left = Math.min(x0, x1)
    const top = Math.min(y0, y1)
    const width = Math.abs(x1 - x0)
    const height = Math.abs(y1 - y0)

    if (!Number.isFinite(width) || !Number.isFinite(height) || width === 0 || height === 0) return null

    return { x: left, y: top, width, height, isNormalized }
}

function HighlightedPage({ renderPageProps, highlights }) {
    const {
        annotationLayer,
        canvasLayer,
        textLayer,
        canvasLayerRendered,
        textLayerRendered,
        markRendered,
        pageIndex,
        scale,
        width,
        height,
        page,
    } = renderPageProps

    const { originalWidth, originalHeight } = getPageOriginalSize(page, width, height, scale)
    const activeHighlights = highlights?.[pageIndex] ?? []

    useEffect(() => {
        if (canvasLayerRendered && textLayerRendered) {
            markRendered(pageIndex)
        }
    }, [canvasLayerRendered, textLayerRendered, markRendered, pageIndex])

    const pageRects = useMemo(() => {
        if (!originalWidth || !originalHeight) return []
        return activeHighlights
            .map((bbox, index) => {
                const rect = resolveBBoxToRect(bbox, originalWidth, originalHeight)
                if (!rect) return null
                return { rect, key: `${pageIndex}-${index}` }
            })
            .filter(Boolean)
    }, [activeHighlights, originalHeight, originalWidth, pageIndex])

    return (
        <>
            {canvasLayer.children}
            {textLayer.children}
            {annotationLayer.children}
            {pageRects.length > 0 && originalWidth && originalHeight ? (
                <svg
                    className="pdf-highlight-layer"
                    aria-hidden="true"
                    viewBox={`0 0 ${originalWidth} ${originalHeight}`}
                    style={{
                        position: "absolute",
                        inset: 0,
                        width: "100%",
                        height: "100%",
                        pointerEvents: "none",
                        zIndex: 10,
                    }}
                >
                    {pageRects.map(({ rect, key }) => (
                        <rect
                            key={key}
                            x={rect.x}
                            y={rect.y}
                            width={rect.width}
                            height={rect.height}
                            className="evidence-highlight-rect"
                            vectorEffect="non-scaling-stroke"
                        />
                    ))}
                </svg>
            ) : null}
        </>
    )
}

function EvidenceText({ text, evidences, onSelectEvidence }) {
    const evidenceNoByElement = useMemo(() => {
        const mapping = new Map()
        ;(evidences ?? []).forEach((ev) => {
            if (ev.element_id != null && ev.evidence_no != null) {
                mapping.set(Number(ev.element_id), Number(ev.evidence_no))
            }
        })
        return mapping
    }, [evidences])

    if (!text) {
        return <p className="caption muted">暂无回答</p>
    }

    const nodes = []
    const bracketRegex = /\[([^\]]+)\]/g

    const resolveEvidenceNo = (tokenType, rawNo) => {
        const numeric = Number(rawNo)
        if (!Number.isFinite(numeric)) return null
        if (tokenType.toLowerCase() === "elem") {
            return evidenceNoByElement.get(numeric) ?? null
        }
        return numeric
    }

    const renderEvidenceButton = (evNo, key) => (
        <button
            key={key}
            type="button"
            className="evidence-tag"
            onClick={() => onSelectEvidence(evNo)}
        >
            Evidence #{evNo}
        </button>
    )

    const pushTextWithTokens = (chunk, keyPrefix) => {
        const tokenRegex = /(Evidence|Elem)#(\d+)/gi
        let cursor = 0
        let tokenMatch
        while ((tokenMatch = tokenRegex.exec(chunk)) !== null) {
            if (tokenMatch.index > cursor) {
                nodes.push(
                    <span key={`${keyPrefix}-text-${cursor}`}>
                        {chunk.slice(cursor, tokenMatch.index)}
                    </span>,
                )
            }
            const evNo = resolveEvidenceNo(tokenMatch[1], tokenMatch[2])
            if (evNo !== null) {
                nodes.push(renderEvidenceButton(evNo, `${keyPrefix}-ev-${tokenMatch.index}`))
            } else {
                nodes.push(<span key={`${keyPrefix}-raw-${tokenMatch.index}`}>{tokenMatch[0]}</span>)
            }
            cursor = tokenRegex.lastIndex
        }
        if (cursor < chunk.length) {
            nodes.push(<span key={`${keyPrefix}-tail-${cursor}`}>{chunk.slice(cursor)}</span>)
        }
    }

    const extractBracketEvidenceNos = (content) => {
        const tokenRegex = /(Evidence|Elem)#(\d+)/gi
        const ids = []
        let tokenMatch
        while ((tokenMatch = tokenRegex.exec(content)) !== null) {
            const evNo = resolveEvidenceNo(tokenMatch[1], tokenMatch[2])
            if (evNo !== null) {
                ids.push(evNo)
            }
        }
        return ids
    }

    let lastIndex = 0
    let match
    while ((match = bracketRegex.exec(text)) !== null) {
        if (match.index > lastIndex) {
            pushTextWithTokens(text.slice(lastIndex, match.index), `text-${lastIndex}`)
        }
        const evidenceNos = extractBracketEvidenceNos(match[1])
        if (evidenceNos.length === 0) {
            nodes.push(<span key={`raw-${match.index}`}>{match[0]}</span>)
        } else {
            evidenceNos.forEach((evNo, idx) => {
                nodes.push(renderEvidenceButton(evNo, `ev-${match.index}-${idx}`))
            })
        }
        lastIndex = match.index + match[0].length
    }
    if (lastIndex < text.length) {
        pushTextWithTokens(text.slice(lastIndex), `tail-${lastIndex}`)
    }
    return <p className="answer-text">{nodes}</p>
}

export default function CollectionChat() {
    const { collectionId, chatId } = useParams()
    const navigate = useNavigate()
    const { addToast } = useToast()

    const [chatDetail, setChatDetail] = useState(null)
    const [turns, setTurns] = useState([])
    const [chatList, setChatList] = useState([])
    const [documents, setDocuments] = useState([])
    const [selectedDocId, setSelectedDocId] = useState(null)
    const [selectedEvidence, setSelectedEvidence] = useState(null)
    const [pageForHighlight, setPageForHighlight] = useState(null)
    const [loadingChat, setLoadingChat] = useState(false)
    const [loadingDocs, setLoadingDocs] = useState(false)
    const [loadingChatList, setLoadingChatList] = useState(false)
    const [draftQuestion, setDraftQuestion] = useState("")
    const [sending, setSending] = useState(false)
    const [showCreateModal, setShowCreateModal] = useState(false)
    const [newChatTitle, setNewChatTitle] = useState("")
    const [showChatDrawer, setShowChatDrawer] = useState(false)
    const [showMetaPanel, setShowMetaPanel] = useState(false)

    const navigationPlugin = pageNavigationPlugin()
    const { jumpToPage } = navigationPlugin

    useEffect(() => {
        loadChatDetail()
        loadChatList()
        loadDocuments()
        setSelectedEvidence(null)
        setPageForHighlight(null)
        setDraftQuestion("")
    }, [chatId, collectionId])

    useEffect(() => {
        if (selectedDocId || documents.length === 0) return
        const evidenceDoc =
            selectedEvidence?.document_id ||
            turns.flatMap((turn) => turn.evidences ?? []).find((ev) => ev.document_id)?.document_id
        if (evidenceDoc) {
            setSelectedDocId(evidenceDoc)
        } else {
            setSelectedDocId(documents[0].id)
        }
    }, [documents, selectedDocId, selectedEvidence, turns])

    const evidenceDocId = useMemo(
        () => (selectedEvidence?.document_id != null ? Number(selectedEvidence.document_id) : null),
        [selectedEvidence?.document_id],
    )
    const evidencePageIndex = useMemo(
        () =>
            selectedEvidence?.page_index != null
                ? Math.max(0, Number(selectedEvidence.page_index) - 1)
                : null,
        [selectedEvidence?.page_index],
    )
    const evidenceBoxes = useMemo(
        () => normalizeBBoxes(selectedEvidence?.bbox),
        [selectedEvidence?.bbox],
    )

    const pageHighlights = useMemo(() => {
        if (evidenceDocId && selectedDocId && evidenceDocId !== Number(selectedDocId)) return {}
        if (!evidenceBoxes.length || evidencePageIndex == null) return {}
        return { [evidencePageIndex]: evidenceBoxes }
    }, [evidenceBoxes, evidenceDocId, evidencePageIndex, selectedDocId])

    const viewerKey = selectedDocId ? `doc-${selectedDocId}` : "no-doc"
    const selectedDocUrl = selectedDocId ? buildDocumentFileUrl(selectedDocId) : null

    async function loadChatDetail() {
        if (!chatId) return
        setLoadingChat(true)
        try {
            const data = await getChatDetail(chatId)
            setChatDetail(data)
            setTurns(Array.isArray(data.turns) ? data.turns : [])
        } catch (error) {
            setChatDetail(null)
            setTurns([])
            addToast({ type: "error", title: "加载聊天失败", message: error.message })
        } finally {
            setLoadingChat(false)
        }
    }

    async function loadChatList() {
        if (!collectionId) return
        setLoadingChatList(true)
        try {
            const data = await listCollectionChats(collectionId)
            setChatList(Array.isArray(data) ? data : [])
        } catch (error) {
            addToast({ type: "error", title: "加载聊天列表失败", message: error.message })
        } finally {
            setLoadingChatList(false)
        }
    }

    async function loadDocuments() {
        if (!collectionId) return
        setLoadingDocs(true)
        try {
            const data = await listDocuments(collectionId)
            setDocuments(Array.isArray(data) ? data : [])
        } catch (error) {
            addToast({ type: "error", title: "加载文档失败", message: error.message })
        } finally {
            setLoadingDocs(false)
        }
    }

    async function handleCreateChat() {
        if (!collectionId) return
        try {
            const result = await createCollectionChat(collectionId, { title: newChatTitle })
            setShowCreateModal(false)
            setNewChatTitle("")
            await loadChatList()
            const newChatId = result?.id ?? result?.data?.id
            if (newChatId) {
                navigate(`/collections/${collectionId}/chat/${newChatId}`)
            } else {
                addToast({ type: "info", title: "已创建聊天", message: "请手动选择新创建的会话" })
            }
        } catch (error) {
            addToast({ type: "error", title: "创建聊天失败", message: error.message })
        }
    }

    async function handleSendQuestion() {
        const question = draftQuestion.trim()
        if (!question) {
            addToast({ type: "info", title: "请输入问题", message: "问题内容不能为空" })
            return
        }
        if (!chatId) {
            addToast({ type: "error", title: "缺少 chatId", message: "请先创建或选择聊天" })
            return
        }
        setSending(true)
        try {
            await createTurn(chatId, { question })
            setDraftQuestion("")
            await loadChatDetail()
        } catch (error) {
            addToast({ type: "error", title: "发送失败", message: error.message })
        } finally {
            setSending(false)
        }
    }

    async function handleEvidenceSelect(evNo, turn) {
        if (!evNo || !turn) return
        let targetEvidence =
            turn.evidences?.find((item) => item.evidence_no === evNo) || turn.evidences?.[0]
        if (!targetEvidence) {
            try {
                const data = await getTurnEvidences(turn.id)
                targetEvidence =
                    data?.evidences?.find((item) => item.evidence_no === evNo) ||
                    data?.evidences?.[0]
            } catch (error) {
                addToast({ type: "error", title: "拉取证据失败", message: error.message })
                return
            }
        }
        if (!targetEvidence) {
            addToast({ type: "info", title: "未找到证据", message: "该标签缺少对应的 element" })
            return
        }
        setSelectedEvidence(targetEvidence)
        if (targetEvidence.document_id) {
            setSelectedDocId(Number(targetEvidence.document_id))
        }
        if (targetEvidence.page_index !== null && targetEvidence.page_index !== undefined) {
            const pageIndex = Math.max(0, Number(targetEvidence.page_index) - 1)
            setPageForHighlight(pageIndex)
            jumpToPage(pageIndex)
        } else {
            setPageForHighlight(null)
        }
    }

    const chatTitle = useMemo(() => {
        if (chatDetail?.title) return chatDetail.title
        if (chatId) return `Chat #${chatId}`
        return "Collection Chat"
    }, [chatDetail?.title, chatId])

    const selectedEvidenceMeta = selectedEvidence
        ? [
              { label: "Doc", value: selectedEvidence.document_id ?? "-" },
              { label: "Page", value: selectedEvidence.page_index ?? "-" },
              { label: "Type", value: selectedEvidence.elem_type ?? "-" },
          ]
        : []

    const breadcrumbs = [
        { label: "Home", href: "/" },
        { label: `Collection ${collectionId}`, href: `/collections/${collectionId}` },
        { label: chatTitle },
    ]

    return (
        <>
            <Breadcrumbs items={breadcrumbs} />

            <div className="meta-toggle">
                <span className="caption muted">页面头部信息已折叠以扩大聊天和 PDF 区域。</span>
                <Button variant="ghost" onClick={() => setShowMetaPanel((prev) => !prev)}>
                    {showMetaPanel ? "收起操作" : "展开操作"}
                </Button>
            </div>

            {showMetaPanel && (
                <div className="meta-panel">
                    <div className="meta-panel__header">
                        <div>
                            <h1 className="page-title">{chatTitle}</h1>
                            <p className="page-subtitle">
                                双栏布局：左侧聊天流，右侧 PDF 预览，可展开聊天列表查看历史会话。
                            </p>
                        </div>
                        <div className="meta-panel__actions">
                            <Button variant="ghost" onClick={() => setShowChatDrawer(true)}>
                                聊天列表
                            </Button>
                            <Button variant="ghost" onClick={loadChatDetail} disabled={loadingChat}>
                                {loadingChat ? "刷新中..." : "刷新聊天"}
                            </Button>
                            <Button variant="tonal" onClick={() => setShowCreateModal(true)}>
                                新建聊天
                            </Button>
                        </div>
                    </div>
                </div>
            )}

            <div className="grid two-column chat-layout">
                <div className="card chat-panel">
                    <div className="card__header">
                        <div>
                            <h3 className="card__title">聊天流</h3>
                            <p className="caption">展示用户问题、回答与 `[Evidence#no]` 标签。</p>
                        </div>
                        <span className="pill muted">{loadingChat ? "加载中..." : "M5e ready"}</span>
                    </div>

                    <div className="chat-messages">
                        {loadingChat ? (
                            <div className="empty-state">加载聊天记录...</div>
                        ) : turns.length === 0 ? (
                            <div className="empty-state">暂无历史，输入问题开始对话。</div>
                        ) : (
                            turns.map((turn) => (
                                <div key={turn.id} className="turn-block">
                                    <div className="message message-user">
                                        <div className="message__meta">
                                            <span className="pill muted">User</span>
                                            <span className="caption">
                                                #{turn.order ?? "-"} · {formatDateTime(turn.created_at)}
                                            </span>
                                        </div>
                                        <div className="message__bubble">{turn.user_question}</div>
                                    </div>
                                    <div className="message message-assistant">
                                        <div className="message__meta">
                                            <span className="pill">Assistant</span>
                                            <span className="caption">
                                                {turn.evidences?.length || 0} evidences
                                            </span>
                                        </div>
                                        <div className="message__bubble">
                                            <EvidenceText
                                                text={turn.answer_with_evidence || turn.answer_text}
                                                evidences={turn.evidences}
                                                onSelectEvidence={(evNo) => handleEvidenceSelect(evNo, turn)}
                                            />
                                            <div className="evidence-chip-row">
                                                {(turn.evidences ?? []).map((ev) => (
                                                    <button
                                                        key={`${turn.id}-${ev.element_id}`}
                                                        type="button"
                                                        className="evidence-chip"
                                                        onClick={() =>
                                                            handleEvidenceSelect(ev.evidence_no, turn)
                                                        }
                                                    >
                                                        <span className="pill muted">
                                                            Evidence #{ev.evidence_no ?? "-"}
                                                        </span>
                                                        <span className="caption">
                                                            Doc {ev.document_id ?? "-"} · Page{" "}
                                                            {ev.page_index ?? "-"}
                                                        </span>
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>

                    <div className="chat-input">
                        <textarea
                            className="input"
                            rows={4}
                            value={draftQuestion}
                            onChange={(event) => setDraftQuestion(event.target.value)}
                            placeholder="提出你的问题，回答会包含可点击的 Evidence 标签..."
                        ></textarea>
                        <div className="chat-input__actions">
                            <span className="caption">
                                提示：点击回答中的 Evidence 标签可跳转到 PDF 并高亮 bbox。
                            </span>
                            <Button onClick={handleSendQuestion} disabled={sending}>
                                {sending ? "发送中..." : "发送"}
                            </Button>
                        </div>
                    </div>
                </div>

                <div className="stack pdf-column">
                    <div className="card pdf-panel">
                        <div className="card__header pdf-header">
                            <div>
                                <h3 className="card__title">PDF Viewer</h3>
                                <p className="caption">
                                    文档下拉 + bbox 高亮；点击 Evidence 自动跳转对应页。
                                </p>
                            </div>
                            <div className="pdf-header__actions">
                                <Button variant="ghost" onClick={() => setShowChatDrawer(true)}>
                                    聊天列表
                                </Button>
                                {selectedDocId && (
                                    <Button
                                        variant="ghost"
                                        onClick={() => window.open(buildDocumentFileUrl(selectedDocId), "_blank")}
                                    >
                                        打开原始 PDF
                                    </Button>
                                )}
                            </div>
                        </div>

                        <div className="pdf-toolbar">
                            <label className="caption" htmlFor="doc-select">
                                当前文档
                            </label>
                            <div className="pdf-toolbar__row">
                                <select
                                    id="doc-select"
                                    className="search-bar__select"
                                    value={selectedDocId ?? ""}
                                    onChange={(event) => {
                                        setSelectedDocId(event.target.value ? Number(event.target.value) : null)
                                        setPageForHighlight(null)
                                    }}
                                    disabled={loadingDocs || documents.length === 0}
                                >
                                    {documents.map((doc) => (
                                        <option key={doc.id} value={doc.id}>
                                            {doc.title || doc.file_name || `Doc #${doc.id}`}
                                        </option>
                                    ))}
                                </select>
                                <span className="caption muted">
                                    {loadingDocs ? "文档加载中..." : `${documents.length} 个可选文档`}
                                </span>
                            </div>
                        </div>

                        {!selectedDocId ? (
                            <div className="empty-state">请选择文档以加载 PDF。</div>
                        ) : (
                            <div className="pdf-viewer">
                                <Worker workerUrl={workerSrc}>
                                    <Viewer
                                        key={viewerKey}
                                        fileUrl={selectedDocUrl}
                                        renderPage={(props) => (
                                            <HighlightedPage renderPageProps={props} highlights={pageHighlights} />
                                        )}
                                        initialPage={pageForHighlight ?? 0}
                                        plugins={[navigationPlugin]}
                                    />
                                </Worker>
                            </div>
                        )}
                    </div>

                    <div className="card">
                        <div className="card__header">
                            <div>
                                <h4 className="card__title">选中证据信息</h4>
                                <p className="caption">点击回答中的 Evidence 标签后显示。</p>
                            </div>
                        </div>
                        {selectedEvidence ? (
                            <div className="stack">
                                <div className="inline-kv">
                                    <strong>Evidence #{selectedEvidence.evidence_no ?? "-"}</strong>
                                    <span className="caption">Elem #{selectedEvidence.element_id}</span>
                                </div>
                                <div className="info-grid">
                                    {selectedEvidenceMeta.map((item) => (
                                        <div key={item.label} className="info-item">
                                            <div className="caption">{item.label}</div>
                                            <strong>{item.value}</strong>
                                        </div>
                                    ))}
                                </div>
                                {selectedEvidence.snippet || selectedEvidence.text_content ? (
                                    <div className="stack">
                                        {selectedEvidence.snippet && (
                                            <div className="stack">
                                                <div className="caption muted">Snippet</div>
                                                <div className="code-block">{selectedEvidence.snippet}</div>
                                            </div>
                                        )}
                                        {selectedEvidence.text_content && (
                                            <div className="stack">
                                                <div className="caption muted">Text Content</div>
                                                <div className="code-block">{selectedEvidence.text_content}</div>
                                            </div>
                                        )}
                                    </div>
                                ) : (
                                    <div className="code-block">无 snippet</div>
                                )}
                                {!selectedEvidence.bbox && (
                                    <p className="caption muted">该证据缺少 bbox，高亮不可用。</p>
                                )}
                            </div>
                        ) : (
                            <div className="empty-state">点击 Evidence 标签后在此查看元信息。</div>
                        )}
                    </div>
                </div>
            </div>

            <Modal
                open={showCreateModal}
                title="新建 Collection Chat"
                description="为当前 Collection 创建一个新的聊天会话。"
                onClose={() => setShowCreateModal(false)}
                footer={
                    <>
                        <Button variant="ghost" onClick={() => setShowCreateModal(false)}>
                            取消
                        </Button>
                        <Button onClick={handleCreateChat}>创建</Button>
                    </>
                }
            >
                <div className="stack">
                    <label className="caption" htmlFor="chat-title">
                        聊天标题（可选）
                    </label>
                    <input
                        id="chat-title"
                        className="input"
                        value={newChatTitle}
                        onChange={(event) => setNewChatTitle(event.target.value)}
                        placeholder="如：Dataset 综述问答"
                    />
                </div>
            </Modal>

            <Drawer
                open={showChatDrawer}
                title="聊天列表"
                onClose={() => setShowChatDrawer(false)}
                footer={
                    <Button variant="tonal" onClick={() => setShowCreateModal(true)}>
                        新建聊天
                    </Button>
                }
            >
                <div className="inline-kv">
                    <span className="caption">来自 /api/collections/{collectionId}/chats</span>
                    <Button variant="ghost" onClick={loadChatList} disabled={loadingChatList}>
                        {loadingChatList ? "刷新中..." : "刷新"}
                    </Button>
                </div>
                {loadingChatList ? (
                    <div className="empty-state">加载中...</div>
                ) : chatList.length === 0 ? (
                    <div className="empty-state">暂无聊天，创建一个新会话开始提问。</div>
                ) : (
                    <div className="list scrollable-list">
                        {chatList.map((chat) => {
                            const isActive = String(chat.id) === String(chatId)
                            return (
                                <button
                                    key={chat.id}
                                    type="button"
                                    className={`list-item${isActive ? " active" : ""}`}
                                    onClick={() => {
                                        navigate(`/collections/${collectionId}/chat/${chat.id}`)
                                        setShowChatDrawer(false)
                                    }}
                                >
                                    <div>
                                        <strong>{chat.title || `Chat #${chat.id}`}</strong>
                                        <p className="caption">order {chat.max_turn_order ?? 0}</p>
                                    </div>
                                    <span className="pill muted">{chat.type}</span>
                                </button>
                            )
                        })}
                    </div>
                )}
            </Drawer>
        </>
    )
}
