import { useCallback, useEffect, useMemo, useState } from "react"
import { SpecialZoomLevel, Viewer, Worker } from "@react-pdf-viewer/core"
import "@react-pdf-viewer/core/lib/styles/index.css"
import { zoomPlugin } from "@react-pdf-viewer/zoom"
import "@react-pdf-viewer/zoom/lib/styles/index.css"
import workerSrc from "pdfjs-dist/build/pdf.worker.min.js?url"

import { buildDemoPdfUrl } from "../api/client"
import PageHeader from "../components/layout/PageHeader"
import Button from "../components/ui/Button"

const DEMO_HIGHLIGHTS = {
    // MinerU bbox: [x, y, width, height] on a 0~1000 grid.
    0: [[96, 294, 485, 640]],
}

function getPageOriginalSize(page, width, height, scale) {
    const view = page?.view
    const [, , rawWidth, rawHeight] = Array.isArray(view) ? view : []
    const originalWidth = Number(rawWidth)
    const originalHeight = Number(rawHeight)
    if (Number.isFinite(originalWidth) && Number.isFinite(originalHeight) && originalWidth > 0 && originalHeight > 0) {
        return { originalWidth, originalHeight }
    }
    const fallbackWidth = Number.isFinite(width) && Number.isFinite(scale) && scale !== 0 ? width / scale : null
    const fallbackHeight = Number.isFinite(height) && Number.isFinite(scale) && scale !== 0 ? height / scale : null
    if (
        Number.isFinite(fallbackWidth) &&
        Number.isFinite(fallbackHeight) &&
        fallbackWidth > 0 &&
        fallbackHeight > 0
    ) {
        return { originalWidth: fallbackWidth, originalHeight: fallbackHeight }
    }
    return { originalWidth: null, originalHeight: null }
}

function resolveBBoxToRect(bbox, originalWidth, originalHeight) {
    if (!Array.isArray(bbox) || bbox.length !== 4) return null
    const numeric = bbox.map((value) => Number(value))
    if (numeric.some((value) => !Number.isFinite(value))) return null
    const [rawX, rawY, rawWidth, rawHeight] = numeric
    const hasPageSize =
        Number.isFinite(originalWidth) && Number.isFinite(originalHeight) && originalWidth > 0 && originalHeight > 0
    if (!hasPageSize) return null

    if (rawWidth <= 0 || rawHeight <= 0) return null

    const inUnitRange = numeric.every((value) => value >= 0 && value <= 1)
    const inThousandRange = !inUnitRange && numeric.every((value) => value >= 0 && value <= 1000)

    // MinerU bbox 使用 0~1000 的基准，需要按实际页面宽高缩放。
    const scaleX = inUnitRange ? originalWidth : inThousandRange ? originalWidth / 1000 : 1
    const scaleY = inUnitRange ? originalHeight : inThousandRange ? originalHeight / 1000 : 1

    const x = rawX * scaleX
    const y = rawY * scaleY
    const width = rawWidth * scaleX
    const height = rawHeight * scaleY

    if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) return null
    return { x, y, width, height, isNormalized: inUnitRange || inThousandRange }
}

function HighlightedPage({ renderPageProps, highlights, onMetrics }) {
    const {
        annotationLayer,
        canvasLayer,
        textLayer,
        canvasLayerRendered,
        textLayerRendered,
        markRendered,
        pageIndex,
        scale,
        width,
        height,
        page,
    } = renderPageProps

    const { originalWidth, originalHeight } = getPageOriginalSize(page, width, height, scale)
    const activeHighlights = highlights?.[pageIndex] ?? []

    const pageRects = useMemo(() => {
        if (!originalWidth || !originalHeight) return []
        return activeHighlights
            .map((bbox, index) => {
                const rect = resolveBBoxToRect(bbox, originalWidth, originalHeight)
                if (!rect) return null
                return { rect, key: `${pageIndex}-${index}` }
            })
            .filter(Boolean)
    }, [activeHighlights, originalHeight, originalWidth, pageIndex])

    const onMetricsReady = useCallback(() => {
        if (!onMetrics) return
        onMetrics({
            pageIndex,
            originalWidth,
            originalHeight,
            highlightCount: activeHighlights.length,
        })
    }, [activeHighlights.length, onMetrics, originalHeight, originalWidth, pageIndex])

    useEffect(() => {
        if (canvasLayerRendered && textLayerRendered) {
            markRendered(pageIndex)
            onMetricsReady()
        }
    }, [canvasLayerRendered, markRendered, onMetricsReady, pageIndex, textLayerRendered])

    return (
        <>
            {canvasLayer.children}
            {textLayer.children}
            {annotationLayer.children}
            {pageRects.length > 0 && originalWidth && originalHeight ? (
                <svg
                    className="pdf-highlight-layer"
                    aria-hidden="true"
                    viewBox={`0 0 ${originalWidth} ${originalHeight}`}
                    style={{
                        position: "absolute",
                        inset: 0,
                        width: "100%",
                        height: "100%",
                        pointerEvents: "none",
                        zIndex: 10,
                    }}
                >
                    {pageRects.map(({ rect, key }) => (
                        <rect
                            key={key}
                            x={rect.x}
                            y={rect.y}
                            width={rect.width}
                            height={rect.height}
                            className="evidence-highlight-rect"
                            vectorEffect="non-scaling-stroke"
                        />
                    ))}
                </svg>
            ) : null}
        </>
    )
}

export default function PdfHighlightDemo() {
    const [pageMetrics, setPageMetrics] = useState(null)
    const pdfUrl = useMemo(() => buildDemoPdfUrl(), [])
    // zoomPlugin 调用需要在组件顶层执行，避免在 useMemo 内部触发 Hook 顺序错误
    const zoomPluginInstance = zoomPlugin()
    const { ZoomIn, ZoomOut, ZoomPopover } = zoomPluginInstance

    const handleMetrics = useCallback(
        (metrics) => {
            if (!metrics) return
            setPageMetrics(metrics)
        },
        [setPageMetrics],
    )

    return (
        <>
            <PageHeader
                breadcrumbs={[{ label: "Home", href: "/" }, { label: "PDF Evidence Demo" }]}
                title="PDF Evidence 高亮测试"
                subtitle="仅渲染指定样例 PDF，在第 1 页高亮给定 bbox，用于排查定位偏移问题。"
                actions={
                    <Button variant="ghost" onClick={() => window.open(pdfUrl, "_blank", "noopener,noreferrer")}>
                        在新标签页打开 PDF
                    </Button>
                }
            />

            <div className="stack" style={{ gap: "var(--space-4)" }}>
                <div className="card">
                    <div className="card__header">
                        <h3 className="card__title">调试信息</h3>
                        <span className="pill muted">只读</span>
                    </div>
                    <div className="info-grid">
                        <div className="info-item">
                            <div className="caption">PDF 路径</div>
                            <strong>
                                sample_data/test_convert/1-Cui et al. - 2019 - Class-Balanced Loss Based on Effective Number of Samples/auto/1-Cui et al. - 2019 - Class-Balanced Loss Based on Effective Number of Samples_origin.pdf
                            </strong>
                            <p className="caption">由后端 /api/debug/pdf-evidence-demo 透传</p>
                        </div>
                        <div className="info-item">
                            <div className="caption">BBox (0~1000 基准)</div>
                            <strong>[96, 294, 485, 640]</strong>
                            <p className="caption">page_index = 0 · 渲染时按页面尺寸等比缩放</p>
                        </div>
                        <div className="info-item">
                            <div className="caption">页面尺寸</div>
                            <strong>
                                {pageMetrics?.originalWidth ? `${pageMetrics.originalWidth} × ${pageMetrics.originalHeight}` : "待加载"}
                            </strong>
                            <p className="caption">
                                {pageMetrics ? `第 ${pageMetrics.pageIndex + 1} 页 · ${pageMetrics.highlightCount} 个高亮` : "等待 viewer 渲染"}
                            </p>
                        </div>
                    </div>
                    <p className="caption muted">
                        该页面只包含一个 PDF viewer，确保高亮坐标转换逻辑简单可观测。
                    </p>
                </div>

                <div className="card">
                    <div className="card__header">
                        <h3 className="card__title">PDF Viewer（单页高亮）</h3>
                        <span className="pill muted">仅使用本地样例</span>
                    </div>
                    <div className="pdf-demo-controls">
                        <div className="pill muted">缩放</div>
                        <ZoomOut />
                        <ZoomPopover />
                        <ZoomIn />
                        <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => zoomPluginInstance.zoomTo(SpecialZoomLevel.PageWidth)}
                        >
                            重置为页宽
                        </Button>
                        <span className="caption muted">默认按页宽铺满，可手动放大/缩小。</span>
                    </div>
                    <div className="pdf-viewer" style={{ height: "calc(100vh - 220px)" }}>
                        <Worker workerUrl={workerSrc}>
                            <Viewer
                                fileUrl={pdfUrl}
                                renderPage={(props) => (
                                    <HighlightedPage renderPageProps={props} highlights={DEMO_HIGHLIGHTS} onMetrics={handleMetrics} />
                                )}
                                defaultScale={SpecialZoomLevel.PageWidth}
                                plugins={[zoomPluginInstance]}
                                initialPage={0}
                            />
                        </Worker>
                    </div>
                </div>
            </div>
        </>
    )
}
