import { useCallback, useMemo } from "react"
import ReactMarkdown from "react-markdown"
import remarkBreaks from "remark-breaks"
import remarkGfm from "remark-gfm"
import remarkMath from "remark-math"
import rehypeKatex from "rehype-katex"
import "katex/dist/katex.min.css"

const EVIDENCE_REGEX = /(\[?\s*(Evidence|Elem)\s*#\s*(\d+)\s*\]?)/gi
const BRACKET_BLOCK_MATH_PATTERN = /\\\[(.+?)\\\]/gs
const BRACKET_INLINE_MATH_PATTERN = /\\\((.+?)\\\)/gs

function normalizeMathDelimiters(value) {
    if (!value) return ""
    return value
        .replace(BRACKET_BLOCK_MATH_PATTERN, (_, inner) => `$$${inner.trim()}$$`)
        .replace(BRACKET_INLINE_MATH_PATTERN, (_, inner) => `$${inner.trim()}$`)
}

function remarkEvidencePlugin(options = {}) {
    const { resolveElementToEvidence } = options
    const shouldSkipType = (type) => type === "code" || type === "inlineCode" || type === "math" || type === "inlineMath"

    return function transformer(tree) {
        if (!tree || !Array.isArray(tree.children)) return

        const splitTextToNodes = (text) => {
            const nodes = []
            let lastIndex = 0
            let match

            EVIDENCE_REGEX.lastIndex = 0

            while ((match = EVIDENCE_REGEX.exec(text)) !== null) {
                const [raw, , tokenType, rawNo] = match
                const start = match.index

                if (start > lastIndex) {
                    nodes.push({ type: "text", value: text.slice(lastIndex, start) })
                }

                const numeric = Number(rawNo)
                const evidenceNo =
                    Number.isFinite(numeric) && tokenType?.toLowerCase() === "elem"
                        ? resolveElementToEvidence?.(numeric)
                        : Number.isFinite(numeric)
                          ? numeric
                          : null

                if (evidenceNo != null) {
                    nodes.push({
                        type: "evidenceReference",
                        value: evidenceNo,
                        data: {
                            hName: "evidence-reference",
                            hProperties: { "data-evidence": evidenceNo },
                        },
                    })
                } else {
                    nodes.push({ type: "text", value: raw })
                }

                lastIndex = start + raw.length
            }

            if (lastIndex < text.length) {
                nodes.push({ type: "text", value: text.slice(lastIndex) })
            }

            return nodes
        }

        const transformChildren = (children, parentType) => {
            if (!Array.isArray(children)) return children
            const mapped = children.flatMap((node) => {
                if (!node) return []
                if (node.type === "text" && !shouldSkipType(parentType)) {
                    return splitTextToNodes(node.value || "")
                }
                if (node.children && Array.isArray(node.children)) {
                    return {
                        ...node,
                        children: transformChildren(node.children, node.type),
                    }
                }
                return node
            })
            return mapped.filter(Boolean)
        }

        tree.children = transformChildren(tree.children, tree.type)
    }
}

function EvidenceCapsule({ evidenceNo, onSelectEvidence }) {
    if (!Number.isFinite(evidenceNo)) return null
    return (
        <button
            type="button"
            className="evidence-tag"
            aria-label={`Evidence #${evidenceNo}`}
            onClick={(event) => {
                event.preventDefault()
                event.stopPropagation()
                if (onSelectEvidence) onSelectEvidence(evidenceNo)
            }}
        >
            Evidence #{evidenceNo}
        </button>
    )
}

export default function MarkdownRenderer({ content, evidences, onSelectEvidence, className = "" }) {
    const rootClassName = useMemo(
        () => ["markdown-body", className].filter(Boolean).join(" "),
        [className],
    )

    const normalizedContent = useMemo(
        () => normalizeMathDelimiters(content || ""),
        [content],
    )
    const evidenceNoByElement = useMemo(() => {
        const mapping = new Map()
        ;(evidences ?? []).forEach((ev) => {
            if (ev.element_id == null || ev.evidence_no == null) return
            const elementId = Number(ev.element_id)
            const evidenceNo = Number(ev.evidence_no)
            if (Number.isFinite(elementId) && Number.isFinite(evidenceNo)) {
                mapping.set(elementId, evidenceNo)
            }
        })
        return mapping
    }, [evidences])

    const resolveElementToEvidence = useCallback(
        (elementId) => {
            const numeric = Number(elementId)
            if (!Number.isFinite(numeric)) return null
            return evidenceNoByElement.get(numeric) ?? null
        },
        [evidenceNoByElement],
    )

    const remarkPlugins = useMemo(
        // Parse math first, then inject evidence references so math nodes stay intact.
        () => [remarkGfm, remarkMath, remarkBreaks, [remarkEvidencePlugin, { resolveElementToEvidence }]],
        [resolveElementToEvidence],
    )

    const rehypePlugins = useMemo(() => [rehypeKatex], [])

    const components = useMemo(
        () => ({
            p: ({ children }) => <p className="markdown-paragraph">{children}</p>,
            h1: ({ children }) => <h1 className="markdown-heading">{children}</h1>,
            h2: ({ children }) => <h2 className="markdown-heading">{children}</h2>,
            h3: ({ children }) => <h3 className="markdown-heading">{children}</h3>,
            h4: ({ children }) => <h4 className="markdown-heading">{children}</h4>,
            ul: ({ children }) => <ul className="markdown-list">{children}</ul>,
            ol: ({ children }) => <ol className="markdown-list ordered">{children}</ol>,
            li: ({ children }) => <li className="markdown-list__item">{children}</li>,
            blockquote: ({ children }) => <blockquote className="markdown-quote">{children}</blockquote>,
            code: ({ inline, className: codeClassName, children, ...rest }) => {
                const language = codeClassName ? codeClassName.replace("language-", "") : ""
                if (inline) {
                    return (
                        <code className="markdown-code-inline" {...rest}>
                            {children}
                        </code>
                    )
                }
                return (
                    <pre className="markdown-code-block" data-language={language || undefined}>
                        <code className={language ? `language-${language}` : undefined} {...rest}>
                            {children}
                        </code>
                    </pre>
                )
            },
            a: ({ children, href, ...rest }) => (
                <a className="markdown-link" href={href} target="_blank" rel="noreferrer" {...rest}>
                    {children}
                </a>
            ),
            table: ({ children }) => (
                <div className="markdown-table-wrapper">
                    <table className="markdown-table">{children}</table>
                </div>
            ),
            th: ({ children }) => <th className="markdown-table__cell head">{children}</th>,
            td: ({ children }) => <td className="markdown-table__cell">{children}</td>,
            "evidence-reference": ({ node }) => {
                const evidenceNo =
                    Number(
                        node?.data?.hProperties?.["data-evidence"] ??
                            node?.properties?.["data-evidence"] ??
                            node?.value,
                    ) || null
                return <EvidenceCapsule evidenceNo={evidenceNo} onSelectEvidence={onSelectEvidence} />
            },
        }),
        [onSelectEvidence],
    )

    if (!content) {
        return <p className="caption muted">暂无回答</p>
    }

    try {
        return (
            <div className={rootClassName}>
                <ReactMarkdown
                    skipHtml
                    remarkPlugins={remarkPlugins}
                    rehypePlugins={rehypePlugins}
                    components={components}
                >
                    {normalizedContent}
                </ReactMarkdown>
            </div>
        )
    } catch (error) {
        console.warn("Failed to render markdown content", error)
        return (
            <pre className={`markdown-fallback ${className}`}>
                {content}
            </pre>
        )
    }
}
