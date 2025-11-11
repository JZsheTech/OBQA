export async function healthCheck() {
    const res = await fetch("http://127.0.0.1:9075/healthz")
    if (!res.ok) {
    throw new Error(`Health check failed: ${res.status}`)
    }
    return res.json() // returns { ok: boolean }
}