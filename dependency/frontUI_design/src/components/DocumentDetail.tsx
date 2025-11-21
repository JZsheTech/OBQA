import React, { useState } from 'react';
import { FileText, Hash, Layers, MessageSquare, Copy, Plus, BookOpen } from 'lucide-react';
import { Button } from './ui/Button';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';
import { Modal } from './ui/Modal';

interface Chat {
  id: string;
  name: string;
  created_at: string;
}

interface RAGResult {
  id: string;
  text_content: string;
}

interface DocumentDetailProps {
  collectionId: string;
  collectionName: string;
  documentId: string;
  documentTitle: string;
  onNavigate: (path: string) => void;
}

export function DocumentDetail({ 
  collectionId, 
  collectionName,
  documentId, 
  documentTitle,
  onNavigate 
}: DocumentDetailProps) {
  const [chats] = useState<Chat[]>([
    { id: '1', name: 'Attention机制解析', created_at: '2024-11-20 10:30' },
    { id: '2', name: '模型架构讨论', created_at: '2024-11-19 15:45' }
  ]);
  
  const [ragQuery, setRagQuery] = useState('');
  const [ragResults, setRagResults] = useState<RAGResult[]>([]);
  const [selectedSnippet, setSelectedSnippet] = useState<string | null>(null);
  const [showNewChatModal, setShowNewChatModal] = useState(false);
  const [newChatName, setNewChatName] = useState('');
  
  const documentInfo = {
    collection_name: collectionName || 'Machine Learning Papers',
    title: documentTitle || 'Attention Is All You Need',
    file_name: 'attention_paper.pdf',
    num_pages: 15,
    element_count: 234,
    abstract: 'The dominant sequence transduction models are based on complex recurrent or convolutional neural networks that include an encoder and a decoder. The best performing models also connect the encoder and decoder through an attention mechanism. We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely. Experiments on two machine translation tasks show these models to be superior in quality while being more parallelizable and requiring significantly less time to train.'
  };
  
  const handleRAGSearch = () => {
    if (ragQuery.trim()) {
      setRagResults([
        { id: '1', text_content: 'The Transformer uses scaled dot-product attention, which computes the attention function on a set of queries simultaneously, packed together into a matrix Q...' },
        { id: '2', text_content: 'Multi-head attention allows the model to jointly attend to information from different representation subspaces at different positions...' }
      ]);
    }
  };
  
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };
  
  const handleCreateChat = () => {
    if (newChatName.trim()) {
      const newChatId = Date.now().toString();
      setShowNewChatModal(false);
      setNewChatName('');
      onNavigate(`/collection/${collectionId}/document/${documentId}/chat/${newChatId}`);
    }
  };
  
  return (
    <div className="max-w-7xl mx-auto px-8 py-8">
      {/* Page Title */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-purple-600 rounded-xl flex items-center justify-center">
            <BookOpen className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="mb-1">Document 管理</h1>
            <p className="text-sm text-[var(--color-text-tertiary)]">
              查看文档详情、摘要和聊天记录
            </p>
          </div>
        </div>
      </div>
      
      {/* Document Info Card */}
      <Card className="mb-8">
        <div className="flex items-start justify-between mb-4">
          <div className="flex-1">
            <button
              onClick={() => onNavigate(`/collection/${collectionId}`)}
              className="text-sm text-[var(--color-primary)] hover:underline mb-2"
            >
              ← {documentInfo.collection_name}
            </button>
            <h1 className="mb-2">{documentInfo.title}</h1>
            <p className="text-[var(--color-text-secondary)] flex items-center gap-2">
              <FileText className="w-4 h-4" />
              {documentInfo.file_name}
            </p>
          </div>
        </div>
        
        <div className="flex gap-3">
          <Badge variant="default">
            <Hash className="w-3 h-3" />
            {documentInfo.num_pages} 页
          </Badge>
          <Badge variant="default">
            <Layers className="w-3 h-3" />
            {documentInfo.element_count} 元素
          </Badge>
        </div>
      </Card>
      
      {/* Two Column Layout */}
      <div className="grid grid-cols-2 gap-8">
        {/* Left Column - Abstract & RAG */}
        <div className="space-y-6">
          {/* Abstract */}
          <div>
            <h3 className="mb-4">摘要 (Abstract)</h3>
            <Card>
              <p className="text-[var(--color-text-secondary)] leading-relaxed">
                {documentInfo.abstract}
              </p>
            </Card>
          </div>
          
          {/* Simple RAG Search */}
          <div>
            <h3 className="mb-4">简单 Document-RAG 搜索</h3>
            <div className="space-y-3">
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="输入关键词或短句..."
                  value={ragQuery}
                  onChange={(e) => setRagQuery(e.target.value)}
                  className="flex-1 px-4 py-2.5 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg outline-none focus:border-[var(--color-primary)] transition-colors"
                />
                <Button onClick={handleRAGSearch}>检索</Button>
              </div>
              
              {ragResults.length > 0 && (
                <div className="space-y-2">
                  {ragResults.map(result => (
                    <Card 
                      key={result.id}
                      hover
                      onClick={() => setSelectedSnippet(result.text_content)}
                      className="p-4"
                    >
                      <div className="flex items-start justify-between gap-3">
                        <p className="text-sm text-[var(--color-text-secondary)] line-clamp-2">
                          {result.text_content}
                        </p>
                        <Badge variant="primary" className="flex-shrink-0">Evidence</Badge>
                      </div>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
        
        {/* Right Column - Chat History */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h3>Document 聊天历史</h3>
            <Button size="sm" onClick={() => setShowNewChatModal(true)}>
              <Plus className="w-4 h-4" />
              新建聊天
            </Button>
          </div>
          <div className="space-y-2">
            {chats.map(chat => (
              <Card 
                key={chat.id}
                hover
                onClick={() => onNavigate(`/collection/${collectionId}/document/${documentId}/chat/${chat.id}`)}
                className="p-4"
              >
                <div className="flex items-center gap-3">
                  <MessageSquare className="w-5 h-5 text-[var(--color-primary)]" />
                  <div className="flex-1">
                    <h4 className="text-sm mb-1">{chat.name}</h4>
                    <p className="text-xs text-[var(--color-text-tertiary)]">
                      {chat.created_at}
                    </p>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      </div>
      
      {/* Snippet Modal */}
      <Modal
        isOpen={!!selectedSnippet}
        onClose={() => setSelectedSnippet(null)}
        title="完整片段"
      >
        <div className="space-y-4">
          <p className="text-[var(--color-text-secondary)] leading-relaxed">
            {selectedSnippet}
          </p>
          <Button 
            variant="secondary" 
            onClick={() => copyToClipboard(selectedSnippet!)}
            className="w-full"
          >
            <Copy className="w-4 h-4" />
            复制文本
          </Button>
        </div>
      </Modal>
      
      {/* New Chat Modal */}
      <Modal
        isOpen={showNewChatModal}
        onClose={() => setShowNewChatModal(false)}
        title="新建聊天"
        size="sm"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm mb-2 text-[var(--color-text-secondary)]">
              聊天名称 *
            </label>
            <input
              type="text"
              value={newChatName}
              onChange={(e) => setNewChatName(e.target.value)}
              placeholder="输入聊天名称"
              className="w-full px-4 py-2.5 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg outline-none focus:border-[var(--color-primary)] transition-colors"
              autoFocus
            />
          </div>
          
          <div className="flex gap-3 pt-4">
            <Button 
              onClick={handleCreateChat}
              disabled={!newChatName.trim()}
              className="flex-1"
            >
              创建
            </Button>
            <Button 
              variant="secondary" 
              onClick={() => setShowNewChatModal(false)}
              className="flex-1"
            >
              取消
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
}