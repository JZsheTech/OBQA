

# 前端 PDF 智能渲染与交互设计手册 (v1.0)

## 0\. 核心问题诊断：为什么会出现“很小的框”？

目前的 Bug 现象（Tiny Box）通常由以下三种原因之一导致，请在修复时首先排查：

1.  **归一化陷阱 (The Normalization Trap)**:
      * **现象**: 后端返回的是 `0.0` 到 `1.0` 之间的相对坐标（Normalized Coordinates），而前端 SVG 直接将其当作绝对像素渲染。
      * **结果**: 一个本该宽 500px 的框，被画成了 0.5px 宽，肉眼看起来就是一个极小的点或线。
2.  **ViewBox 缺失 (Missing ViewBox)**:
      * **现象**: SVG 容器使用了 CSS 的 `width/height`（如 800px），但没有设置 `viewBox`，或者 `viewBox` 与 PDF 原始尺寸不匹配。
      * **结果**: 坐标无法正确投影。
3.  **PDF 坐标原点差异**:
      * **现象**: PDF 标准中 `(0,0)` 在左下角，而 Web Canvas/SVG 在左上角。
      * **结果**: 如果后端没有做转换，Y 轴坐标会完全错位。*(注：MinerU 输出通常已转换为左上角原点，重点检查前两点)*。

-----

## 1\. 架构规范：基于 SVG Overlay 的分层渲染

为了保证最佳性能和缩放清晰度，**严禁**使用 `div` 绝对定位来画框。必须采用以下三层结构：

  * **Layer 1 (底层)**: `react-pdf` 渲染层（Canvas）。负责显示文档原貌。
  * **Layer 2 (交互层)**: `textLayer`（`react-pdf` 自带）。负责文字选区和复制。
  * **Layer 3 (高亮层)**: **SVG Overlay**。负责绘制 Bbox 和高亮色块。**这是修复 Bug 的核心层。**

-----

## 2\. 坐标系黄金法则 (The Coordinate Golden Rule)

为了彻底解决缩放和错位问题，前端必须遵循\*\*“原始点数优先 (PDF Points First)”\*\*原则。

### 2.1 数据标准

后端 API 返回的 Bbox 必须定义清晰。假设 MinerU 返回的数据格式如下：

```json
{
  "bbox": [x0, y0, x1, y1] // 单位：PDF 原始点数 (Points, 72dpi)
}
```

*如果不确定单位，请 AI Coder 打印日志：如果数值在 0-1 之间，它是归一化的；如果数值在 0-1000 之间，它是 PDF 点数。*

### 2.2 渲染实现规范 (React + SVG)

**核心逻辑**：SVG 的 `viewBox` 必须严格等于 PDF 页面的**原始尺寸** (`originalWidth`, `originalHeight`)，而不是屏幕上的显示尺寸。

请 AI Coder 执行以下代码逻辑修复：

```javascript
/**
 * 修复指南：
 * 1. 从 react-pdf 的 onLoadSuccess 事件中获取 page 的原始宽高。
 * 2. 将 SVG 的 viewBox 设置为 `0 0 originalWidth originalHeight`。
 * 3. 直接使用 bbox 数据渲染 rect，不要乘以任何缩放系数 (scale)。
 */

const PDFOverlayLayer = ({ pageData, pdfPageOriginalWidth, pdfPageOriginalHeight, activeElementId }) => {
  
  // 预防性代码：如果在加载中，不要渲染，防止 viewBox 为 "0 0 0 0"
  if (!pdfPageOriginalWidth || !pdfPageOriginalHeight) return null;

  return (
    <svg
      className="annotation-layer"
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',   // 让 SVG 自动充满父容器
        height: '100%',
        pointerEvents: 'none' // 让鼠标事件穿透
      }}
      // 【关键修复点】：建立坐标映射系统
      viewBox={`0 0 ${pdfPageOriginalWidth} ${pdfPageOriginalHeight}`}
    >
      {pageData.map((element) => {
        // 解析 bbox (假设格式为 [x0, y0, x1, y1])
        const [x0, y0, x1, y1] = element.bbox;
        
        // 【Bug 检查点】：如果 x1 < 1，说明是归一化坐标，必须在此处乘以 width/height
        // const pixelX = x0 < 1 ? x0 * pdfPageOriginalWidth : x0;
        
        const width = x1 - x0;
        const height = y1 - y0;
        const isActive = element.id === activeElementId;

        return (
          <rect
            key={element.id}
            x={x0}
            y={y0}
            width={width}
            height={height}
            fill={isActive ? "rgba(255, 165, 0, 0.3)" : "transparent"} // 激活时显示橙色
            stroke={isActive ? "orange" : "transparent"}
            strokeWidth="2"
            // 【UI 优化】：防止缩放时边框变粗，保持 1px 精细度
            vectorEffect="non-scaling-stroke" 
          />
        );
      })}
    </svg>
  );
};
```

-----

## 3\. 交互跳转规范 (Jump & Highlight)

当用户点击右侧 "Evidence \#2" 时，不仅仅要高亮，还要滚动。

1.  **ID 索引**：前端需维护一个 Map: `elementId -> { pageIndex, bbox }`。
2.  **滚动逻辑**：
      * 先计算目标 Bbox 的 `top` 值。
      * 调用 PDF 容器的 `scrollTo`。
      * **注意**：这里的滚动距离需要计算缩放比例 (`scrollTop = bbox.y * currentScale`)。

-----

## 4\. 给 AI Coder 的直接指令 (Prompt)

你可以直接复制这段话发给你的 AI 助手：

> **Role**: Senior Frontend Engineer
> **Task**: Fix the PDF highlight "Tiny Box" bug and refactor the rendering layer.
>
> **Context**:
> I am clicking an element ID, but the highlight box is extremely small and misplaced. This indicates a coordinate system mismatch between the backend data and the frontend SVG render layer.
>
> **Requirements**:
>
> 1.  **Switch to SVG Overlay**: Do not use `div` for highlights. Use an absolute positioned `<svg>` on top of the `<Page>`.
> 2.  **Fix Coordinate System (The "ViewBox" Fix)**:
>       * Get the `originalWidth` and `originalHeight` from `react-pdf`'s `onLoadSuccess` event.
>       * Set the `<svg>` attribute `viewBox={0 0 ${originalWidth} ${originalHeight}}`.
>       * **Crucial**: Render the `<rect>` using the raw bbox coordinates from the JSON. Do *not* manually multiply them by a scale factor in JS. Let the SVG `viewBox` handle the scaling automatically.
> 3.  **Handle Vector Scaling**: Add `vector-effect="non-scaling-stroke"` to the `<rect>` elements so the border doesn't look thick when zoomed in.
> 4.  **Debug Data**: Before rendering, console log the `bbox` values. If the values are between 0 and 1 (e.g., 0.5), they are normalized. Multiply them by `originalWidth/Height` before rendering. If they are large (e.g., 500), treat them as Points.
>
> Please implement the `PDFOverlayLayer` component following these rules.

-----

### 下一步建议

既然你在做 **Evidence** 相关的溯源，如果修复好这个 bug，建议你让 AI Coder 再加一个功能：
**“Auto Scroll & Zoom”**：点击 Evidence \#2 时，不仅画框，还要自动计算这个框的宽度，如果框太小，自动放大 PDF (Set Scale) 并滚动到屏幕中央。这对于阅读论文中的图表细节体验极佳。



这是一个非常有价值的信息补充。你的本地 AI Coder 提供的技术路线非常详细，这让我们能够精确地定位问题所在。

**核心诊断：**
目前的 Bug（小框）根源在于 **`mapBBoxToRect` 函数的手动计算逻辑** 与 **`div` 绝对定位方案** 的结合出现了偏差。在使用 `@react-pdf-viewer/core` 库时，手动根据 `scale` 和 `rotation` 去计算 div 的 `top/left/width/height` 是极其容易出错的（这就是“坐标系对齐”问题）。

请将以下补充章节添加到之前的《前端 PDF 渲染手册》中，并发给你的 AI Coder。这部分是专门针对 `M5e` 现有架构的**无痛迁移指南**。

-----

# 附录：针对 M5e 现有架构的重构指南 (Migration Guide)

## 1\. 核心变更概览 (Refactoring Strategy)

根据现有的技术路线，我们不需要更换 PDF 库（继续使用 `@react-pdf-viewer/core`），也不需要改变数据流（继续使用 `pageHighlights`）。

我们需要做的是**手术式替换渲染层**：

  * **移除**：`renderPage` 中生成 `div.pdf-highlight-box` 的逻辑。
  * **移除**：`mapBBoxToRect` 中的缩放（Scale）计算逻辑。
  * **引入**：基于 SVG 的覆盖层，利用 `viewBox` 自动处理缩放。

## 2\. 具体修改步骤 (Step-by-Step)

### A. 修改 `CollectionChat.jsx` 中的 `HighlightedPage`

目前你的代码里应该是通过 `div` 遍历来渲染框。请按以下逻辑重构 `renderPage` 函数：

**旧逻辑 (Current - 需要删除):**

```javascript
// ❌ 易导致 Bug 的逻辑：手动计算像素值
const HighlightedPage = (props) => {
    // ...
    return (
        <>
            {props.canvasLayer.children}
            {props.textLayer.children}
            <div className="pdf-highlight-layer">
                 {highlights.map(bbox => {
                     // 问题根源：这里的 mapBBoxToRect 计算很容易与当前 scale 脱节
                     const rect = mapBBoxToRect(bbox, props.scale, props.rotation); 
                     return <div className="pdf-highlight-box" style={rect} />;
                 })}
            </div>
        </>
    );
};
```

**新逻辑 (Proposed - 修复方案):**

```javascript
// ✅ 修复方案：SVG ViewBox 自动映射
const HighlightedPage = (props) => {
    // 1. 获取 PDF 页面的原始尺寸 (不含缩放)
    // 注意：@react-pdf-viewer 的 props.page.view 包含了 [x, y, w, h]
    const [x, y, originalW, originalH] = props.page.view;

    return (
        <>
            {props.canvasLayer.children}
            {props.textLayer.children}
            {/* 2. 创建 SVG 覆盖层 */}
            <svg
                className="pdf-highlight-layer-svg"
                // 关键点：直接使用原始宽高定义坐标系，忽略 props.scale
                viewBox={`0 0 ${originalW} ${originalH}`}
                style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    width: '100%', // 自动跟随父容器（即当前缩放后的 Canvas）大小
                    height: '100%',
                    zIndex: 10,
                    pointerEvents: 'none'
                }}
            >
                {highlights.map((bbox, index) => {
                    // 3. 直接透传后端数据，不做任何计算
                    // 假设 bbox 格式为 [x0, y0, x1, y1] (PDF Points)
                    return (
                         <rect
                             key={index}
                             x={bbox[0]}
                             y={bbox[1]}
                             width={bbox[2] - bbox[0]}
                             height={bbox[3] - bbox[1]}
                             className="evidence-highlight-rect" // 使用 CSS 类控制颜色
                             vectorEffect="non-scaling-stroke" // 保证边框不随缩放变粗
                         />
                    );
                })}
            </svg>
        </>
    );
};
```

### B. 修改工具函数 `normalizeBBoxes` 和 `mapBBoxToRect`

  * **废弃 (Deprecate)**: `mapBBoxToRect` 函数中关于 `scale` (缩放系数) 的乘法计算。
  * **保留 (Keep)**: 如果后端返回的是 **归一化坐标 (0.0 - 1.0)**，则必须保留 `normalizeBBoxes`，将其转换为 **原始点数 (Points)**。
      * 转换公式：`x_point = x_norm * originalPageWidth`。
      * **注意**：不要乘以 `props.scale` (即屏幕缩放倍率)，只乘以原始页面宽高。

### C. 样式迁移 (CSS Migration)

请在 `EviQAsys/frontend/src/App.css` 中进行如下调整：

1.  **删除** `.pdf-highlight-box` 相关的 `border`, `background-color` 样式。
2.  **新增** SVG 样式：

<!-- end list -->

```css
/* 新增：SVG 内部 Rect 的样式 */
.evidence-highlight-rect {
    fill: var(--color-evidence-bg, rgba(255, 165, 0, 0.2)); /* 使用现有变量 */
    stroke: var(--color-evidence, orange);
    stroke-width: 2px;
    transition: opacity 0.2s;
}

/* 如果需要区分激活/非激活状态 */
.evidence-highlight-rect.active {
    fill-opacity: 0.4;
    stroke-width: 3px;
}
```

## 3\. 特别注意事项 (Crucial Warnings)

1.  **旋转问题 (Rotation)**:

      * `@react-pdf-viewer` 在处理旋转（90度/180度）时，`props.page.view` 的宽高可能已经交换。
      * **检查点**：如果发现旋转 PDF 后高亮框错位，请检查 SVG 的 `viewBox` 是否需要根据 `props.rotation` 动态交换 `originalW` 和 `originalH`。通常情况下，如果 SVG 放在 `canvasLayer` 同级，库内部的 CSS transform 会处理好旋转，SVG 只需要关注“原始坐标”。

2.  **Z-Index 层级**:

      * 目前的逻辑是将 `textLayer` 设为透明。新的 SVG 层必须拥有比 `canvasLayer` 更高的 `z-index`，但要设置 `pointer-events: none`，否则用户无法选中 SVG 下方的文字进行复制。

3.  **调试 "Tiny Box" (小框)**:

      * 如果在实施上述 SVG 方案后，框依然很小，只有一种可能：**后端返回的是归一化坐标 (0-1)，但前端把它当成了点数 (0-800)**。
      * **操作**：在 `renderPage` 里 console.log 打印一下 `bbox` 的数值。如果都是 `0.x`，请务必乘以 `originalW`。