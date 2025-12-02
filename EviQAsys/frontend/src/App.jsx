import { BrowserRouter, Routes, Route } from "react-router-dom"
import AppLayout from "./components/layout/AppLayout"
import ChatHistory from "./pages/ChatHistory"
import CollectionChat from "./pages/CollectionChat"
import CollectionDetail from "./pages/CollectionDetail"
import CollectionsHome from "./pages/CollectionsHome"
import DocumentChat from "./pages/DocumentChat"
import DocumentDetail from "./pages/DocumentDetail"
import ArxivSearch from "./pages/ArxivSearch"
import ArxivFavorites from "./pages/ArxivFavorites"
import NotFound from "./pages/NotFound"
import "./App.css"

function App() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<AppLayout />}>
                    <Route index element={<CollectionsHome />} />
                    <Route path="collections/:collectionId" element={<CollectionDetail />} />
                    <Route path="collections/:collectionId/documents/:documentId" element={<DocumentDetail />} />
                    <Route path="collections/:collectionId/chat/:chatId" element={<CollectionChat />} />
                    <Route path="documents/:documentId/chat/:chatId" element={<DocumentChat />} />
                    <Route path="chat-history" element={<ChatHistory />} />
                    <Route path="arxiv/search" element={<ArxivSearch />} />
                    <Route path="arxiv/favorites" element={<ArxivFavorites />} />
                    <Route path="*" element={<NotFound />} />
                </Route>
            </Routes>
        </BrowserRouter>
    )
}

export default App
