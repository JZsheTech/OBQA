import { Fragment } from "react"
import { Link } from "react-router-dom"

export default function Breadcrumbs({ items }) {
    if (!items || items.length === 0) return null

    return (
        <div className="breadcrumb">
            {items.map((item, index) => {
                const isLast = index === items.length - 1
                return (
                    <Fragment key={item.label + index}>
                        <span className={`breadcrumb__item${isLast ? " breadcrumb__item--active" : ""}`}>
                            {item.href && !isLast ? <Link to={item.href}>{item.label}</Link> : item.label}
                        </span>
                        {!isLast && <span aria-hidden="true">/</span>}
                    </Fragment>
                )
            })}
        </div>
    )
}
