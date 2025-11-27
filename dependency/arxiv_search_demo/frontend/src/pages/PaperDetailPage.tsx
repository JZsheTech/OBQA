import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { fetchSavedDetail, updateSaved } from "../api/papers";
import type { SavedPaper } from "../types";

function Row({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <div className="field">
      <label>{label}</label>
      <div>{value}</div>
    </div>
  );
}

function PaperDetailPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<SavedPaper | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tags, setTags] = useState("");
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);

  const load = async () => {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const resp = await fetchSavedDetail(Number(id));
      setData(resp);
      setTags(resp.tags || "");
      setNote(resp.note || "");
    } catch (err: unknown) {
      setError((err as Error).message || "加载失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, [id]);

  const save = async () => {
    if (!id) return;
    setSaving(true);
    try {
      const updated = await updateSaved(Number(id), { tags, note });
      setData(updated);
    } catch (err: unknown) {
      setError((err as Error).message || "保存失败");
    } finally {
      setSaving(false);
    }
  };

  if (!id) return <div className="muted">未提供 ID</div>;
  if (loading) return <div className="muted">加载中...</div>;
  if (error) return <div style={{ color: "#ff9b9b" }}>{error}</div>;
  if (!data) return <div className="muted">未找到记录</div>;

  const p = data.paper;

  return (
    <div className="stack">
      <div className="hero">
        <h1>{p.title}</h1>
        <p>收藏于 {new Date(data.created_at).toLocaleString()} · 更新 {new Date(data.updated_at).toLocaleString()}</p>
      </div>
      <div className="panel stack">
        <div className="split" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <div className="paper-meta">
            <span className="badge">arXiv {p.arxiv_id}{p.version ? ` ${p.version}` : ""}</span>
            {p.primary_category && <span className="badge">分类 {p.primary_category}</span>}
            {p.published && <span className="badge">发表 {new Date(p.published).toLocaleDateString()}</span>}
            {p.updated && <span className="badge">更新 {new Date(p.updated).toLocaleDateString()}</span>}
          </div>
          <div className="float-actions">
            {p.abs_url && (
              <a className="btn ghost" href={p.abs_url} target="_blank" rel="noreferrer">
                Arxiv 页面
              </a>
            )}
            {p.pdf_url && (
              <a className="btn primary" href={p.pdf_url} target="_blank" rel="noreferrer">
                打开 PDF
              </a>
            )}
          </div>
        </div>
        <Row label="作者" value={p.authors.join(", ")} />
        <Row label="摘要" value={p.summary} />
        <Row label="DOI" value={p.doi} />
        <Row label="期刊引用" value={p.journal_ref} />
        <Row label="分类" value={p.categories.join(", ")} />
        <div className="grid-2">
          <div className="field">
            <label>Tags</label>
            <input value={tags} onChange={(e) => setTags(e.target.value)} />
          </div>
          <div className="field">
            <label>备注</label>
            <input value={note} onChange={(e) => setNote(e.target.value)} />
          </div>
        </div>
        <div className="split" style={{ justifyContent: "flex-end" }}>
          <button className="btn secondary" onClick={() => navigate(-1)}>返回</button>
          <button className="btn primary" onClick={save} disabled={saving}>{saving ? "保存中..." : "保存修改"}</button>
        </div>
      </div>
    </div>
  );
}

export default PaperDetailPage;
