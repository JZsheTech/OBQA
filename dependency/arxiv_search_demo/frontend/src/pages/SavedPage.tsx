import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { deleteSavedRecord, fetchSaved, updateSaved } from "../api/papers";
import type { SavedPaper } from "../types";
import SummaryModal from "../components/SummaryModal";

function SavedCard({
  item,
  onUpdate,
  onDelete,
  onShowSummary,
  busy
}: {
  item: SavedPaper;
  onUpdate: (id: number, tags: string, note: string) => void;
  onDelete: (id: number) => void;
  onShowSummary: (paper: SavedPaper["paper"]) => void;
  busy: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [tags, setTags] = useState(item.tags || "");
  const [note, setNote] = useState(item.note || "");

  const saveEdit = () => {
    onUpdate(item.id, tags, note);
    setEditing(false);
  };

  return (
    <div className="paper-card">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
        <div>
          <Link to={`/papers/${item.id}`}><strong>{item.paper.title}</strong></Link>
          <div className="paper-meta" style={{ marginTop: 6 }}>
            <span className="badge">arXiv {item.paper.arxiv_id}{item.paper.version ? ` ${item.paper.version}` : ""}</span>
            <span className="badge">收藏 {new Date(item.created_at).toLocaleDateString()}</span>
            {item.paper.primary_category && <span className="badge">分类 {item.paper.primary_category}</span>}
          </div>
          <div className="muted" style={{ marginTop: 8 }}>
            <span
              className="summary-snippet"
              role="button"
              tabIndex={0}
              onClick={() => onShowSummary(item.paper)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  onShowSummary(item.paper);
                }
              }}
            >
              {item.paper.summary?.slice(0, 180)}
              {item.paper.summary && item.paper.summary.length > 180 ? "..." : ""}
              {!item.paper.summary && "暂无摘要"}
            </span>
          </div>
          <div className="paper-meta">
            {(item.tags || "").split(",").filter(Boolean).map((t) => (
              <span className="tag" key={t.trim()}>{t.trim()}</span>
            ))}
          </div>
        </div>
        <div className="float-actions">
          {!editing ? (
            <button className="btn secondary" onClick={() => setEditing(true)}>编辑标注</button>
          ) : (
            <button className="btn primary" onClick={saveEdit} disabled={busy}>保存</button>
          )}
          <button className="btn ghost" onClick={() => onDelete(item.id)} disabled={busy}>删除</button>
        </div>
      </div>
      {editing && (
        <div className="grid-2">
          <div className="field">
            <label>Tags</label>
            <input value={tags} onChange={(e) => setTags(e.target.value)} />
          </div>
          <div className="field">
            <label>Note</label>
            <input value={note} onChange={(e) => setNote(e.target.value)} />
          </div>
        </div>
      )}
    </div>
  );
}

function SavedPage() {
  const [items, setItems] = useState<SavedPaper[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [total, setTotal] = useState(0);
  const [keyword, setKeyword] = useState("");
  const [author, setAuthor] = useState("");
  const [category, setCategory] = useState("");
  const [tag, setTag] = useState("");
  const [sortBy, setSortBy] = useState<"created_at" | "published" | "updated">("created_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [previewPaper, setPreviewPaper] = useState<SavedPaper["paper"] | null>(null);

  const load = async (overridePage?: number) => {
    const pageToUse = overridePage ?? page;
    setLoading(true);
    setError(null);
    try {
      const resp = await fetchSaved({
        page: pageToUse,
        page_size: pageSize,
        keyword: keyword || undefined,
        author: author || undefined,
        category: category || undefined,
        tag: tag || undefined,
        sort_by: sortBy,
        sort_order: sortOrder
      });
      setItems(resp.items);
      setTotal(resp.total);
    } catch (err: unknown) {
      setError((err as Error).message || "加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [page, sortBy, sortOrder]);

  const handleUpdate = async (id: number, tagsValue: string, noteValue: string) => {
    setBusyId(id);
    try {
      await updateSaved(id, { tags: tagsValue, note: noteValue });
      await load();
    } catch (err: unknown) {
      setError((err as Error).message || "更新失败");
    } finally {
      setBusyId(null);
    }
  };

  const handleDelete = async (id: number) => {
    setBusyId(id);
    try {
      await deleteSavedRecord(id);
      await load();
    } catch (err: unknown) {
      setError((err as Error).message || "删除失败");
    } finally {
      setBusyId(null);
    }
  };

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  const applyFilters = () => {
    setPage(1);
    void load(1);
  };

  return (
    <div className="stack">
      <div className="hero">
        <h1>我的收藏</h1>
        <p>本地数据库中的论文，支持过滤、排序、编辑标注。</p>
      </div>

      <div className="panel stack">
        <div className="grid-2">
          <div className="field">
            <label>标题/摘要关键词</label>
            <input value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="LLM / retrieval" />
          </div>
          <div className="field">
            <label>作者关键词</label>
            <input value={author} onChange={(e) => setAuthor(e.target.value)} />
          </div>
          <div className="field">
            <label>分类</label>
            <input value={category} onChange={(e) => setCategory(e.target.value)} placeholder="cs.LG" />
          </div>
          <div className="field">
            <label>标签</label>
            <input value={tag} onChange={(e) => setTag(e.target.value)} placeholder="llm, graph" />
          </div>
        </div>
        <div className="split" style={{ alignItems: "center", justifyContent: "space-between" }}>
          <div className="split">
            <select value={sortBy} onChange={(e) => setSortBy(e.target.value as typeof sortBy)}>
              <option value="created_at">按收藏时间</option>
              <option value="published">按发表时间</option>
              <option value="updated">按更新日期</option>
            </select>
            <select value={sortOrder} onChange={(e) => setSortOrder(e.target.value as typeof sortOrder)}>
              <option value="desc">降序</option>
              <option value="asc">升序</option>
            </select>
          </div>
          <button className="btn primary" onClick={applyFilters} disabled={loading}>应用过滤</button>
        </div>
        {error && <div style={{ color: "#ff9b9b" }}>{error}</div>}
      </div>

      {loading ? (
        <div className="muted">加载中...</div>
      ) : (
        <div className="stack">
          {items.map((item) => (
            <SavedCard
              key={item.id}
              item={item}
              onUpdate={handleUpdate}
              onDelete={handleDelete}
              onShowSummary={setPreviewPaper}
              busy={busyId === item.id}
            />
          ))}
          {items.length === 0 && <div className="muted">暂无收藏。</div>}
        </div>
      )}

      <div className="split" style={{ justifyContent: "space-between" }}>
        <div className="muted">
          第 {page} / {totalPages} 页，共 {total} 条
        </div>
        <div className="float-actions">
          <button className="btn ghost" disabled={page <= 1} onClick={() => setPage((p) => Math.max(1, p - 1))}>
            上一页
          </button>
          <button className="btn ghost" disabled={page >= totalPages} onClick={() => setPage((p) => Math.min(totalPages, p + 1))}>
            下一页
          </button>
        </div>
      </div>

      <SummaryModal
        open={!!previewPaper}
        title={previewPaper?.title}
        summary={previewPaper?.summary}
        onClose={() => setPreviewPaper(null)}
      />
    </div>
  );
}

export default SavedPage;
