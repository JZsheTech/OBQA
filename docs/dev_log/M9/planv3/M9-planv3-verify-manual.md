# M9-planv3 手工验证指引

## 验证目标
- 文本 chunk 以字符数窗口(`MIN_CHARACTOR_CHUNK_SIZE` / `MAX_CHARACTOR_CHUNK_SIZE`)在同一 `level_nav` 内顺序合并，无 overlap，单元素超长则独立成块。
- image/table 元素从合并列表中剥离，按 section 末尾输出 chunk，并在嵌入时使用 caption/文本 + `image_base64` 做图文联合。

## 前置
- 使用真实 PDF（例如 `sample_data/pdf_doc` 内文件或新的业务文档），不要使用 mock 数据。
- 建议先清理表与上传目录，保证观测到的 chunk 来自本次解析。

## 操作步骤
1) **解析真实文档**
   - 运行手工脚本完成 MinerU 解析：  
     `python EviQAsys/backend/tests/manual/test_m2_ingest.py --reset-db --clear-uploads --keep --pdf <真实PDF路径>`  
     记录创建的 `collection_id` 与 `doc_id`。

2) **重建索引并检查 chunk 切分**
   - 准备临时检查脚本（示例可保存为 `tmp_planv3_check.py`）：
     ```python
     from __future__ import annotations
     import argparse
     from collections import defaultdict
     from EviQAsys.backend.app.env_setting import MIN_CHARACTOR_CHUNK_SIZE, MAX_CHARACTOR_CHUNK_SIZE
     from EviQAsys.backend.app.repositories import ChunksRepository
     from EviQAsys.backend.app.services.index import DocumentIndexer

     def main() -> None:
         parser = argparse.ArgumentParser()
         parser.add_argument("--collection-id", type=int, required=True)
         parser.add_argument("--doc-id", type=int, required=True)
         args = parser.parse_args()

         indexer = DocumentIndexer()
         indexer.embed_document(collection_id=args.collection_id, doc_id=args.doc_id)

         repo = ChunksRepository()
         chunks = repo.list_by_document(args.doc_id)
         by_nav: dict[str, list[dict]] = defaultdict(list)
         for chunk in chunks:
             by_nav[chunk.get("level_nav") or "root"].append(chunk)

         print(f"MIN={MIN_CHARACTOR_CHUNK_SIZE}, MAX={MAX_CHARACTOR_CHUNK_SIZE}")
         for nav, items in by_nav.items():
             print(f"\n[section] {nav} chunks={len(items)}")
             for chunk in items:
                 text = (chunk.get("chunk_text_main") or "")
                 length = len(text)
                 marker = ""
                 if chunk["chunk_type"] == "text":
                     if length > MAX_CHARACTOR_CHUNK_SIZE:
                         marker = " (text>MAX, 应仅为超长单元素)"
                     elif length < MIN_CHARACTOR_CHUNK_SIZE and chunk is not items[-1]:
                         marker = " (text<MIN，需确认是否因边界截断)"
                 print(f"  order={chunk['order']} type={chunk['chunk_type']} len={length} elem_ids={chunk.get('elem_ids')} {marker}")
             tail = [c["chunk_type"] for c in items if c["chunk_type"] in {"image", "table"}]
             if tail:
                 print(f"  media tail types={tail} (应位于该 section 末尾)")

     if __name__ == "__main__":
         main()
     ```
   - 执行：`python tmp_planv3_check.py --collection-id <cid> --doc-id <docid>`  
     期望：文本 chunk 长度大部分落在 MIN~MAX，若出现 `>MAX` 仅限单元素；同一 `level_nav` 下的 image/table 行被打印在末尾。

3) **多模态嵌入抽查**
   - 在同一脚本或新脚本中追加对首个 image/table chunk 的检查：读取对应 `elem_ids[0]` 的元素，确认 `text_caption`/`text_content` 已写入 `chunk_text_main`，`image_base64` 不为空且 `vec_embedding` 已生成（可在数据库中查看向量列非空、长度与 `VECTOR_DIM` 一致）。
   - 如需目视确认，可打印 chunk_text_main 与 caption，保证图文信息被纳入嵌入文本。

4) **QA 端点验证（可选）**
   - 通过 `/api/chats/{chat_id}/turns` 提问，确认命中的 chunk 顺序符合 section 顺序，image/table 证据仍可按尾部顺序展开。

## 结果记录
- 将上述检查的控制台输出（chunk 长度分布、媒体尾部顺序、向量是否落库等）随同 PDF 名称与时间戳记录在本目录，便于后续回溯。
