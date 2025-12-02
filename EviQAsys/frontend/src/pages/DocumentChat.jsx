import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useNavigate, useParams } from "react-router-dom"
import { SpecialZoomLevel, Viewer, Worker } from "@react-pdf-viewer/core"
import { pageNavigationPlugin } from "@react-pdf-viewer/page-navigation"
import { zoomPlugin } from "@react-pdf-viewer/zoom"
import "@react-pdf-viewer/core/lib/styles/index.css"
import "@react-pdf-viewer/zoom/lib/styles/index.css"
import workerSrc from "pdfjs-dist/build/pdf.worker.min.js?url"

import {
    buildDocumentFileUrl,
    createDocumentChat,
    createTurn,
    getChatDetail,
    getDocumentDetail,
    getTurnEvidences,
    listDocumentChats,
    updateChat,
} from "../api/client"
import { HIGHLIGHT_BBOX_BASE, HIGHLIGHT_BBOX_OFFSET_X, HIGHLIGHT_BBOX_OFFSET_Y } from "../config/highlight"
import DebugIdFooter from "../components/DebugIdFooter"
import Breadcrumbs from "../components/ui/Breadcrumbs"
import Button from "../components/ui/Button"
import Drawer from "../components/ui/Drawer"
import Modal from "../components/ui/Modal"
import { useToast } from "../components/ui/Toast"

const DEFAULT_USE_IMAGE = false
const DEFAULT_TEXT_RETRIEVE_TOPK = "8"
const DEFAULT_IMAGE_RETRIEVE_TOPK = "2"
const DEFAULT_TEXT_MEMORY_TOPK = "4"
const DEFAULT_IMAGE_MEMORY_TOPK = "1"
const DEFAULT_USE_PAGE_IN_TEXT_RETRIEVE = false
const DEFAULT_PAGE_RETRIEVE_TOPK = "4"
const DEFAULT_TEXT_SEARCH_MODE = "hybrid"
const DEFAULT_CHAT_PANEL_RATIO = 0.55
const MIN_PANEL_RATIO = 0.32
const MAX_PANEL_RATIO = 0.68

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
            const [x1, y1, x2, y2] = numeric
            const left = Math.min(x1, x2)
            const top = Math.min(y1, y2)
            const right = Math.max(x1, x2)
            const bottom = Math.max(y1, y2)
            if (right <= left || bottom <= top) return null
            return [left, top, right, bottom]
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
    if (!Array.isArray(bbox) || bbox.length !== 4) return null
    const numeric = bbox.map((value) => Number(value))
    if (numeric.some((value) => !Number.isFinite(value))) return null
    const [rawX1, rawY1, rawX2, rawY2] = numeric
    const hasPageSize =
        Number.isFinite(originalWidth) && Number.isFinite(originalHeight) && originalWidth > 0 && originalHeight > 0
    if (!hasPageSize) return null

    const left = Math.min(rawX1, rawX2)
    const top = Math.min(rawY1, rawY2)
    const right = Math.max(rawX1, rawX2)
    const bottom = Math.max(rawY1, rawY2)

    if (right <= left || bottom <= top) return null

    const ordered = [left, top, right, bottom]
    const inUnitRange = ordered.every((value) => value >= 0 && value <= 1)
    const inThousandRange = !inUnitRange && ordered.every((value) => value >= 0 && value <= HIGHLIGHT_BBOX_BASE)

    const adjustedRight = inThousandRange ? right + HIGHLIGHT_BBOX_OFFSET_X : right
    const adjustedBottom = inThousandRange ? bottom + HIGHLIGHT_BBOX_OFFSET_Y : bottom

    const scaleX = inUnitRange ? originalWidth : inThousandRange ? originalWidth / HIGHLIGHT_BBOX_BASE : 1
    const scaleY = inUnitRange ? originalHeight : inThousandRange ? originalHeight / HIGHLIGHT_BBOX_BASE : 1

    const x = left * scaleX
    const y = top * scaleY
    const width = (adjustedRight - left) * scaleX
    const height = (adjustedBottom - top) * scaleY

    if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) return null

    return { x, y, width, height, isNormalized: inUnitRange || inThousandRange }
}

function HighlightedPage({ renderPageProps, highlights, onHighlightClick }) {
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
                    viewBox={`0 0 ${originalWidth} ${originalHeight}`}
                    style={{
                        position: "absolute",
                        inset: 0,
                        width: "100%",
                        height: "100%",
                        pointerEvents: "auto",
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
                            role="button"
                            tabIndex={0}
                            aria-label={`Evidence highlight on page ${pageIndex + 1}`}
                            onClick={(event) => {
                                event.stopPropagation()
                                if (onHighlightClick) {
                                    onHighlightClick({ pageIndex, rect })
                                }
                            }}
                            onKeyDown={(event) => {
                                if (event.key === "Enter" || event.key === " ") {
                                    event.preventDefault()
                                    if (onHighlightClick) {
                                        onHighlightClick({ pageIndex, rect })
                                    }
                                }
                            }}
                            style={{ pointerEvents: "auto" }}
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

export default function DocumentChat() {
    const { documentId, chatId: chatIdParam } = useParams()
    const chatId = chatIdParam && chatIdParam !== "new" ? chatIdParam : null
    const navigate = useNavigate()
    const { addToast } = useToast()

    const [chatDetail, setChatDetail] = useState(null)
    const [documentDetail, setDocumentDetail] = useState(null)
    const [turns, setTurns] = useState([])
    const [chatList, setChatList] = useState([])
    const [selectedEvidence, setSelectedEvidence] = useState(null)
    const [pageForHighlight, setPageForHighlight] = useState(null)
    const [showEvidencePopover, setShowEvidencePopover] = useState(false)
    const [loadingChat, setLoadingChat] = useState(false)
    const [loadingChatList, setLoadingChatList] = useState(false)
    const [loadingDocument, setLoadingDocument] = useState(false)
    const [draftQuestion, setDraftQuestion] = useState("")
    const [sending, setSending] = useState(false)
    const [showChatDrawer, setShowChatDrawer] = useState(false)
    const [useImage, setUseImage] = useState(DEFAULT_USE_IMAGE)
    const [textRetrieveTopk, setTextRetrieveTopk] = useState(DEFAULT_TEXT_RETRIEVE_TOPK)
    const [imageRetrieveTopk, setImageRetrieveTopk] = useState(DEFAULT_IMAGE_RETRIEVE_TOPK)
    const [textMemoryTopk, setTextMemoryTopk] = useState(DEFAULT_TEXT_MEMORY_TOPK)
    const [imageMemoryTopk, setImageMemoryTopk] = useState(DEFAULT_IMAGE_MEMORY_TOPK)
    const [usePageInTextRetrieve, setUsePageInTextRetrieve] = useState(DEFAULT_USE_PAGE_IN_TEXT_RETRIEVE)
    const [pageRetrieveTopk, setPageRetrieveTopk] = useState(DEFAULT_PAGE_RETRIEVE_TOPK)
    const [textSearchMode, setTextSearchMode] = useState(DEFAULT_TEXT_SEARCH_MODE)
    const [chatPanelRatio, setChatPanelRatio] = useState(DEFAULT_CHAT_PANEL_RATIO)
    const [isResizing, setIsResizing] = useState(false)
    const [savingChatTitle, setSavingChatTitle] = useState(false)
    const [showRenameModal, setShowRenameModal] = useState(false)
    const [renameTitle, setRenameTitle] = useState("")
    const [creatingChat, setCreatingChat] = useState(false)

    const layoutRef = useRef(null)

    const navigationPlugin = pageNavigationPlugin()
    const { jumpToPage } = navigationPlugin
    const zoomPluginInstance = zoomPlugin()
    const { ZoomIn, ZoomOut, ZoomPopover } = zoomPluginInstance

    const updatePanelRatio = useCallback(
        (clientX) => {
            if (!layoutRef.current || !Number.isFinite(clientX)) return
            const rect = layoutRef.current.getBoundingClientRect()
            if (!rect.width) return
            const rawRatio = (clientX - rect.left) / rect.width
            const nextRatio = Math.min(MAX_PANEL_RATIO, Math.max(MIN_PANEL_RATIO, rawRatio))
            setChatPanelRatio(nextRatio)
        },
        [layoutRef],
    )

    const handleResizeStart = useCallback(
        (clientX) => {
            if (!layoutRef.current) return
            updatePanelRatio(clientX)
            setIsResizing(true)
        },
        [updatePanelRatio],
    )

    const handleResizeKeyDown = (event) => {
        if (event.key !== "ArrowLeft" && event.key !== "ArrowRight") return
        event.preventDefault()
        const delta = event.key === "ArrowLeft" ? -0.02 : 0.02
        setChatPanelRatio((prev) => Math.min(MAX_PANEL_RATIO, Math.max(MIN_PANEL_RATIO, prev + delta)))
    }

    const resetPanelRatio = useCallback(() => {
        setChatPanelRatio(DEFAULT_CHAT_PANEL_RATIO)
    }, [])

    useEffect(() => {
        if (!isResizing) return
        const handleMouseMove = (event) => updatePanelRatio(event.clientX)
        const handleTouchMove = (event) => {
            const touch = event.touches?.[0]
            if (touch) updatePanelRatio(touch.clientX)
        }
        const stopResize = () => setIsResizing(false)
        const bodyStyle = typeof document !== "undefined" ? document.body?.style : null
        const originalUserSelect = bodyStyle?.userSelect
        if (bodyStyle) {
            bodyStyle.userSelect = "none"
        }
        window.addEventListener("mousemove", handleMouseMove)
        window.addEventListener("touchmove", handleTouchMove)
        window.addEventListener("mouseup", stopResize)
        window.addEventListener("touchend", stopResize)
        window.addEventListener("touchcancel", stopResize)
        window.addEventListener("mouseleave", stopResize)
        return () => {
            if (bodyStyle) {
                bodyStyle.userSelect = originalUserSelect
            }
            window.removeEventListener("mousemove", handleMouseMove)
            window.removeEventListener("touchmove", handleTouchMove)
            window.removeEventListener("mouseup", stopResize)
            window.removeEventListener("touchend", stopResize)
            window.removeEventListener("touchcancel", stopResize)
            window.removeEventListener("mouseleave", stopResize)
        }
    }, [isResizing, updatePanelRatio])

    useEffect(() => {
        loadDocumentDetail()
    }, [documentId])

    useEffect(() => {
        if (chatId) {
            loadChatDetail(chatId)
        } else {
            setChatDetail(null)
            setTurns([])
        }
        loadChatList()
        setSelectedEvidence(null)
        setPageForHighlight(null)
        setDraftQuestion("")
        setShowEvidencePopover(false)
    }, [chatId, documentId])

    useEffect(() => {
        setRenameTitle(chatDetail?.title ?? "")
    }, [chatDetail?.title])

    useEffect(() => {
        setShowEvidencePopover(false)
    }, [selectedEvidence])

    useEffect(() => {
        const defaults = chatDetail?.qa_config_defaults
        if (!defaults) {
            setUseImage(DEFAULT_USE_IMAGE)
            setTextRetrieveTopk(DEFAULT_TEXT_RETRIEVE_TOPK)
            setImageRetrieveTopk(DEFAULT_IMAGE_RETRIEVE_TOPK)
            setTextMemoryTopk(DEFAULT_TEXT_MEMORY_TOPK)
            setImageMemoryTopk(DEFAULT_IMAGE_MEMORY_TOPK)
            setUsePageInTextRetrieve(DEFAULT_USE_PAGE_IN_TEXT_RETRIEVE)
            setPageRetrieveTopk(DEFAULT_PAGE_RETRIEVE_TOPK)
            setTextSearchMode(DEFAULT_TEXT_SEARCH_MODE)
            return
        }
        setUseImage(Boolean(defaults.use_image))
        setTextRetrieveTopk(String(defaults.text_retrieve_topk ?? DEFAULT_TEXT_RETRIEVE_TOPK))
        setImageRetrieveTopk(String(defaults.image_retrieve_topk ?? DEFAULT_IMAGE_RETRIEVE_TOPK))
        setTextMemoryTopk(String(defaults.text_memory_topk ?? DEFAULT_TEXT_MEMORY_TOPK))
        setImageMemoryTopk(String(defaults.image_memory_topk ?? DEFAULT_IMAGE_MEMORY_TOPK))
        setUsePageInTextRetrieve(Boolean(defaults.use_page_in_text_retrieve))
        setPageRetrieveTopk(String(defaults.page_retrieve_topk ?? DEFAULT_PAGE_RETRIEVE_TOPK))
        setTextSearchMode(defaults.text_search_mode || DEFAULT_TEXT_SEARCH_MODE)
    }, [chatDetail?.qa_config_defaults])

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
        if (!selectedEvidence) return {}
        if (selectedEvidence.document_id && documentId && Number(selectedEvidence.document_id) !== Number(documentId)) {
            return {}
        }
        if (!evidenceBoxes.length || evidencePageIndex == null) return {}
        return { [evidencePageIndex]: evidenceBoxes }
    }, [documentId, evidenceBoxes, evidencePageIndex, selectedEvidence])

    function resetQaControls() {
        const defaults = chatDetail?.qa_config_defaults
        if (defaults) {
            setUseImage(Boolean(defaults.use_image))
            setTextRetrieveTopk(String(defaults.text_retrieve_topk ?? DEFAULT_TEXT_RETRIEVE_TOPK))
            setImageRetrieveTopk(String(defaults.image_retrieve_topk ?? DEFAULT_IMAGE_RETRIEVE_TOPK))
            setTextMemoryTopk(String(defaults.text_memory_topk ?? DEFAULT_TEXT_MEMORY_TOPK))
            setImageMemoryTopk(String(defaults.image_memory_topk ?? DEFAULT_IMAGE_MEMORY_TOPK))
            setUsePageInTextRetrieve(Boolean(defaults.use_page_in_text_retrieve))
            setPageRetrieveTopk(String(defaults.page_retrieve_topk ?? DEFAULT_PAGE_RETRIEVE_TOPK))
            setTextSearchMode(defaults.text_search_mode || DEFAULT_TEXT_SEARCH_MODE)
            return
        }
        setUseImage(DEFAULT_USE_IMAGE)
        setTextRetrieveTopk(DEFAULT_TEXT_RETRIEVE_TOPK)
        setImageRetrieveTopk(DEFAULT_IMAGE_RETRIEVE_TOPK)
        setTextMemoryTopk(DEFAULT_TEXT_MEMORY_TOPK)
        setImageMemoryTopk(DEFAULT_IMAGE_MEMORY_TOPK)
        setUsePageInTextRetrieve(DEFAULT_USE_PAGE_IN_TEXT_RETRIEVE)
        setPageRetrieveTopk(DEFAULT_PAGE_RETRIEVE_TOPK)
        setTextSearchMode(DEFAULT_TEXT_SEARCH_MODE)
    }

    const layoutStyle = useMemo(() => {
        const leftRatio = Math.min(MAX_PANEL_RATIO, Math.max(MIN_PANEL_RATIO, chatPanelRatio))
        const rightRatio = Math.max(0.1, 1 - leftRatio)
        return {
            "--chat-panel-width": `${leftRatio}fr`,
            "--pdf-panel-width": `${rightRatio}fr`,
        }
    }, [chatPanelRatio])

    const viewerKey = documentId ? `doc-${documentId}` : "no-doc"
    const documentFileUrl = documentId ? buildDocumentFileUrl(documentId) : null

    async function loadDocumentDetail() {
        if (!documentId) return
        setLoadingDocument(true)
        try {
            const data = await getDocumentDetail(documentId)
            setDocumentDetail(data)
        } catch (error) {
            addToast({ type: "error", title: "加载 Document 失败", message: error.message })
        } finally {
            setLoadingDocument(false)
        }
    }

    async function loadChatDetail(targetId = chatId) {
        if (!targetId) return
        setLoadingChat(true)
        try {
            const data = await getChatDetail(targetId)
            setChatDetail(data)
            setTurns(Array.isArray(data.turns) ? data.turns : [])
            const targetDocId = data?.document_id
            const typeLower = (data?.type || "document").toLowerCase()
            if (targetDocId && documentId && Number(targetDocId) !== Number(documentId)) {
                addToast({
                    type: "warning",
                    title: "chat 文档不匹配",
                    message: `聊天绑定 doc ${targetDocId}，当前路由 doc ${documentId}`,
                })
            }
            if (typeLower !== "document") {
                addToast({ type: "warning", title: "非 document 类型聊天", message: "请确认聊天类型" })
            }
        } catch (error) {
            setChatDetail(null)
            setTurns([])
            addToast({ type: "error", title: "加载聊天失败", message: error.message })
        } finally {
            setLoadingChat(false)
        }
    }

    async function loadChatList() {
        if (!documentId) return
        setLoadingChatList(true)
        try {
            const data = await listDocumentChats(documentId)
            setChatList(Array.isArray(data) ? data : [])
        } catch (error) {
            addToast({ type: "error", title: "加载聊天列表失败", message: error.message })
        } finally {
            setLoadingChatList(false)
        }
    }

    async function handleCreateChat() {
        if (!documentId) return
        const collectionId = documentDetail?.collection_id
        if (!collectionId) {
            addToast({ type: "error", title: "缺少 collection_id", message: "无法创建文档级聊天" })
            return
        }
        if (creatingChat) return
        setCreatingChat(true)
        try {
            const result = await createDocumentChat({
                documentId,
                collectionId,
                title: documentDetail?.title || documentDetail?.file_name || null,
            })
            await loadChatList()
            const newChatId = result?.id ?? result?.data?.id
            if (newChatId) {
                navigate(`/documents/${documentId}/chat/${newChatId}`)
            } else {
                addToast({ type: "info", title: "聊天已创建", message: "请在列表中选择新会话" })
            }
        } catch (error) {
            addToast({ type: "error", title: "创建聊天失败", message: error.message })
        } finally {
            setCreatingChat(false)
        }
    }

    async function persistChatTitle(nextTitle) {
        if (!chatId) {
            addToast({ type: "error", title: "缺少 chatId", message: "无法保存聊天标题" })
            return
        }
        setSavingChatTitle(true)
        try {
            await updateChat(chatId, { title: nextTitle })
            await Promise.all([loadChatDetail(chatId), loadChatList()])
            addToast({
                type: "success",
                title: "聊天标题已更新",
                message: nextTitle ? nextTitle : `已重置为 Chat #${chatId}`,
            })
        } catch (error) {
            addToast({ type: "error", title: "保存聊天标题失败", message: error.message })
        } finally {
            setSavingChatTitle(false)
        }
    }

    async function handleRenameSave() {
        if (savingChatTitle) return
        const trimmed = renameTitle.trim()
        await persistChatTitle(trimmed || null)
        setShowRenameModal(false)
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
        if (scopeMismatch) {
            addToast({ type: "error", title: "聊天未绑定当前文档", message: "请切换或新建针对该文档的聊天" })
            return
        }
        const normalizeTopk = (value) => {
            if (value === "" || value === undefined || value === null) return undefined
            const numeric = Number(value)
            if (Number.isNaN(numeric)) return undefined
            return Math.min(20, Math.max(1, Math.floor(numeric)))
        }
        const normalizedTextTopk = normalizeTopk(textRetrieveTopk)
        const normalizedImageTopk = normalizeTopk(imageRetrieveTopk)
        const normalizedTextMemTopk = normalizeTopk(textMemoryTopk)
        const normalizedImageMemTopk = normalizeTopk(imageMemoryTopk)
        const normalizedPageTopK = normalizeTopk(pageRetrieveTopk)
        if (normalizedTextTopk !== undefined) setTextRetrieveTopk(String(normalizedTextTopk))
        if (normalizedImageTopk !== undefined) setImageRetrieveTopk(String(normalizedImageTopk))
        if (normalizedTextMemTopk !== undefined) setTextMemoryTopk(String(normalizedTextMemTopk))
        if (normalizedImageMemTopk !== undefined) setImageMemoryTopk(String(normalizedImageMemTopk))
        if (normalizedPageTopK !== undefined) setPageRetrieveTopk(String(normalizedPageTopK))
        setSending(true)
        try {
            await createTurn(chatId, {
                question,
                useImage,
                textRetrieveTopk: normalizedTextTopk,
                imageRetrieveTopk: normalizedImageTopk,
                textMemoryTopk: normalizedTextMemTopk,
                imageMemoryTopk: normalizedImageMemTopk,
                usePageInTextRetrieve,
                pageRetrieveTopk: normalizedPageTopK,
                textSearchMode,
            })
            setDraftQuestion("")
            await loadChatDetail(chatId)
        } catch (error) {
            addToast({ type: "error", title: "发送失败", message: error.message })
        } finally {
            setSending(false)
        }
    }

    async function handleEvidenceSelect(evNo, turn) {
        if (!evNo || !turn) return
        let targetEvidence = turn.evidences?.find((item) => item.evidence_no === evNo) || turn.evidences?.[0]
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
        if (targetEvidence.document_id && documentId && Number(targetEvidence.document_id) !== Number(documentId)) {
            addToast({ type: "warning", title: "证据不属于当前文档", message: "仅高亮当前 doc 的证据" })
        }
        setSelectedEvidence(targetEvidence)
        if (targetEvidence.page_index !== null && targetEvidence.page_index !== undefined) {
            const pageIndex = Math.max(0, Number(targetEvidence.page_index) - 1)
            setPageForHighlight(pageIndex)
            jumpToPage(pageIndex)
        } else {
            setPageForHighlight(null)
        }
        setShowEvidencePopover(false)
    }

    const chatTitle = useMemo(() => {
        if (chatDetail?.title) return chatDetail.title
        if (chatId) return `Chat #${chatId}`
        return "Document Chat"
    }, [chatDetail?.title, chatId])

    const docName = useMemo(() => {
        if (documentDetail?.title) return documentDetail.title
        if (documentDetail?.file_name) return documentDetail.file_name
        if (documentId) return `Document ${documentId}`
        return "Document"
    }, [documentDetail?.file_name, documentDetail?.title, documentId])

    const collectionLabel = useMemo(() => {
        if (documentDetail?.collection_name) return documentDetail.collection_name
        if (documentDetail?.collection_id) return `Collection ${documentDetail.collection_id}`
        return "Collection"
    }, [documentDetail?.collection_id, documentDetail?.collection_name])

    const breadcrumbs = useMemo(() => {
        const collectionId = documentDetail?.collection_id
        const items = [
            { label: "Home", href: "/" },
            { label: collectionLabel, href: collectionId ? `/collections/${collectionId}` : undefined },
            {
                label: docName,
                href: collectionId && documentId ? `/collections/${collectionId}/documents/${documentId}` : undefined,
            },
            { label: chatTitle },
        ]
        return items
    }, [collectionLabel, docName, chatTitle, documentDetail?.collection_id, documentId])

    const chatType = useMemo(() => (chatDetail?.type || "document").toLowerCase(), [chatDetail?.type])
    const docMismatch = useMemo(() => {
        if (!chatId || chatType !== "document") return false
        if (chatDetail?.document_id == null || documentId == null) return false
        return Number(chatDetail.document_id) !== Number(documentId)
    }, [chatDetail?.document_id, chatId, chatType, documentId])
    const scopeMismatch = docMismatch || (chatId ? chatType !== "document" : false)

    const selectedEvidenceMeta = selectedEvidence
        ? [
              { label: "Doc", value: selectedEvidence.document_id ?? "-" },
              { label: "Page", value: selectedEvidence.page_index ?? "-" },
              { label: "Type", value: selectedEvidence.elem_type ?? "-" },
          ]
        : []

    const highlightWarning = useMemo(() => {
        if (!selectedEvidence) return null
        if (!selectedEvidence.bbox) return "该证据缺少 bbox，高亮不可用。"
        if (selectedEvidence.page_index === null || selectedEvidence.page_index === undefined) {
            return "该证据缺少 page_index，无法跳页。"
        }
        if (Array.isArray(selectedEvidence.bbox) && selectedEvidence.bbox.length > 1) {
            return "证据包含多个 bbox，按当前页渲染。"
        }
        return null
    }, [selectedEvidence])

    const chatDebugSegments = useMemo(() => {
        const segments = []
        if (documentId) {
            segments.push({ label: "Document", value: documentId })
        }
        if (chatId) {
            segments.push({ label: "Chat", value: chatId })
        }
        return segments
    }, [documentId, chatId])

    const handleHighlightClick = () => {
        if (!selectedEvidence) return
        setShowEvidencePopover(true)
    }

    const handleCopyEvidenceText = async () => {
        if (!selectedEvidence) return
        const text = selectedEvidence.text_content || selectedEvidence.snippet || ""
        if (!text) {
            addToast({ type: "info", title: "暂无可复制内容", message: "该证据缺少 text_content/snippet" })
            return
        }
        try {
            if (!navigator?.clipboard?.writeText) {
                throw new Error("浏览器不支持一键复制")
            }
            await navigator.clipboard.writeText(text)
            addToast({ type: "success", title: "已复制到剪贴板", message: "证据文本已可粘贴" })
        } catch (error) {
            addToast({ type: "error", title: "复制失败", message: error.message || "请检查浏览器权限" })
        }
    }

    return (
        <>
            <Breadcrumbs items={breadcrumbs} />

            <div className="meta-toggle">
                <span className="caption muted">固定单文档聊天，PDF 与 Evidence 高亮保持一致。</span>
                <div className="meta-toggle__actions">
                    <Button
                        onClick={() => {
                            setRenameTitle(chatDetail?.title ?? "")
                            setShowRenameModal(true)
                        }}
                        disabled={!chatId || savingChatTitle}
                    >
                        修改聊天名称
                    </Button>
                    <Button variant="ghost" onClick={() => setShowChatDrawer(true)}>
                        聊天列表
                    </Button>
                    <Button variant="ghost" onClick={() => loadChatDetail(chatId)} disabled={!chatId || loadingChat}>
                        {loadingChat ? "刷新中..." : "刷新聊天"}
                    </Button>
                    <Button variant="ghost" onClick={loadChatList} disabled={loadingChatList}>
                        {loadingChatList ? "刷新历史..." : "刷新历史"}
                    </Button>
                    <Button variant="tonal" onClick={handleCreateChat} disabled={creatingChat || !documentDetail?.collection_id}>
                        {creatingChat ? "创建中..." : "新建 Document Chat"}
                    </Button>
                </div>
            </div>

            <div className="meta-panel">
                <div className="meta-panel__header">
                    <div className="stack" style={{ gap: "8px" }}>
                        <div
                            style={{
                                display: "flex",
                                alignItems: "center",
                                gap: "10px",
                                flexWrap: "wrap",
                            }}
                        >
                            <h1 className="page-title">{chatTitle}</h1>
                            {scopeMismatch && <span className="pill warning">文档不匹配或类型异常</span>}
                        </div>
                        <p className="page-subtitle">
                            单文档问答：左侧聊天流 + 右侧固定 PDF 高亮。{loadingDocument && "加载 document..."}
                        </p>
                    </div>
                    <div className="meta-panel__actions">
                        <div className="stack" style={{ gap: "6px", alignItems: "flex-end" }}>
                            <div className="inline-kv">
                                <span className="caption">Doc</span>
                                <strong>#{documentId}</strong>
                            </div>
                            <div className="inline-kv">
                                <span className="caption">Pages</span>
                                <strong>{documentDetail?.num_pages ?? "?"}</strong>
                            </div>
                            <div className="inline-kv">
                                <span className="caption">Elements</span>
                                <strong>{documentDetail?.element_count ?? 0}</strong>
                            </div>
                            <Button
                                variant="ghost"
                                onClick={() => window.open(documentFileUrl, "_blank")}
                                disabled={!documentFileUrl}
                            >
                                打开原始 PDF
                            </Button>
                        </div>
                    </div>
                </div>
            </div>

            <div className="chat-layout" ref={layoutRef} style={layoutStyle}>
                <div className="card chat-panel">
                    <div className="card__header">
                        <div>
                            <h3 className="card__title">聊天流</h3>
                            <p className="caption">展示用户问题、回答与 `[Evidence#no]` 标签。</p>
                        </div>
                        <span className="pill muted">{loadingChat ? "加载中..." : "M5f"}</span>
                    </div>

                    {scopeMismatch && (
                        <div className="banner warning">
                            <div>
                                <strong>当前聊天未绑定此 Document</strong>
                                <p className="caption">请切换到正确的文档聊天或新建一个。</p>
                            </div>
                            {chatDetail?.document_id && (
                                <Button
                                    variant="ghost"
                                    onClick={() => navigate(`/documents/${chatDetail.document_id}/chat/${chatId}`)}
                                >
                                    跳转到文档 {chatDetail.document_id}
                                </Button>
                            )}
                        </div>
                    )}

                    <div
                        className="qa-control-panel"
                        style={{
                            margin: "0 0 12px",
                            padding: "12px",
                            border: "1px solid #e5e7eb",
                            borderRadius: "12px",
                            background: "#f8fafc",
                        }}
                    >
                        <div
                            style={{
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "space-between",
                                gap: "12px",
                                marginBottom: "8px",
                            }}
                        >
                            <div className="stack" style={{ gap: "4px" }}>
                                <strong>QA 控制面板</strong>
                                <span className="caption muted">
                                    仅保留检索/记忆相关可调参数：文本/图片检索 TopK、记忆 TopK、是否页级过滤与搜索模式。
                                </span>
                            </div>
                            <Button variant="ghost" onClick={resetQaControls} type="button">
                                重置为默认
                            </Button>
                        </div>

                        <div
                            style={{
                                display: "grid",
                                gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
                                gap: "12px",
                            }}
                        >
                            <div className="stack" style={{ gap: "4px" }}>
                                <label className="caption" htmlFor="use-image-switch">
                                    启用图片路径
                                </label>
                                <label className="inline-kv" style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}>
                                    <input
                                        id="use-image-switch"
                                        type="checkbox"
                                        checked={useImage}
                                        onChange={(event) => setUseImage(event.target.checked)}
                                    />
                                    <span className="caption">use_image</span>
                                </label>
                            </div>
                            <div className="stack" style={{ gap: "4px" }}>
                                <label className="caption" htmlFor="search-mode-select">
                                    文本检索模式
                                </label>
                                <select
                                    id="search-mode-select"
                                    className="search-bar__select"
                                    value={textSearchMode}
                                    onChange={(event) => setTextSearchMode(event.target.value)}
                                >
                                    <option value="hybrid">混合</option>
                                    <option value="vector">向量</option>
                                    <option value="fulltext">全文</option>
                                </select>
                            </div>
                            <div className="stack" style={{ gap: "4px" }}>
                                <label className="caption" htmlFor="page-toggle">
                                    页级过滤
                                </label>
                                <label className="inline-kv" style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}>
                                    <input
                                        id="page-toggle"
                                        type="checkbox"
                                        checked={usePageInTextRetrieve}
                                        onChange={(event) => setUsePageInTextRetrieve(event.target.checked)}
                                    />
                                    <span className="caption">use_page_in_text_retrieve</span>
                                </label>
                                <input
                                    id="page-topk-input"
                                    className="input"
                                    type="number"
                                    min="1"
                                    max="20"
                                    value={pageRetrieveTopk}
                                    onChange={(event) => setPageRetrieveTopk(event.target.value)}
                                    placeholder="Page TopK（空则使用后端默认）"
                                />
                            </div>
                            <div className="stack" style={{ gap: "4px" }}>
                                <label className="caption" htmlFor="text-retrieve-topk-input">
                                    文本检索 TopK
                                </label>
                                <input
                                    id="text-retrieve-topk-input"
                                    className="input"
                                    type="number"
                                    min="1"
                                    max="20"
                                    value={textRetrieveTopk}
                                    onChange={(event) => setTextRetrieveTopk(event.target.value)}
                                    placeholder="默认 8"
                                />
                            </div>
                            <div className="stack" style={{ gap: "4px" }}>
                                <label className="caption" htmlFor="image-retrieve-topk-input">
                                    图片检索 TopK
                                </label>
                                <input
                                    id="image-retrieve-topk-input"
                                    className="input"
                                    type="number"
                                    min="1"
                                    max="20"
                                    value={imageRetrieveTopk}
                                    onChange={(event) => setImageRetrieveTopk(event.target.value)}
                                    placeholder="默认 2"
                                />
                            </div>
                            <div className="stack" style={{ gap: "4px" }}>
                                <label className="caption" htmlFor="text-memory-topk-input">
                                    记忆文本 TopK
                                </label>
                                <input
                                    id="text-memory-topk-input"
                                    className="input"
                                    type="number"
                                    min="1"
                                    max="20"
                                    value={textMemoryTopk}
                                    onChange={(event) => setTextMemoryTopk(event.target.value)}
                                    placeholder="默认 4"
                                />
                            </div>
                            <div className="stack" style={{ gap: "4px" }}>
                                <label className="caption" htmlFor="image-memory-topk-input">
                                    记忆图片 TopK
                                </label>
                                <input
                                    id="image-memory-topk-input"
                                    className="input"
                                    type="number"
                                    min="1"
                                    max="20"
                                    value={imageMemoryTopk}
                                    onChange={(event) => setImageMemoryTopk(event.target.value)}
                                    placeholder="默认 1"
                                />
                            </div>
                        </div>
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
                                                        onClick={() => handleEvidenceSelect(ev.evidence_no, turn)}
                                                    >
                                                        <span className="pill muted">
                                                            Evidence #{ev.evidence_no ?? "-"}
                                                        </span>
                                                        <span className="caption">
                                                            Doc {ev.document_id ?? "-"} · Page {ev.page_index ?? "-"}
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
                            <Button onClick={handleSendQuestion} disabled={sending || scopeMismatch}>
                                {sending ? "发送中..." : "发送"}
                            </Button>
                        </div>
                    </div>
                </div>

                <div
                    className={`resize-handle${isResizing ? " is-active" : ""}`}
                    role="separator"
                    aria-orientation="vertical"
                    aria-label="拖动调整聊天与 PDF 区域宽度"
                    tabIndex={0}
                    onMouseDown={(event) => {
                        event.preventDefault()
                        handleResizeStart(event.clientX)
                    }}
                    onTouchStart={(event) => {
                        const touch = event.touches?.[0]
                        if (!touch) return
                        event.preventDefault()
                        handleResizeStart(touch.clientX)
                    }}
                    onDoubleClick={resetPanelRatio}
                    onKeyDown={handleResizeKeyDown}
                />

                <div className="stack pdf-column">
                    <div className="card pdf-panel">
                        <div className="card__header pdf-header">
                            <div>
                                <h3 className="card__title">PDF Viewer</h3>
                                <p className="caption">固定 doc_id，点击 Evidence 标签后高亮 bbox。</p>
                            </div>
                            <div className="pdf-header__actions">
                                <Button variant="ghost" onClick={() => setShowChatDrawer(true)}>
                                    聊天列表
                                </Button>
                                {documentId && (
                                    <Button variant="ghost" onClick={() => window.open(documentFileUrl, "_blank")}>
                                        打开原始 PDF
                                    </Button>
                                )}
                            </div>
                        </div>

                        <div className="pdf-toolbar">
                            <div className="pdf-toolbar__row" style={{ justifyContent: "space-between" }}>
                                <div className="stack" style={{ gap: "4px" }}>
                                    <label className="caption">当前文档</label>
                                    <strong>{docName}</strong>
                                    <span className="caption muted">
                                        Doc #{documentId} · Pages {documentDetail?.num_pages ?? "?"}
                                    </span>
                                </div>
                                <div className="pdf-zoom-controls">
                                    <div className="pill muted">缩放</div>
                                    <ZoomOut />
                                    <ZoomPopover />
                                    <ZoomIn />
                                    <Button
                                        variant="ghost"
                                        onClick={() => zoomPluginInstance.zoomTo(SpecialZoomLevel.PageWidth)}
                                    >
                                        重置为页宽
                                    </Button>
                                </div>
                            </div>
                        </div>

                        {!documentId ? (
                            <div className="empty-state">缺少 documentId，无法加载 PDF。</div>
                        ) : (
                            <div className="pdf-viewer">
                                <Worker workerUrl={workerSrc}>
                                    <Viewer
                                        key={viewerKey}
                                        fileUrl={documentFileUrl}
                                        defaultScale={SpecialZoomLevel.PageWidth}
                                        renderPage={(props) => (
                                            <HighlightedPage
                                                renderPageProps={props}
                                                highlights={pageHighlights}
                                                onHighlightClick={handleHighlightClick}
                                            />
                                        )}
                                        initialPage={pageForHighlight ?? 0}
                                        plugins={[navigationPlugin, zoomPluginInstance]}
                                    />
                                </Worker>
                                {showEvidencePopover && selectedEvidence && (
                                    <div className="evidence-popover" role="dialog" aria-label="选中证据信息">
                                        <div className="evidence-popover__header">
                                            <div className="stack" style={{ gap: "4px" }}>
                                                <div className="inline-kv">
                                                    <strong>Evidence #{selectedEvidence.evidence_no ?? "-"}</strong>
                                                    <span className="caption">
                                                        Elem #{selectedEvidence.element_id ?? "-"}
                                                    </span>
                                                </div>
                                                <div className="caption muted">
                                                    Doc {selectedEvidence.document_id ?? "-"} · Page {selectedEvidence.page_index ?? "-"} · Type {selectedEvidence.elem_type ?? "-"}
                                                </div>
                                            </div>
                                            <Button variant="ghost" onClick={() => setShowEvidencePopover(false)}>
                                                关闭
                                            </Button>
                                        </div>
                                        <div className="stack evidence-popover__body">
                                            {selectedEvidence.snippet && (
                                                <div className="stack">
                                                    <div className="caption muted">Snippet</div>
                                                    <div className="code-block code-block--compact">
                                                        {selectedEvidence.snippet}
                                                    </div>
                                                </div>
                                            )}
                                            {selectedEvidence.text_content && (
                                                <div className="stack">
                                                    <div className="caption muted">Text Content</div>
                                                    <div className="code-block code-block--compact">
                                                        {selectedEvidence.text_content}
                                                    </div>
                                                </div>
                                            )}
                                            {!selectedEvidence.snippet && !selectedEvidence.text_content && (
                                                <div className="code-block code-block--compact">无 snippet</div>
                                            )}
                                        </div>
                                        <div className="evidence-popover__actions">
                                            <Button variant="tonal" onClick={handleCopyEvidenceText}>
                                                复制文本内容
                                            </Button>
                                            <span className="caption muted">点击高亮框后弹出，优先复制 text_content。</span>
                                        </div>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    <div className="card">
                        <div className="card__header">
                            <div>
                                <h4 className="card__title">选中证据信息</h4>
                                <p className="caption">点击 Evidence 标签后在此查看元信息与 bbox 状态。</p>
                            </div>
                            {highlightWarning && <span className="pill warning">{highlightWarning}</span>}
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

            <DebugIdFooter segments={chatDebugSegments} />

            <Drawer
                open={showChatDrawer}
                title="Document 聊天列表"
                onClose={() => setShowChatDrawer(false)}
                footer={
                    <Button variant="tonal" onClick={handleCreateChat} disabled={creatingChat}>
                        {creatingChat ? "创建中..." : "新建聊天"}
                    </Button>
                }
            >
                <div className="inline-kv">
                    <span className="caption">来自 /api/documents/{documentId}/chats</span>
                    <Button variant="ghost" onClick={loadChatList} disabled={loadingChatList}>
                        {loadingChatList ? "刷新中..." : "刷新"}
                    </Button>
                </div>
                {loadingChatList ? (
                    <div className="empty-state">加载中...</div>
                ) : chatList.length === 0 ? (
                    <div className="empty-state">暂无聊天，点击下方按钮创建新会话。</div>
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
                                        navigate(`/documents/${documentId}/chat/${chat.id}`)
                                        setShowChatDrawer(false)
                                    }}
                                >
                                    <div>
                                        <strong>{chat.title || `Chat #${chat.id}`}</strong>
                                        <p className="caption">{formatDateTime(chat.created_at)}</p>
                                    </div>
                                    <span className="pill muted">{chat.type}</span>
                                </button>
                            )
                        })}
                    </div>
                )}
            </Drawer>

            <Modal
                open={showRenameModal}
                title="编辑聊天名称"
                description="默认名称为 Chat #id，可在此修改。"
                onClose={() => setShowRenameModal(false)}
                footer={
                    <>
                        <Button variant="ghost" onClick={() => setShowRenameModal(false)}>
                            取消
                        </Button>
                        <Button onClick={handleRenameSave} disabled={savingChatTitle || !chatId}>
                            {savingChatTitle ? "保存中..." : "保存"}
                        </Button>
                    </>
                }
            >
                <div className="stack">
                    <label className="caption" htmlFor="rename-title-input">
                        聊天名称
                    </label>
                    <input
                        id="rename-title-input"
                        className="input"
                        value={renameTitle}
                        onChange={(event) => setRenameTitle(event.target.value)}
                        placeholder={chatId ? `Chat #${chatId}` : "输入聊天名称"}
                        disabled={savingChatTitle}
                    />
                    <p className="caption muted">留空将恢复为默认 Chat #id。</p>
                </div>
            </Modal>
        </>
    )
}
