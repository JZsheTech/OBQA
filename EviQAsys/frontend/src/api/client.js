const API_BASE = import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:9075/api"

export async function healthCheck() {
    const res = await fetch("http://127.0.0.1:9075/healthz")
    if (!res.ok) {
        throw new Error(`Health check failed: ${res.status}`)
    }
    return res.json()
}

export async function listDocuments(collectionId) {
    const res = await fetch(`${API_BASE}/collections/${collectionId}/documents`)
    const payload = await res.json()
    if (!res.ok) {
        throw new Error(payload?.message ?? "Failed to load documents")
    }
    return payload?.data ?? []
}

export async function uploadDocument(collectionId, file) {
    const formData = new FormData()
    formData.append("file", file)
    const res = await fetch(`${API_BASE}/collections/${collectionId}/documents`, {
        method: "POST",
        body: formData,
    })
    const payload = await res.json()
    if (!res.ok) {
        throw new Error(payload?.detail ?? payload?.message ?? "Upload failed")
    }
    return payload?.data
}
