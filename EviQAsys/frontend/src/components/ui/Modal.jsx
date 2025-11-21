import { createPortal } from "react-dom"

export default function Modal({ open, title, description, children, footer, onClose }) {
    if (!open) return null

    const modalContent = (
        <div className="modal-backdrop" role="dialog" aria-modal="true" onClick={onClose}>
            <div className="modal" onClick={(event) => event.stopPropagation()}>
                <div className="card__header">
                    <div>
                        <h3 className="card__title">{title}</h3>
                        {description && <p className="page-subtitle">{description}</p>}
                    </div>
                </div>
                <div>{children}</div>
                {footer && <div className="modal__footer">{footer}</div>}
            </div>
        </div>
    )

    return createPortal(modalContent, document.body)
}
