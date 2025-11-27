export default function DebugIdFooter({ segments = [] }) {
    const visibleSegments = (segments || []).filter(
        (segment) => segment && segment.value !== undefined && segment.value !== null && segment.value !== "",
    )

    if (visibleSegments.length === 0) return null

    return (
        <div className="id-debug-footer" role="note" aria-label="debug-ids">
            <span className="caption muted">调试 ID</span>
            <div className="id-debug-footer__segments">
                {visibleSegments.map((segment, index) => (
                    <span key={`${segment.label}-${segment.value}`} className="id-debug-chip">
                        {segment.label} #{segment.value}
                        {index < visibleSegments.length - 1 ? <span className="id-debug-separator">&gt;</span> : null}
                    </span>
                ))}
            </div>
        </div>
    )
}
