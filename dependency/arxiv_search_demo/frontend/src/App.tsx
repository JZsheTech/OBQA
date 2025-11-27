import { NavLink, Route, Routes, Navigate, useLocation } from "react-router-dom";
import SearchPage from "./pages/SearchPage";
import SavedPage from "./pages/SavedPage";
import PaperDetailPage from "./pages/PaperDetailPage";

function Navbar() {
  const location = useLocation();
  return (
    <div className="navbar">
      <div>
        <div style={{ fontWeight: 700, letterSpacing: 0.4 }}>Arxiv Lab</div>
        <div className="muted" style={{ fontSize: 12 }}>
          在线检索 · 本地收藏
        </div>
      </div>
      <div className="nav-links">
        <NavLink to="/search" className={`nav-link ${location.pathname.startsWith("/search") ? "active" : ""}`}>
          检索
        </NavLink>
        <NavLink to="/saved" className={`nav-link ${location.pathname.startsWith("/saved") ? "active" : ""}`}>
          我的收藏
        </NavLink>
      </div>
    </div>
  );
}

function App() {
  return (
    <div className="app-shell">
      <Navbar />
      <Routes>
        <Route path="/" element={<Navigate to="/search" replace />} />
        <Route path="/search" element={<SearchPage />} />
        <Route path="/saved" element={<SavedPage />} />
        <Route path="/papers/:id" element={<PaperDetailPage />} />
        <Route path="*" element={<Navigate to="/search" replace />} />
      </Routes>
    </div>
  );
}

export default App;
