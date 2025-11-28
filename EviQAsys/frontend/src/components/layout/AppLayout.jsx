import { Link, NavLink, Outlet, useLocation } from "react-router-dom"

const tabs = [
    {
        label: "知识库主页",
        to: "/",
        match: (pathname) =>
            pathname === "/" ||
            pathname.startsWith("/collections") ||
            pathname.startsWith("/documents"),
    },
    {
        label: "arXiv 搜索",
        to: "/arxiv/search",
        match: (pathname) => pathname.startsWith("/arxiv/search"),
    },
    {
        label: "arXiv 收藏夹",
        to: "/arxiv/favorites",
        match: (pathname) => pathname.startsWith("/arxiv/favorites"),
    },
    {
        label: "Chat 历史",
        to: "/chat-history",
        match: (pathname) => pathname.startsWith("/chat-history"),
    },
]

function tabClassName(pathname, tab) {
    const active = tab.match ? tab.match(pathname) : pathname.startsWith(tab.to)
    return `top-tab${active ? " top-tab--active" : ""}`
}

function formatBaseLabel(base) {
    if (!base) return "API 未配置"
    try {
        const url = new URL(base)
        return url.host ?? base
    } catch {
        return base
    }
}

export default function AppLayout() {
    const apiBase = (import.meta.env.VITE_API_BASE ?? "http://127.0.0.1:9075/api").replace(/\/+$/, "")
    const location = useLocation()
    const isChatPage = location.pathname.includes("/chat/")

    return (
        <div className="app-shell">
            <header className="app-shell__topbar">
                <Link className="brand" to="/">
                    <span className="brand-mark">EQ</span>
                    <span>
                        EviQAsys
                        <div className="caption">Evidence-based QA Console</div>
                    </span>
                </Link>
                <div className="top-actions">
                    <span className="pill muted">API: {formatBaseLabel(apiBase)}</span>
                    <div className="avatar" aria-hidden="true"></div>
                </div>
            </header>

            <nav className="top-tabs" aria-label="Primary">
                {tabs.map((tab) => (
                    <NavLink
                        key={tab.to}
                        to={tab.to}
                        className={() => tabClassName(location.pathname, tab)}
                        end={false}
                    >
                        {tab.label}
                    </NavLink>
                ))}
            </nav>

            <main className="app-shell__body">
                <div className={`content-container${isChatPage ? " content-container--fluid" : ""}`}>
                    <Outlet context={{ currentPath: location.pathname }} />
                </div>
            </main>
        </div>
    )
}
