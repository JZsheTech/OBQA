import { createPortal } from "react-dom"

export default function Modal({
    open,
    title,
    description,
    children,
    footer,
    onClose,
    size = "md",
    className = "",
}) {
    if (!open) return null

    const classes = ["modal", size && size !== "md" ? `modal--${size}` : "", className]
        .filter(Boolean)
        .join(" ")

    const modalContent = (
        <div className="modal-backdrop" role="dialog" aria-modal="true" onClick={onClose}>
            <div className={classes} onClick={(event) => event.stopPropagation()}>
                <div className="card__header">
                    <div>
                        <h3 className="card__title">{title}</h3>
                        {description && <p className="page-subtitle">{description}</p>}
                    </div>
                </div>
                <div className="modal__body">{children}</div>
                {footer && <div className="modal__footer">{footer}</div>}
            </div>
        </div>
    )

    return createPortal(modalContent, document.body)
}
