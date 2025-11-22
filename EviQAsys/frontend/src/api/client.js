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

export async function listCollectionChats(collectionId) {
    if (!collectionId) {
        throw new Error("Collection id is required")
    }
    return request(`/collections/${collectionId}/chats`)
}

export async function runRetrieval({
    collectionId,
    query,
    topK = 5,
    docId,
    elemTypes,
    searchMode = "vector",
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
