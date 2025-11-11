from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Iterable, List, Optional

from .parse_pdf_mineru import parse_pdf_with_mineru


def parse_pdf_with_mineru_parallel(
    pdf_path: str,
    pdf_file_names: Iterable[str],
    *,
    url: str = "http://localhost:18543/file_parse",
    lang_list=None,
    backend: str = "pipeline",
    return_md: bool = True,
    return_images: bool = False,
    return_content_list: bool = False,
    max_workers: Optional[int] = 4,
) -> List[dict]:
    """
    并行调用 parse_pdf_with_mineru，对一批 PDF 文件执行 MinerU 解析。

    Args:
        pdf_path: PDF 文件所在目录路径。
        pdf_file_names: 需要解析的 PDF 文件名序列。
        url: MinerU 服务地址。
        lang_list: 语言列表，默认为 ["ch"]。
        backend: MinerU 后端标识。
        return_md: 是否返回 Markdown 内容。
        return_images: 是否返回图片内容。
        return_content_list: 是否返回内容列表。
        max_workers: 线程池最大并发数，默认按照输入文件数量确定。

    Returns:
        List[dict]: res_contents 列表，与 pdf_file_names 的顺序一致。
    """

    pdf_file_names = list(pdf_file_names)
    if not pdf_file_names:
        return []

    if max_workers is None:
        max_workers = len(pdf_file_names) or 1
    else:
        max_workers = max(1, min(max_workers, len(pdf_file_names)))

    def _worker(file_name: str) -> dict:
        return parse_pdf_with_mineru(
            pdf_path,
            file_name,
            url=url,
            lang_list=lang_list,
            backend=backend,
            return_md=return_md,
            return_images=return_images,
            return_content_list=return_content_list,
        )

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(_worker, pdf_file_names))

    return results
