import { createPortal } from "react-dom";

interface SummaryModalProps {
  open: boolean;
  title?: string | null;
  summary?: string | null;
  onClose: () => void;
}

function SummaryModal({ open, title, summary, onClose }: SummaryModalProps) {
  if (!open) return null;

  const content = summary?.trim() ? summary : "暂无摘要内容。";

  return createPortal(
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <div className="modal-label">摘要全文</div>
            {title && <div className="modal-title">{title}</div>}
          </div>
          <button className="btn ghost" onClick={onClose}>
            关闭
          </button>
        </div>
        <div className="modal-body">
          <p style={{ margin: 0, whiteSpace: "pre-wrap" }}>{content}</p>
        </div>
      </div>
    </div>,
    document.body
  );
}

export default SummaryModal;
