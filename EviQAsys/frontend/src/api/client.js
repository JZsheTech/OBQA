const RAW_API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:9075/api"
const API_BASE = RAW_API_BASE.replace(/\/+$/, "")
const API_HOST = API_BASE.replace(/\/api$/, "")

export class ApiError extends Error {
    constructor(message, payload, status) {
        super(message)
        this.name = "ApiError"
        this.payload = payload
        this.status = status
    }
}

async function parseJsonSafely(response) {
    try {
        return await response.json()
    } catch (error) {
        console.warn("Response is not JSON", error)
        return null
    }
}

export async function request(path, { method = "GET", body, headers, signal } = {}) {
    const isAbsolute = /^https?:\/\//.test(path)
    const target = isAbsolute ? path : `${API_BASE}${path}`
    const isFormData = body instanceof FormData

    const requestInit = {
        method,
        headers: { ...(headers ?? {}) },
        signal,
    }

    if (body !== undefined) {
        requestInit.body = isFormData ? body : JSON.stringify(body)
    }

    if (!isFormData && body !== undefined) {
        requestInit.headers["Content-Type"] = requestInit.headers["Content-Type"] ?? "application/json"
    }

    const response = await fetch(target, requestInit)
    const payload = await parseJsonSafely(response)

    const usesEnvelope = payload && typeof payload === "object" && "code" in payload
    const success = usesEnvelope ? payload.code === "OK" : response.ok

    if (!success) {
        throw new ApiError(
            payload?.message || payload?.detail || `Request failed with status ${response.status}`,
            payload,
            response.status,
        )
    }

    return usesEnvelope && "data" in payload ? payload.data : payload
}

export async function healthCheck() {
    const url = `${API_HOST}/healthz`
    const response = await fetch(url)
    const payload = await parseJsonSafely(response)
    if (!response.ok) {
        throw new ApiError(`Health check failed (${response.status})`, payload, response.status)
    }
    return payload ?? { ok: true }
}

export async function listCollections({ searchField, keyword } = {}) {
    const params = new URLSearchParams()
    if (searchField) {
        params.set("search_field", searchField)
    }
    if (keyword) {
        params.set("keyword", keyword)
    }
    const query = params.toString()
    const path = query ? `/collections?${query}` : "/collections"
    return request(path)
}

export async function createCollection({ name, description }) {
    const trimmedName = (name ?? "").trim()
    if (!trimmedName) {
        throw new Error("Collection name is required")
    }
    return request("/collections", {
        method: "POST",
        body: {
            name: trimmedName,
            description: (description ?? "").trim() || null,
        },
    })
}

export async function deleteCollection(collectionId) {
    if (!collectionId) {
        throw new Error("Collection id is required")
    }
    return request(`/collections/${collectionId}`, { method: "DELETE" })
}

export async function updateCollection(collectionId, { name, description } = {}) {
    if (!collectionId) {
        throw new Error("Collection id is required")
    }
    const payload = {}
    if (name !== undefined) {
        payload.name = name
    }
    if (description !== undefined) {
        payload.description = description
    }
    if (Object.keys(payload).length === 0) {
        throw new Error("At least one field (name/description) is required")
    }
    const trimmedName = payload.name !== undefined ? (payload.name ?? "").trim() : undefined
    if (trimmedName !== undefined) {
        if (!trimmedName) {
            throw new Error("Collection name cannot be empty")
        }
        payload.name = trimmedName
    }
    if (payload.description !== undefined) {
        payload.description = (payload.description ?? "").trim()
    }
    return request(`/collections/${collectionId}`, {
        method: "PATCH",
        body: payload,
    })
}

export async function uploadDocument(collectionId, file) {
    if (!collectionId) {
        throw new Error("Collection id is required")
    }
    if (!file) {
        throw new Error("File is required")
    }

    const formData = new FormData()
    formData.append("file", file)
    return request(`/collections/${collectionId}/documents`, {
        method: "POST",
        body: formData,
    })
}

export async function getCollectionDetail(collectionId) {
    if (!collectionId) {
        throw new Error("Collection id is required")
    }
    return request(`/collections/${collectionId}`)
}

export async function listDocuments(collectionId, { searchField, keyword } = {}) {
    if (!collectionId) {
        throw new Error("Collection id is required")
    }
    const params = new URLSearchParams()
    if (searchField) {
        params.set("search_field", searchField)
    }
    if (keyword) {
        params.set("keyword", keyword)
    }
    const query = params.toString()
    const path = query ? `/collections/${collectionId}/documents?${query}` : `/collections/${collectionId}/documents`
    return request(path)
}

export async function deleteDocument(documentId) {
    if (!documentId) {
        throw new Error("Document id is required")
    }
    return request(`/documents/${documentId}`, { method: "DELETE" })
}

export async function listCollectionChats(collectionId) {
    if (!collectionId) {
        throw new Error("Collection id is required")
    }
    return request(`/collections/${collectionId}/chats`)
}

export async function createCollectionChat(collectionId, { title, docId } = {}) {
    if (!collectionId) {
        throw new Error("Collection id is required")
    }
    const body = { title: title?.trim() || null }
    if (docId !== undefined && docId !== null) {
        const numericDocId = Number(docId)
        if (!Number.isFinite(numericDocId)) {
            throw new Error("docId must be a number")
        }
        body.doc_id = numericDocId
    }
    return request(`/collections/${collectionId}/chats`, {
        method: "POST",
        body,
    })
}

export async function createDocumentChat({ documentId, collectionId, title } = {}) {
    if (!documentId) {
        throw new Error("Document id is required")
    }
    if (!collectionId) {
        throw new Error("Collection id is required to create document chat")
    }
    return createCollectionChat(collectionId, { title, docId: documentId })
}

export async function getChatDetail(chatId) {
    if (!chatId) {
        throw new Error("Chat id is required")
    }
    return request(`/chats/${chatId}`)
}

export async function updateChat(chatId, { title } = {}) {
    if (!chatId) {
        throw new Error("Chat id is required")
    }
    return request(`/chats/${chatId}`, {
        method: "PATCH",
        body: { title: title?.trim() || null },
    })
}

export async function deleteChat(chatId) {
    if (!chatId) {
        throw new Error("Chat id is required")
    }
    return request(`/chats/${chatId}`, { method: "DELETE" })
}

export async function createTurn(
    chatId,
    {
        question,
        topK,
        retrievalMode,
        elemTypes,
        searchMode,
        maxHistoryTurns,
        enableImageVqa,
        enableMemorySummarizer,
        pageTopK,
        enablePageFilter,
    } = {},
) {
    const trimmedQuestion = (question ?? "").trim()
    if (!chatId) {
        throw new Error("Chat id is required")
    }
    if (!trimmedQuestion) {
        throw new Error("Question is required")
    }
    const numericTopK = topK == null ? undefined : Number(topK)
    const body = {
        question: trimmedQuestion,
    }
    if (Number.isFinite(numericTopK)) {
        body.top_k = numericTopK
    }
    if (retrievalMode) {
        body.retrieval_mode = retrievalMode
    }
    if (Array.isArray(elemTypes) && elemTypes.length) {
        body.elem_types = elemTypes
    }
    if (searchMode) {
        body.search_mode = searchMode
    }
    if (maxHistoryTurns !== undefined && maxHistoryTurns !== null) {
        const numericHistory = Number(maxHistoryTurns)
        if (Number.isFinite(numericHistory)) {
            body.max_history_turns = numericHistory
        }
    }
    if (pageTopK !== undefined && pageTopK !== null) {
        const numericPageTopK = Number(pageTopK)
        if (Number.isFinite(numericPageTopK)) {
            body.page_top_k = numericPageTopK
        }
    }
    if (enablePageFilter !== undefined) {
        body.enable_page_filter = Boolean(enablePageFilter)
    }
    if (enableImageVqa !== undefined) {
        body.enable_image_vqa = Boolean(enableImageVqa)
    }
    if (enableMemorySummarizer !== undefined) {
        body.enable_memory_summarizer = Boolean(enableMemorySummarizer)
    }
    return request(`/chats/${chatId}/turns`, {
        method: "POST",
        body,
    })
}

export async function getTurnEvidences(turnId) {
    if (!turnId) {
        throw new Error("Turn id is required")
    }
    return request(`/turns/${turnId}/evidences`)
}

export async function getDocumentDetail(documentId) {
    if (!documentId) {
        throw new Error("Document id is required")
    }
    return request(`/documents/${documentId}`)
}

export async function listDocumentChats(documentId) {
    if (!documentId) {
        throw new Error("Document id is required")
    }
    return request(`/documents/${documentId}/chats`)
}

export async function listChatHistory() {
    return request("/chat-history")
}

export function buildDocumentFileUrl(documentId) {
    if (!documentId) {
        throw new Error("Document id is required")
    }
    return `${API_BASE}/documents/${documentId}/file`
}

export function buildDemoPdfUrl() {
    return `${API_BASE}/debug/pdf-evidence-demo`
}

export async function runRetrieval({
    collectionId,
    query,
    topK = 5,
    docId,
    elemTypes,
    searchMode = "hybrid",
}) {
    const keyword = (query ?? "").trim()
    if (!collectionId) {
        throw new Error("collectionId is required for retrieval")
    }
    if (!keyword) {
        throw new Error("query is required for retrieval")
    }
    const params = new URLSearchParams()
    params.set("collection_id", collectionId)
    params.set("query", keyword)
    params.set("top_k", topK)
    if (docId) {
        params.set("doc_id", docId)
    }
    if (elemTypes && elemTypes.length) {
        params.set("elem_types", elemTypes.join(","))
    }
    if (searchMode) {
        params.set("search_mode", searchMode)
    }
    return request(`/retrieval/test?${params.toString()}`)
}

export async function searchArxiv({
    allTerms,
    title,
    abstract,
    author,
    categories,
    dateMode,
    dateFrom,
    dateTo,
    sortBy,
    sortOrder,
    maxResults,
    idList,
} = {}) {
    const payload = {
        all_terms: allTerms,
        title,
        abstract,
        author,
        categories,
        date_mode: dateMode,
        date_from: dateFrom,
        date_to: dateTo,
        sort_by: sortBy,
        sort_order: sortOrder,
        max_results: maxResults,
        id_list: idList,
    }
    return request("/arxiv/search", { method: "POST", body: payload })
}

export async function saveArxivFavorite({ paper, tags, note }) {
    if (!paper || !paper.arxiv_id) {
        throw new Error("paper with arxiv_id is required")
    }
    return request("/arxiv/favorites", {
        method: "POST",
        body: { paper, tags: tags ?? null, note: note ?? null },
    })
}

export async function listArxivFavorites({
    page = 1,
    pageSize = 20,
    keyword,
    author,
    category,
    tag,
    note,
    sortBy,
    sortOrder,
} = {}) {
    const params = new URLSearchParams()
    params.set("page", page)
    params.set("page_size", pageSize)
    if (keyword) params.set("keyword", keyword)
    if (author) params.set("author", author)
    if (category) params.set("category", category)
    if (tag) params.set("tag", tag)
    if (note) params.set("note", note)
    if (sortBy) params.set("sort_by", sortBy)
    if (sortOrder) params.set("sort_order", sortOrder)
    return request(`/arxiv/favorites?${params.toString()}`)
}

export async function getArxivFavorite(favoriteId) {
    if (!favoriteId) {
        throw new Error("favoriteId is required")
    }
    return request(`/arxiv/favorites/${favoriteId}`)
}

export async function updateArxivFavorite(favoriteId, { tags, note } = {}) {
    if (!favoriteId) {
        throw new Error("favoriteId is required")
    }
    if (tags === undefined && note === undefined) {
        throw new Error("tags or note is required to update favorite")
    }
    return request(`/arxiv/favorites/${favoriteId}`, {
        method: "PATCH",
        body: { tags, note },
    })
}

export async function deleteArxivFavorite(favoriteId) {
    if (!favoriteId) {
        throw new Error("favoriteId is required")
    }
    return request(`/arxiv/favorites/${favoriteId}`, { method: "DELETE" })
}

export async function importArxivFavorite(favoriteId, { collectionId }) {
    if (!favoriteId) {
        throw new Error("favoriteId is required")
    }
    if (!collectionId) {
        throw new Error("collectionId is required")
    }
    return request(`/arxiv/favorites/${favoriteId}/import`, {
        method: "POST",
        body: { collection_id: collectionId },
    })
}
