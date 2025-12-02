import { useCallback, useMemo } from "react"
import ReactMarkdown from "react-markdown"
import remarkBreaks from "remark-breaks"
import remarkGfm from "remark-gfm"
import remarkMath from "remark-math"
import rehypeKatex from "rehype-katex"
import "katex/dist/katex.min.css"

const EVIDENCE_PATTERN = /\b(Evidence|Elem)\s*#\s*(\d+)\b/i

function createEvidencePlugin({ resolveElementToEvidence }) {
    const tokenizeEvidence = (eat, value, silent) => {
        const match = EVIDENCE_PATTERN.exec(value)
        if (!match || match.index !== 0) return

        const [raw, tokenType, rawNo] = match
        if (silent) return true

        const numeric = Number(rawNo)
        if (!Number.isFinite(numeric)) {
            return eat(raw)({ type: "text", value: raw })
        }

        const evidenceNo =
            tokenType.toLowerCase() === "elem" && typeof resolveElementToEvidence === "function"
                ? resolveElementToEvidence(numeric)
                : numeric

        if (evidenceNo == null) {
            return eat(raw)({ type: "text", value: raw })
        }

        return eat(raw)({
            type: "evidenceReference",
            value: evidenceNo,
            data: {
                hName: "evidence-reference",
                hProperties: { "data-evidence": evidenceNo },
                hChildren: [{ type: "text", value: `Evidence #${evidenceNo}` }],
            },
        })
    }

    tokenizeEvidence.locator = (value, fromIndex) => {
        const cursor = typeof fromIndex === "number" ? fromIndex : 0
        const match = EVIDENCE_PATTERN.exec(value.slice(cursor))
        return match ? cursor + match.index : -1
    }

    return function attacher() {
        const Parser = this?.Parser
        if (!Parser?.prototype?.inlineTokenizers || !Parser.prototype.inlineMethods) return

        const tokenizers = Parser.prototype.inlineTokenizers
        const methods = Parser.prototype.inlineMethods

        tokenizers.evidenceReference = tokenizeEvidence
        if (!methods.includes("evidenceReference")) {
            const textIndex = methods.indexOf("text")
            if (textIndex === -1) {
                methods.push("evidenceReference")
            } else {
                methods.splice(textIndex, 0, "evidenceReference")
            }
        }
    }
}

function EvidenceCapsule({ node, children, onSelectEvidence, ...props }) {
    const rawValue =
        props["data-evidence"] ??
        node?.properties?.["data-evidence"] ??
        node?.data?.hProperties?.["data-evidence"] ??
        node?.value
    const evidenceNo = Number(rawValue)

    if (!Number.isFinite(evidenceNo)) {
        return <span {...props}>{children}</span>
    }

    return (
        <button
            type="button"
            className="evidence-tag"
            aria-label={`Evidence #${evidenceNo}`}
            onClick={() => {
                if (onSelectEvidence) {
                    onSelectEvidence(evidenceNo)
                }
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

    const remarkEvidencePlugin = useMemo(
        () => createEvidencePlugin({ resolveElementToEvidence }),
        [resolveElementToEvidence],
    )

    const remarkPlugins = useMemo(
        () => [remarkGfm, remarkMath, remarkBreaks, remarkEvidencePlugin],
        [remarkEvidencePlugin],
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
            "evidence-reference": (props) => <EvidenceCapsule {...props} onSelectEvidence={onSelectEvidence} />,
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
                    {content}
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
