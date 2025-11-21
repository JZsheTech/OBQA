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

export async function listDocuments(collectionId) {
    if (!collectionId) {
        throw new Error("Collection id is required")
    }
    return request(`/collections/${collectionId}/documents`)
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
