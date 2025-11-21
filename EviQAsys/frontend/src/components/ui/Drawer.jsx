import { createPortal } from "react-dom"

export default function Drawer({ open, title, children, onClose, footer }) {
    if (!open) return null

    const content = (
        <div className="modal-backdrop" role="dialog" aria-modal="true" onClick={onClose}>
            <aside className="drawer" onClick={(event) => event.stopPropagation()}>
                {title && (
                    <div className="card__header">
                        <h3 className="card__title">{title}</h3>
                    </div>
                )}
                <div className="stack">{children}</div>
                {footer && <div className="modal__footer">{footer}</div>}
            </aside>
        </div>
    )

    return createPortal(content, document.body)
}
