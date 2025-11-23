## 高亮偏移可能原因 & 逐步排查方案

### 现象
- MinerU 抽取的 bbox（示例 `[96, 294, 485, 640]`, page_idx=0）在 pdf.js 页面尺寸 612×792 上渲染后，高亮落在正文旁边，未精准覆盖 Abstract 段落。

### 可能原因假设
1. **坐标系尺寸不一致**：抽取坐标基于 MinerU 渲染的页图片（宽高约 9xx/9xx），而前端直接用作 PDF 原始尺寸（612×792 points），导致未按比例收缩/放大。
2. **Y 轴原点不同**：MinerU bbox 以左上角为原点；若数据实际以左下角为原点，则需要 `y' = H - y` 翻转。
3. **额外白边/裁剪差异**：矿渣图像可能包含外圈白边或截去页边距，导致需要平移或缩放补偿（非等比）。
4. **页索引/缩放状态**：page_idx 0 vs 1 基准无误，但需要确认 pdf.js 报告的 `page.view` 与我们读取的 `width/height` 是否一致（未旋转、未裁切）。
5. **设备像素比/缩放**：若以 viewport 像素计算再换回 points 可能重复缩放；需确保使用原始 page 尺寸（PDF points）而非屏幕像素。

### 建议的逐步验证与调整
1. **确认基准尺寸**  
   - 通过 pdf.js `page.view` 获取 `origW×origH`（当前已在日志显示 612×792）。  
   - 读取同页所有 bbox 的 maxX/maxY，若明显大于 `origW/H`（例如 >800），说明需要按比例缩放。

2. **计算比例因子并试算**  
   - 取一组 bbox，计算 `scaleX = origW / bboxMaxX`，`scaleY = origH / bboxMaxY`。  
   - 先假设等比：`scale = min(scaleX, scaleY)`，将 bbox 乘 `scale`，观察是否落位正确。  
   - 如果 X/Y 方向偏移不同，再尝试独立缩放 `x *= scaleX`, `y *= scaleY`。

3. **测试 Y 轴翻转**  
   - 在前端加调试开关：`flipY = true` 时使用 `y0' = origH - y1`, `y1' = origH - y0`。  
   - 对比翻转前后位置，确认原点方向。

4. **检查白边/偏移**  
   - 统计所有 bbox 的最小 x/y，若最小值接近 90~100 而非 0，可能表示 MinerU 预裁剪了左右边距；尝试在缩放后再整体平移 `x -= minX`, `y -= minY`（或按固定 margin 比例调整）。

5. **与 pdf.js 文本层对齐校验**  
   - 打开 pdf.js textLayer（临时取消隐藏），选取 Abstract 里一行文字，读取其 clientRect 转回 PDF 坐标（`rect.left * scale / viewport.scale`），与 MinerU bbox 比较，推导转换公式。

6. **按优先级试改前端转换逻辑**  
   - 步骤 2：按等比/独立比例缩放 bbox。  
   - 若仍偏移，步骤 3：加入 Y 翻转。  
   - 若仍偏移，步骤 4：加入平移校正（用最小 bbox 起点或估算白边宽度）。  
   - 每次修改后只改 demo 页，打印转换前后坐标（console）+ 视觉验证。

7. **最终回写转换规则**  
   - 一旦定位正确，沉淀为统一的 bbox 归一化函数（标注：MinerU 坐标基于 XX 尺寸/原点），在 CollectionChat 等实际页面共用。

### 辅助信息
- 当前 PDF page size：`612 × 792`（pdfinfo），与 bbox 最大值（≈900）不符，优先怀疑坐标系缩放问题。  
- bbox 数据来源：`sample_data/..._content_list.json`，疑似基于 MinerU 渲染的 PNG/JPG（宽 900 左右）。  
- 前端目前已使用原始 page 尺寸，不做额外缩放/翻转。
