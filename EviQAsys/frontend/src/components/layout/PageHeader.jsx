import Breadcrumbs from "../ui/Breadcrumbs"

export default function PageHeader({ title, subtitle, breadcrumbs, actions }) {
    return (
        <>
            {breadcrumbs && breadcrumbs.length > 0 && <Breadcrumbs items={breadcrumbs} />}
            <div className="page-header">
                <div>
                    <h1 className="page-title">{title}</h1>
                    {subtitle && <p className="page-subtitle">{subtitle}</p>}
                </div>
                {actions && <div className="page-actions">{actions}</div>}
            </div>
        </>
    )
}
