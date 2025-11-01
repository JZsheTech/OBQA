import React, { useEffect, useState } from "react"
import { healthCheck } from "../api/client"

function Home() {
    const [status, setStatus] = useState("checking...")

    useEffect(() => {
    healthCheck()
        .then((data) => setStatus(data.ok ? "Backend OK ✅" : "Backend Not OK ❌"))
        .catch((err) => setStatus(`Error: ${err.message}`))
    }, [])

    return (
    <div style={{ padding: "2rem", fontFamily: "sans-serif" }}>
        <h1>EviQAsys Frontend</h1>
        <p>Health Check Result: {status}</p>
    </div>
    )
}

export default Home