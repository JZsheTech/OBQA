import { FormEvent, useMemo, useState } from "react";
import { searchArxiv } from "../api/arxiv";
import { savePaper } from "../api/papers";
import type { ArxivPaper, SearchRequest } from "../types";
import SummaryModal from "../components/SummaryModal";

const defaultRequest: SearchRequest = {
  all_terms: "",
  title: "",
  abstract: "",
  author: "",
  categories: [],
  date_mode: null,
  date_from: "",
  date_to: "",
  sort_by: "relevance",
  sort_order: "descending",
  max_results: 10
};

function PaperCard({
  paper,
  onSave,
  onShowSummary,
  saving,
  saved
}: {
  paper: ArxivPaper;
  onSave: (paper: ArxivPaper) => void;
  onShowSummary: (paper: ArxivPaper) => void;
  saving: boolean;
  saved: boolean;
}) {
  const summary = useMemo(() => {
    if (!paper.summary) return "";
    return paper.summary.length > 320 ? `${paper.summary.slice(0, 320)}...` : paper.summary;
  }, [paper.summary]);

  return (
    <div className="paper-card">
      <div style={{ display: "flex", justifyContent: "space-between", gap: 10, alignItems: "flex-start" }}>
        <div>
          <a href={paper.abs_url || "#"} target="_blank" rel="noreferrer">
            <strong>{paper.title}</strong>
          </a>
          <div className="paper-meta" style={{ marginTop: 6 }}>
            <span className="badge">作者 {paper.authors.slice(0, 3).join(", ")}{paper.authors.length > 3 ? " 等" : ""}</span>
            {paper.primary_category && <span className="badge">主类 {paper.primary_category}</span>}
            {paper.published && <span className="badge">发表 {new Date(paper.published).toLocaleDateString()}</span>}
            {paper.updated && <span className="badge">更新 {new Date(paper.updated).toLocaleDateString()}</span>}
          </div>
        </div>
        <div className="float-actions">
          <a className="btn ghost" href={paper.pdf_url || paper.abs_url || "#"} target="_blank" rel="noreferrer">
            PDF
          </a>
          <button className="btn primary" disabled={saving || saved} onClick={() => onSave(paper)}>
            {saved ? "已收藏" : saving ? "收藏中..." : "收藏"}
          </button>
        </div>
      </div>
      <div
        className="muted summary-snippet"
        role="button"
        tabIndex={0}
        onClick={() => onShowSummary(paper)}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            onShowSummary(paper);
          }
        }}
      >
        {summary || "暂无摘要"}
      </div>
      <div className="paper-meta">
        {paper.categories.map((c) => (
          <span key={c} className="pill">
            {c}
          </span>
        ))}
      </div>
    </div>
  );
}

function SearchPage() {
  const [form, setForm] = useState<SearchRequest>(defaultRequest);
  const [categoryInput, setCategoryInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [results, setResults] = useState<ArxivPaper[]>([]);
  const [savingId, setSavingId] = useState<string | null>(null);
  const [savedMap, setSavedMap] = useState<Record<string, boolean>>({});
  const [saveNote, setSaveNote] = useState("");
  const [saveTags, setSaveTags] = useState("");
  const [previewPaper, setPreviewPaper] = useState<ArxivPaper | null>(null);

  const submit = async (evt: FormEvent) => {
    evt.preventDefault();
    setError(null);
    setLoading(true);
    const payload: SearchRequest = {
      ...form,
      categories: categoryInput
        .split(",")
        .map((c) => c.trim())
        .filter(Boolean),
      date_mode: form.date_mode ?? null,
      date_from: form.date_from || null,
      date_to: form.date_to || null
    };

    try {
      const items = await searchArxiv(payload);
      setResults(items);
    } catch (err: unknown) {
      setError((err as Error).message || "搜索失败");
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async (paper: ArxivPaper) => {
    if (savingId) return;
    setSavingId(paper.arxiv_id);
    try {
      await savePaper({
        paper,
        tags: saveTags || undefined,
        note: saveNote || undefined
      });
      setSavedMap((prev) => ({ ...prev, [paper.arxiv_id]: true }));
    } catch (err: unknown) {
      setError((err as Error).message || "收藏失败");
    } finally {
      setSavingId(null);
    }
  };

  return (
    <div className="stack">
      <div className="hero">
        <h1>Arxiv 检索</h1>
        <p>组合关键词、分类、时间范围，一次拿到最多 50 条结果，支持直接收藏。</p>
      </div>

      <form className="panel stack" onSubmit={submit}>
        <div className="grid-2">
          <div className="field">
            <label>关键词（元数据，非 PDF 全文）</label>
            <input
              // arXiv 的 all: 只搜索标题/摘要/作者/分类等元数据，不会检索 PDF 正文
              placeholder="跨标题/摘要/作者等元数据的关键词"
              value={form.all_terms ?? ""}
              onChange={(e) => setForm({ ...form, all_terms: e.target.value })}
            />
          </div>
          <div className="field">
            <label>标题包含</label>
            <input value={form.title ?? ""} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          </div>
          <div className="field">
            <label>摘要包含</label>
            <input value={form.abstract ?? ""} onChange={(e) => setForm({ ...form, abstract: e.target.value })} />
          </div>
          <div className="field">
            <label>作者</label>
            <input value={form.author ?? ""} onChange={(e) => setForm({ ...form, author: e.target.value })} />
          </div>
          <div className="field">
            <label>分类（逗号分隔，例如 cs.LG, cs.AI）</label>
            <input value={categoryInput} onChange={(e) => setCategoryInput(e.target.value)} />
          </div>
          <div className="field">
            <label>日期模式</label>
            <select
              value={form.date_mode ?? ""}
              onChange={(e) => setForm({ ...form, date_mode: e.target.value ? (e.target.value as "submitted" | "updated") : null })}
            >
              <option value="">不限制</option>
              <option value="submitted">提交时间</option>
              <option value="updated">更新时间</option>
            </select>
          </div>
          <div className="field">
            <label>起始日期</label>
            <input type="date" value={form.date_from ?? ""} onChange={(e) => setForm({ ...form, date_from: e.target.value })} />
          </div>
          <div className="field">
            <label>结束日期</label>
            <input type="date" value={form.date_to ?? ""} onChange={(e) => setForm({ ...form, date_to: e.target.value })} />
          </div>
          <div className="field">
            <label>排序</label>
            <div className="split">
              <select value={form.sort_by} onChange={(e) => setForm({ ...form, sort_by: e.target.value as SearchRequest["sort_by"] })}>
                <option value="relevance">相关度</option>
                <option value="submittedDate">提交时间</option>
                <option value="lastUpdatedDate">更新时间</option>
              </select>
              <select value={form.sort_order} onChange={(e) => setForm({ ...form, sort_order: e.target.value as SearchRequest["sort_order"] })}>
                <option value="descending">降序</option>
                <option value="ascending">升序</option>
              </select>
            </div>
          </div>
          <div className="field">
            <label>最多条数（1-50）</label>
            <input
              type="number"
              min={1}
              max={50}
              value={form.max_results ?? 10}
              onChange={(e) => setForm({ ...form, max_results: Number(e.target.value) })}
            />
          </div>
        </div>
        <div className="split" style={{ justifyContent: "space-between", alignItems: "center" }}>
          <div className="split">
            <div className="field">
              <label>收藏 Tags（可选，逗号分隔）</label>
              <input value={saveTags} onChange={(e) => setSaveTags(e.target.value)} placeholder="llm, arxiv" />
            </div>
            <div className="field" style={{ minWidth: 260 }}>
              <label>收藏备注（可选）</label>
              <input value={saveNote} onChange={(e) => setSaveNote(e.target.value)} placeholder="这篇和项目相关" />
            </div>
          </div>
          <button className="btn primary" type="submit" disabled={loading}>
            {loading ? "检索中..." : "开始搜索"}
          </button>
        </div>
        {error && <div style={{ color: "#ff9b9b" }}>{error}</div>}
      </form>

      <div className="stack">
        {results.map((paper) => (
          <PaperCard
            key={paper.arxiv_id + paper.version}
            paper={paper}
            onSave={handleSave}
            onShowSummary={setPreviewPaper}
            saving={savingId === paper.arxiv_id}
            saved={!!savedMap[paper.arxiv_id]}
          />
        ))}
        {!loading && results.length === 0 && <div className="muted">暂无结果，先试着搜索吧。</div>}
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

export default SearchPage;
