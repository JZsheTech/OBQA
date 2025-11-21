import React, { useState } from 'react';
import { MessageSquare, Calendar, Filter, History } from 'lucide-react';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';

interface ChatHistoryItem {
  id: string;
  type: 'collection' | 'document';
  collection_name: string;
  document_title?: string;
  chat_name: string;
  created_at: string;
  collection_id: string;
  document_id?: string;
}

interface ChatHistoryProps {
  onNavigate: (path: string) => void;
}

export function ChatHistory({ onNavigate }: ChatHistoryProps) {
  const [filterType, setFilterType] = useState<'all' | 'collection' | 'document'>('all');
  
  const chatHistory: ChatHistoryItem[] = [
    {
      id: '1',
      type: 'collection',
      collection_name: 'Machine Learning Papers',
      chat_name: 'Transformer架构讨论',
      created_at: '2024-11-20 10:30:00',
      collection_id: '1'
    },
    {
      id: '2',
      type: 'document',
      collection_name: 'Machine Learning Papers',
      document_title: 'Attention Is All You Need',
      chat_name: 'Attention机制解析',
      created_at: '2024-11-20 09:15:00',
      collection_id: '1',
      document_id: '1'
    },
    {
      id: '3',
      type: 'collection',
      collection_name: 'Natural Language Processing',
      chat_name: '预训练模型对比',
      created_at: '2024-11-19 15:45:00',
      collection_id: '2'
    },
    {
      id: '4',
      type: 'document',
      collection_name: 'Machine Learning Papers',
      document_title: 'BERT: Pre-training of Deep Bidirectional Transformers',
      chat_name: 'BERT模型分析',
      created_at: '2024-11-19 11:20:00',
      collection_id: '1',
      document_id: '2'
    },
    {
      id: '5',
      type: 'document',
      collection_name: 'Computer Vision',
      document_title: 'ResNet: Deep Residual Learning',
      chat_name: '残差网络原理',
      created_at: '2024-11-18 14:00:00',
      collection_id: '3',
      document_id: '5'
    }
  ];
  
  const filteredHistory = filterType === 'all' 
    ? chatHistory 
    : chatHistory.filter(item => item.type === filterType);
  
  const collectionChats = filteredHistory.filter(item => item.type === 'collection');
  const documentChats = filteredHistory.filter(item => item.type === 'document');
  
  const handleChatClick = (item: ChatHistoryItem) => {
    if (item.type === 'collection') {
      onNavigate(`/collection/${item.collection_id}/chat/${item.id}`);
    } else {
      onNavigate(`/collection/${item.collection_id}/document/${item.document_id}/chat/${item.id}`);
    }
  };
  
  return (
    <div className="max-w-7xl mx-auto px-8 py-8">
      {/* Page Title */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-12 h-12 bg-gradient-to-br from-green-500 to-green-600 rounded-xl flex items-center justify-center">
            <History className="w-6 h-6 text-white" />
          </div>
          <div className="flex-1">
            <h1 className="mb-1">Chat 历史</h1>
            <p className="text-sm text-[var(--color-text-tertiary)]">
              查看和管理所有 Collection 和 Document 级别的聊天记录
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Filter className="w-5 h-5 text-[var(--color-text-tertiary)]" />
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value as any)}
              className="px-4 py-2 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg outline-none focus:border-[var(--color-primary)] transition-colors"
            >
              <option value="all">全部</option>
              <option value="collection">Collection Chat</option>
              <option value="document">Document Chat</option>
            </select>
          </div>
        </div>
      </div>
      
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <h1>Chat 历史</h1>
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-[var(--color-text-tertiary)]" />
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value as any)}
            className="px-4 py-2 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg outline-none focus:border-[var(--color-primary)] transition-colors"
          >
            <option value="all">全部</option>
            <option value="collection">Collection Chat</option>
            <option value="document">Document Chat</option>
          </select>
        </div>
      </div>
      
      {/* Collection Level Chats */}
      {(filterType === 'all' || filterType === 'collection') && collectionChats.length > 0 && (
        <div className="mb-12">
          <div className="flex items-center gap-3 mb-6">
            <h2>Collection 级别 Chat</h2>
            <Badge variant="default">{collectionChats.length}</Badge>
          </div>
          <div className="grid gap-4">
            {collectionChats.map(item => (
              <Card 
                key={item.id}
                hover
                onClick={() => handleChatClick(item)}
                className="p-5"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <MessageSquare className="w-5 h-5 text-[var(--color-primary)]" />
                      <h4>{item.collection_name}</h4>
                      <span className="text-[var(--color-text-tertiary)]">·</span>
                      <h4 className="text-[var(--color-primary)]">{item.chat_name}</h4>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-[var(--color-text-tertiary)]">
                      <Calendar className="w-4 h-4" />
                      <span>{item.created_at}</span>
                    </div>
                  </div>
                  <Badge variant="primary">Collection</Badge>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}
      
      {/* Document Level Chats */}
      {(filterType === 'all' || filterType === 'document') && documentChats.length > 0 && (
        <div>
          <div className="flex items-center gap-3 mb-6">
            <h2>Document 级别 Chat</h2>
            <Badge variant="default">{documentChats.length}</Badge>
          </div>
          <div className="grid gap-4">
            {documentChats.map(item => (
              <Card 
                key={item.id}
                hover
                onClick={() => handleChatClick(item)}
                className="p-5"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <MessageSquare className="w-5 h-5 text-[var(--color-primary)]" />
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-[var(--color-text-secondary)]">{item.collection_name}</span>
                        <span className="text-[var(--color-text-tertiary)]">›</span>
                        <h4>{item.document_title}</h4>
                        <span className="text-[var(--color-text-tertiary)]">·</span>
                        <h4 className="text-[var(--color-primary)]">{item.chat_name}</h4>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 text-sm text-[var(--color-text-tertiary)]">
                      <Calendar className="w-4 h-4" />
                      <span>{item.created_at}</span>
                    </div>
                  </div>
                  <Badge variant="success">Document</Badge>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}
      
      {/* Empty State */}
      {filteredHistory.length === 0 && (
        <div className="text-center py-16">
          <MessageSquare className="w-16 h-16 mx-auto mb-4 text-[var(--color-text-tertiary)] opacity-50" />
          <p className="text-[var(--color-text-tertiary)]">暂无聊天记录</p>
        </div>
      )}
    </div>
  );
}