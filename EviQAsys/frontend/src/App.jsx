import { BrowserRouter, Routes, Route } from "react-router-dom"
import Home from "./pages/Home"
import DocumentsPage from "./pages/DocumentsPage"
import "./App.css"

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/documents" element={<DocumentsPage />} />
            </Routes>
        </BrowserRouter>
    )
}

export default App
