MinerU 的 `draw_layout_bbox` 负责把解析得到的版面结构 bbox 叠加到原 PDF 上，生成带高亮的调试 PDF。下面按执行流程拆解逻辑，方便在前端复用。

核心输入
- `pdf_info`: MinerU 解析后的结构化结果，按页组织，`para_blocks` 存放布局块，`discarded_blocks` 是被丢弃的块。
- `pdf_bytes`: 原始 PDF 的二进制数据，用于读出页面尺寸并生成输出 PDF。
- `out_path`/`filename`: 输出路径和文件名。

关键辅助函数
- `cal_canvas_rect(page, bbox)`: 将 MinerU 的 bbox（`[x0, y0, x1, y1]`，基于原 PDF 坐标）转换为 ReportLab canvas 需要的矩形参数 `[x, y, w, h]`，并处理 `/Rotate` 元数据（0/90/180/270 度时交换宽高或翻转坐标）。
- `draw_bbox_without_number(...)`: 按给定颜色绘制一组矩形，可以实心填充或仅描边。
- `draw_bbox_with_number(...)`: 在矩形右上角附近绘制编号，可选是否同时画框。布局编号用的是这个函数的“仅编号”模式。

步骤 1：按类型收集每页 bbox
- 初始化多个列表，分别存放 table/figure/code/title/text/equation/list/index 等类型，以及 `discarded_blocks`。
- 遍历每页的 `para_blocks`：
  - Table/Image/Code 先遍历各自的子块，提取 body、caption、footnote 的 bbox。对 table footnote，如果标记了跨页（`SplitFlag.CROSS_PAGE`），则跳过，避免错误重叠。
  - Title/Text/RefText/InterlineEquation/List/Index 直接取块的 bbox。List 额外把子块（list item）的 bbox 单独收集，便于用不同的线型描绘。
- 将上述每类的 per-page 列表追加到对应的总列表，保持与页索引对齐。

步骤 2：构建整体布局序列（用于编号）
- 重新遍历每页的 `para_blocks`，按照视觉阅读顺序生成 `layout_bbox_list`：
  - 文字类（Text/RefText/Title/InterlineEquation/List/Index）直接追加。
  - Image/Code 追加其子块 bbox。
  - Table 子块按 `table_caption -> table_body -> table_footnote` 排序再追加，保持与版式一致；跨页的子块仍然跳过。
- 结果是一个二维列表：外层按页，内层是该页需要编号的布局块 bbox。

步骤 3：为每页生成叠加层
- 用 `PdfReader` 读取 `pdf_bytes`，`PdfWriter` 用来收集输出页面。
- 对每一页：
  - 记录原页面宽高，创建同尺寸的 ReportLab `canvas`。
  - 按类型批量绘制 bbox。颜色/填充约定：
    - Code body: `#6600CC` 半透明填充；Code caption: `#CC99FF` 填充。
    - Dropped: `#9E9E9E` 填充。
    - Table body/caption/footnote: `#CCCC00` / `#FFFF66` / `#E5FFCC` 填充。
    - Image body/caption/footnote: `#99FF33` / `#66B2FF` / `#FFB266` 填充。
    - Title: `#6666FF` 填充；Text: `#99004C` 填充。
    - Interline equation: `#00FF00` 填充。
    - List + Index: `#28A95C` 填充；List item 单独用相同颜色描边（不填充），便于区分父 list 区域。
    - 最后调用 `draw_bbox_with_number(..., draw_bbox=False)`，用红色在 `layout_bbox_list` 上画出序号，不再绘制边框，便于阅读顺序确认。
  - 将 canvas 写入内存，读回为单页 overlay PDF，然后 `merge_page` 到原页。使用新的 `PageObject` 避免直接修改原页面对象。

步骤 4：输出
- 将合成后的页面逐页加入 `PdfWriter`，最终写入 `f\"{out_path}/{filename}\"`。

前端复用提示
- 只要把 `layout_bbox_list`（按视觉顺序）、以及各类型的 bbox 列表按页返回到前端，就能在 React/PDF canvas 上用同样的颜色规则高亮。
- 坐标换算需考虑页面旋转：当前实现使用 `cal_canvas_rect` 做 0/90/180/270 度适配，并将 PDF 左下为原点的坐标转换到绘制坐标系。前端在使用如 PDF.js 或 canvas 时，需要做等价的旋转/翻转处理以对齐。
