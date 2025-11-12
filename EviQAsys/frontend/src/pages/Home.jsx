import React, { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { healthCheck } from "../api/client"

function Home() {
    const [status, setStatus] = useState("checking...")

    useEffect(() => {
        healthCheck()
            .then((data) => setStatus(data.ok ? "Backend OK ✅" : "Backend Not OK ❌"))
            .catch((err) => setStatus(`Error: ${err.message}`))
    }, [])

    return (
        <div
            style={{
                padding: "4rem 2rem",
                fontFamily: "Inter, system-ui, -apple-system, BlinkMacSystemFont, sans-serif",
                minHeight: "100vh",
                background: "#f8fafc",
                color: "#0f172a",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
            }}
        >
            <div
                style={{
                    background: "#fff",
                    borderRadius: "16px",
                    padding: "2.5rem",
                    boxShadow: "0 10px 25px rgba(15, 23, 42, 0.08)",
                    maxWidth: "640px",
                    width: "100%",
                }}
            >
                <h1 style={{ fontSize: "2.5rem", marginBottom: "0.5rem" }}>EviQAsys Console</h1>
                <p style={{ marginBottom: "1.5rem", color: "#475569" }}>
                    Monitor the backend health status and jump into the document ingestion tools.
                </p>

                <div
                    style={{
                        background: "#f1f5f9",
                        borderRadius: "12px",
                        padding: "1rem 1.25rem",
                        marginBottom: "2rem",
                        fontWeight: 600,
                    }}
                >
                    Health Check Result: {status}
                </div>

                <Link
                    to="/documents"
                    style={{
                        display: "inline-flex",
                        alignItems: "center",
                        gap: "0.4rem",
                        background: "#2563eb",
                        color: "#fff",
                        padding: "0.85rem 1.75rem",
                        borderRadius: "999px",
                        textDecoration: "none",
                        fontWeight: 600,
                        boxShadow: "0 10px 20px rgba(37, 99, 235, 0.25)",
                    }}
                >
                    Open Document Upload
                    <span aria-hidden="true">↗</span>
                </Link>
            </div>
        </div>
    )
}

export default Home
