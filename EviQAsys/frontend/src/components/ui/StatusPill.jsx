const statusMap = {
    parsed: { label: "parsed", tone: "success" },
    uploaded: { label: "uploaded", tone: "warn" },
    failed: { label: "failed", tone: "danger" },
}

export default function StatusPill({ status }) {
    const normalized = String(status || "").toLowerCase()
    const tone = statusMap[normalized]?.tone ?? "muted"
    const label = statusMap[normalized]?.label ?? normalized || "unknown"
    return <span className={`pill ${tone}`}>{label}</span>
}
