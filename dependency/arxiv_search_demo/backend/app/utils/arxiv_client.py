# arxiv_client.py
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Any, Dict, List, Literal, Optional

import arxiv

# ---- 数据结构 ----

SortBy = Literal["relevance", "submittedDate", "lastUpdatedDate"]
SortOrder = Literal["ascending", "descending"]
DateMode = Literal["submitted", "updated"]  # 对应 submittedDate / lastUpdatedDate


@dataclass
class ArxivSearchParams:
    # 字段搜索
    all_terms: Optional[str] = None      # all:
    title: Optional[str] = None          # ti:
    abstract: Optional[str] = None       # abs:
    author: Optional[str] = None         # au:
    categories: Optional[List[str]] = None  # cat:cs.LG OR cat:cs.AI

    # 时间范围
    date_mode: Optional[DateMode] = None     # "submitted" / "updated"
    date_from: Optional[date] = None         # 起始日期（含）
    date_to: Optional[date] = None           # 结束日期（含）

    # 其它参数
    start: int = 0
    max_results: int = 20                   # 会在内部强制 <= 50
    sort_by: SortBy = "relevance"
    sort_order: SortOrder = "descending"

    # 可选：按 id_list 精确查询（与 search_query 互斥，用于 detail/补充）
    id_list: Optional[List[str]] = None


@dataclass
class ArxivPaper:
    arxiv_id: str
    version: Optional[str]
    title: str
    summary: str
    authors: List[str]
    primary_category: Optional[str]
    categories: List[str]
    published: Optional[datetime]
    updated: Optional[datetime]
    pdf_url: Optional[str]
    abs_url: Optional[str]
    doi: Optional[str]
    journal_ref: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---- 工具函数 ----

def _format_date_for_range(d: date, start: bool) -> str:
    """
    arXiv 日期格式: YYYYMMDDhhmmss
    我们只管日期，时间用 000000 / 235959 填充。
    """
    base = d.strftime("%Y%m%d")
    return base + ("000000" if start else "235959")


def build_search_query(params: ArxivSearchParams) -> str:
    """
    根据搜索参数构造 arXiv 的 search_query 字符串。
    只负责 search_query，不处理 id_list。
    """
    parts: List[str] = []

    if params.all_terms:
        # all: 仅作用于元数据字段（标题、摘要、作者、评论、journal_ref 等），不包含 PDF 正文
        parts.append(f"all:{params.all_terms}")

    if params.title:
        parts.append(f"ti:{params.title}")

    if params.abstract:
        parts.append(f"abs:{params.abstract}")

    if params.author:
        parts.append(f"au:{params.author}")

    if params.categories:
        # (cat:cs.LG OR cat:cs.AI ...)
        cat_expr = " OR ".join(f"cat:{c}" for c in params.categories)
        parts.append(f"({cat_expr})")

    # 时间范围
    if params.date_mode and (params.date_from or params.date_to):
        if params.date_mode == "submitted":
            field = "submittedDate"
        else:
            field = "lastUpdatedDate"

        # 没给就用一个非常宽的范围
        df = params.date_from or date(1990, 1, 1)
        dt = params.date_to or date.today()

        s = _format_date_for_range(df, start=True)
        e = _format_date_for_range(dt, start=False)
        parts.append(f"{field}:[{s} TO {e}]")

    # 用 AND 串联所有条件
    if not parts:
        # 没有任何条件时，arXiv 不允许完全空查询，这里给个兜底。
        return "all:electron"

    return " AND ".join(parts)


def _to_sort_criterion(sort_by: SortBy) -> arxiv.SortCriterion:
    if sort_by == "submittedDate":
        return arxiv.SortCriterion.SubmittedDate
    if sort_by == "lastUpdatedDate":
        return arxiv.SortCriterion.LastUpdatedDate
    return arxiv.SortCriterion.Relevance


def _to_sort_order(order: SortOrder) -> arxiv.SortOrder:
    return (
        arxiv.SortOrder.Ascending
        if order == "ascending"
        else arxiv.SortOrder.Descending
    )


def _parse_arxiv_id(entry_id: str) -> tuple[str, Optional[str]]:
    """
    entry_id 形如: 'http://arxiv.org/abs/2506.05176v3'
    拆成 (base_id, version) → ('2506.05176', 'v3')
    """
    last = entry_id.rsplit("/", 1)[-1]  # 2506.05176v3
    # 从右往左找到第一个 'v' 并且后面全是数字
    if "v" in last:
        base, ver = last.split("v", 1)
        if ver.isdigit():
            return base, f"v{ver}"
    return last, None


def _parse_result(result: arxiv.Result) -> ArxivPaper:
    arxiv_id, version = _parse_arxiv_id(result.entry_id)

    authors = [a.name for a in result.authors] if getattr(result, "authors", None) else []

    # category 列表
    categories = list(getattr(result, "categories", []))
    primary_category = getattr(result, "primary_category", None)

    return ArxivPaper(
        arxiv_id=arxiv_id,
        version=version,
        title=result.title.strip() if result.title else "",
        summary=result.summary.strip() if result.summary else "",
        authors=authors,
        primary_category=primary_category,
        categories=categories,
        published=getattr(result, "published", None),
        updated=getattr(result, "updated", None),
        pdf_url=getattr(result, "pdf_url", None),
        abs_url=result.entry_id,
        doi=getattr(result, "doi", None),
        journal_ref=getattr(result, "journal_ref", None),
    )


# ---- 对外主函数 ----

def search_arxiv(
    params: ArxivSearchParams,
    client: Optional[arxiv.Client] = None,
) -> List[Dict[str, Any]]:
    """
    安全调用 arxiv API，返回 dict 列表。
    - 自动限制 max_results <= 50
    - 默认使用 arxiv.Client(page_size=50, delay_seconds=3, num_retries=3)
    - 支持 search_query / id_list 两种模式
    """
    max_results = min(params.max_results, 50)

    if client is None:
        client = arxiv.Client(
            page_size=max_results,  # 一页拿完
            delay_seconds=3,        # 官方建议：至少 3 秒一请求
            num_retries=3,          # 简单自动重试
        )

    if params.id_list:
        # 按 id_list 查询，用于详情或精确命中
        search = arxiv.Search(
            id_list=params.id_list,
            max_results=max_results,
        )
    else:
        query = build_search_query(params)
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=_to_sort_criterion(params.sort_by),
            sort_order=_to_sort_order(params.sort_order),
        )

    results: List[Dict[str, Any]] = []
    for res in client.results(search):
        paper = _parse_result(res)
        results.append(paper.to_dict())

    return results
