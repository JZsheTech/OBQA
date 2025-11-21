import { Link } from "react-router-dom"

export default function NotFound() {
    return (
        <div className="card">
            <h3 className="card__title">页面未找到</h3>
            <p className="caption">该路由尚未配置或正在开发中。</p>
            <Link to="/" className="btn btn-primary">
                返回首页
            </Link>
        </div>
    )
}
