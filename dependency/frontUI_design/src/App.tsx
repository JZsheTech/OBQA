import React, { useState } from 'react';
import { Layout } from './components/Layout';
import { CollectionsHome } from './components/CollectionsHome';
import { CollectionDetail } from './components/CollectionDetail';
import { DocumentDetail } from './components/DocumentDetail';
import { CollectionChat } from './components/CollectionChat';
import { DocumentChat } from './components/DocumentChat';
import { ChatHistory } from './components/ChatHistory';

type Route = {
  type: 'home' | 'collection' | 'document' | 'collection-chat' | 'document-chat' | 'chat-history';
  collectionId?: string;
  collectionName?: string;
  documentId?: string;
  documentTitle?: string;
  chatId?: string;
  chatName?: string;
};

export default function App() {
  const [currentRoute, setCurrentRoute] = useState<Route>({ type: 'home' });
  const [routeHistory, setRouteHistory] = useState<Route[]>([{ type: 'home' }]);
  
  // Mock data for collections and documents
  const collections = {
    '1': { name: 'Machine Learning Papers' },
    '2': { name: 'Natural Language Processing' },
    '3': { name: 'Computer Vision' }
  };
  
  const documents = {
    '1': { title: 'Attention Is All You Need' },
    '2': { title: 'BERT: Pre-training of Deep Bidirectional Transformers' },
    '3': { title: 'GPT-3: Language Models are Few-Shot Learners' }
  };
  
  const chats = {
    '1': { name: 'Transformer架构讨论' },
    '2': { name: '预训练模型对比' }
  };
  
  const navigate = (path: string) => {
    let newRoute: Route = { type: 'home' };
    
    // Parse path and update route
    if (path === '/') {
      newRoute = { type: 'home' };
    } else if (path === '/chat-history') {
      newRoute = { type: 'chat-history' };
    } else if (path.match(/^\/collection\/(\w+)\/document\/(\w+)\/chat\/(\w+)$/)) {
      const match = path.match(/^\/collection\/(\w+)\/document\/(\w+)\/chat\/(\w+)$/);
      const collectionId = match![1];
      const documentId = match![2];
      const chatId = match![3];
      newRoute = {
        type: 'document-chat',
        collectionId,
        collectionName: collections[collectionId as keyof typeof collections]?.name,
        documentId,
        documentTitle: documents[documentId as keyof typeof documents]?.title,
        chatId,
        chatName: chats[chatId as keyof typeof chats]?.name
      };
    } else if (path.match(/^\/collection\/(\w+)\/chat\/(\w+)$/)) {
      const match = path.match(/^\/collection\/(\w+)\/chat\/(\w+)$/);
      const collectionId = match![1];
      const chatId = match![2];
      newRoute = {
        type: 'collection-chat',
        collectionId,
        collectionName: collections[collectionId as keyof typeof collections]?.name,
        chatId,
        chatName: chats[chatId as keyof typeof chats]?.name
      };
    } else if (path.match(/^\/collection\/(\w+)\/document\/(\w+)$/)) {
      const match = path.match(/^\/collection\/(\w+)\/document\/(\w+)$/);
      const collectionId = match![1];
      const documentId = match![2];
      newRoute = {
        type: 'document',
        collectionId,
        collectionName: collections[collectionId as keyof typeof collections]?.name,
        documentId,
        documentTitle: documents[documentId as keyof typeof documents]?.title
      };
    } else if (path.match(/^\/collection\/(\w+)$/)) {
      const match = path.match(/^\/collection\/(\w+)$/);
      const collectionId = match![1];
      newRoute = {
        type: 'collection',
        collectionId,
        collectionName: collections[collectionId as keyof typeof collections]?.name
      };
    }
    
    setCurrentRoute(newRoute);
    setRouteHistory([...routeHistory, newRoute]);
  };
  
  const goBack = () => {
    if (routeHistory.length > 1) {
      const newHistory = routeHistory.slice(0, -1);
      setRouteHistory(newHistory);
      setCurrentRoute(newHistory[newHistory.length - 1]);
    }
  };
  
  // Get breadcrumbs based on current route
  const getBreadcrumbs = () => {
    switch (currentRoute.type) {
      case 'home':
        return [{ label: 'Home' }];
      case 'chat-history':
        return [{ label: 'Chat 历史' }];
      case 'collection':
        return [
          { label: 'Home', href: '/' },
          { label: currentRoute.collectionName || 'Collection' }
        ];
      case 'document':
        return [
          { label: 'Home', href: '/' },
          { label: currentRoute.collectionName || 'Collection', href: `/collection/${currentRoute.collectionId}` },
          { label: currentRoute.documentTitle || 'Document' }
        ];
      case 'collection-chat':
        return [
          { label: 'Home', href: '/' },
          { label: currentRoute.collectionName || 'Collection', href: `/collection/${currentRoute.collectionId}` },
          { label: currentRoute.chatName || 'Chat' }
        ];
      case 'document-chat':
        return [
          { label: 'Home', href: '/' },
          { label: currentRoute.collectionName || 'Collection', href: `/collection/${currentRoute.collectionId}` },
          { label: currentRoute.documentTitle || 'Document', href: `/collection/${currentRoute.collectionId}/document/${currentRoute.documentId}` },
          { label: currentRoute.chatName || 'Chat' }
        ];
      default:
        return [{ label: 'Home' }];
    }
  };
  
  // Get active tab
  const getActiveTab = () => {
    return currentRoute.type === 'chat-history' ? 'history' : 'collections';
  };
  
  // Check if we should show back button
  const shouldShowBackButton = () => {
    return routeHistory.length > 1;
  };
  
  // Render current page based on route
  const renderPage = () => {
    switch (currentRoute.type) {
      case 'home':
        return <CollectionsHome onNavigate={navigate} />;
      case 'collection':
        return (
          <CollectionDetail
            collectionId={currentRoute.collectionId!}
            collectionName={currentRoute.collectionName!}
            onNavigate={navigate}
          />
        );
      case 'document':
        return (
          <DocumentDetail
            collectionId={currentRoute.collectionId!}
            collectionName={currentRoute.collectionName!}
            documentId={currentRoute.documentId!}
            documentTitle={currentRoute.documentTitle!}
            onNavigate={navigate}
          />
        );
      case 'collection-chat':
        return (
          <CollectionChat
            collectionId={currentRoute.collectionId!}
            collectionName={currentRoute.collectionName!}
            chatId={currentRoute.chatId!}
            chatName={currentRoute.chatName!}
            onNavigate={navigate}
          />
        );
      case 'document-chat':
        return (
          <DocumentChat
            collectionId={currentRoute.collectionId!}
            collectionName={currentRoute.collectionName!}
            documentId={currentRoute.documentId!}
            documentTitle={currentRoute.documentTitle!}
            chatId={currentRoute.chatId!}
            chatName={currentRoute.chatName!}
            onNavigate={navigate}
          />
        );
      case 'chat-history':
        return <ChatHistory onNavigate={navigate} />;
      default:
        return <CollectionsHome onNavigate={navigate} />;
    }
  };
  
  // For chat pages, render without Layout wrapper (they have their own navigation)
  if (currentRoute.type === 'collection-chat' || currentRoute.type === 'document-chat') {
    return (
      <div className="min-h-screen bg-[var(--color-background)]">
        {renderPage()}
      </div>
    );
  }
  
  return (
    <Layout
      activeTab={getActiveTab()}
      breadcrumbs={getBreadcrumbs()}
      onNavigate={navigate}
      showBackButton={shouldShowBackButton()}
      onBack={goBack}
    >
      {renderPage()}
    </Layout>
  );
}
