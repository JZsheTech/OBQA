import React, { useState } from 'react';
import { Plus, Upload, Calendar, FileText, MessageSquare, Search as SearchIcon, Copy } from 'lucide-react';
import { Button } from './ui/Button';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';
import { SearchBar } from './ui/SearchBar';
import { Modal } from './ui/Modal';

interface Document {
  id: string;
  title: string;
  file_name: string;
}

interface Chat {
  id: string;
  name: string;
  created_at: string;
}

interface RAGResult {
  id: string;
  text_content: string;
}

interface CollectionDetailProps {
  collectionId: string;
  collectionName: string;
  onNavigate: (path: string) => void;
}

export function CollectionDetail({ collectionId, collectionName, onNavigate }: CollectionDetailProps) {
  const [documents] = useState<Document[]>([
    { id: '1', title: 'Attention Is All You Need', file_name: 'attention_paper.pdf' },
    { id: '2', title: 'BERT: Pre-training of Deep Bidirectional Transformers', file_name: 'bert_paper.pdf' },
    { id: '3', title: 'GPT-3: Language Models are Few-Shot Learners', file_name: 'gpt3_paper.pdf' }
  ]);
  
  const [chats] = useState<Chat[]>([
    { id: '1', name: 'Transformer架构讨论', created_at: '2024-11-20 10:30' },
    { id: '2', name: '预训练模型对比', created_at: '2024-11-19 15:45' }
  ]);
  
  const [searchQuery, setSearchQuery] = useState('');
  const [searchType, setSearchType] = useState('title');
  const [isSearchActive, setIsSearchActive] = useState(false);
  const [ragQuery, setRagQuery] = useState('');
  const [ragResults, setRagResults] = useState<RAGResult[]>([]);
  const [selectedSnippet, setSelectedSnippet] = useState<string | null>(null);
  const [showNewChatModal, setShowNewChatModal] = useState(false);
  const [newChatName, setNewChatName] = useState('');
  
  const collectionInfo = {
    name: collectionName || 'Machine Learning Papers',
    description: '关于深度学习和强化学习的最新研究论文集合，包含NIPS、ICML、ICLR等顶级会议的论文，涵盖了Transformer、BERT、GPT等重要模型的研究成果。',
    created_at: '2024-11-15 14:30:00'
  };
  
  const searchOptions = [
    { value: 'title', label: '按 title 搜索' },
    { value: 'abstract', label: '按 abstract 搜索' },
    { value: 'md_text', label: '按全文搜索' }
  ];
  
  const handleSearch = () => {
    if (searchQuery.trim()) {
      setIsSearchActive(true);
    }
  };
  
  const handleReset = () => {
    setSearchQuery('');
    setIsSearchActive(false);
  };
  
  const handleRAGSearch = () => {
    if (ragQuery.trim()) {
      // Mock RAG results
      setRagResults([
        { id: '1', text_content: 'The Transformer architecture uses self-attention mechanisms to process sequential data. This allows the model to weigh the importance of different parts of the input...' },
        { id: '2', text_content: 'BERT introduces bidirectional training of Transformer models, which enables better understanding of context by looking at both left and right context in all layers...' },
        { id: '3', text_content: 'GPT-3 demonstrates that language models can perform few-shot learning by using only a few examples in the prompt, without any gradient updates or fine-tuning...' }
      ]);
    }
  };
  
  const filteredDocuments = isSearchActive
    ? documents.filter(doc => doc.title.toLowerCase().includes(searchQuery.toLowerCase()))
    : documents;
  
  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };
  
  const handleCreateChat = () => {
    if (newChatName.trim()) {
      // Mock: In real app, create a new chat and navigate to it
      const newChatId = Date.now().toString();
      setShowNewChatModal(false);
      setNewChatName('');
      onNavigate(`/collection/${collectionId}/chat/${newChatId}`);
    }
  };
  
  return (
    <div className="max-w-7xl mx-auto px-8 py-8">
      {/* Page Title */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-blue-600 rounded-xl flex items-center justify-center">
            <FileText className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="mb-1">Collection 管理</h1>
            <p className="text-sm text-[var(--color-text-tertiary)]">
              管理 Collection 中的文档和聊天记录
            </p>
          </div>
        </div>
      </div>
      
      {/* Collection Info */}
      <Card className="mb-8">
        <h1 className="mb-3">{collectionInfo.name}</h1>
        <p className="text-[var(--color-text-secondary)] mb-4">
          {collectionInfo.description}
        </p>
        <div className="flex items-center gap-2 text-sm text-[var(--color-text-tertiary)]">
          <Calendar className="w-4 h-4" />
          <span>创建时间：{collectionInfo.created_at}</span>
        </div>
      </Card>
      
      {/* Two Column Layout */}
      <div className="grid grid-cols-2 gap-8">
        {/* Left Column - Documents */}
        <div className="space-y-6">
          <div className="flex items-center justify-between">
            <h2>文档列表</h2>
            <Button size="sm">
              <Plus className="w-4 h-4" />
              上传文档
            </Button>
          </div>
          
          {/* Document Search */}
          <SearchBar
            placeholder="搜索文档..."
            value={searchQuery}
            onChange={setSearchQuery}
            onSearch={handleSearch}
            onReset={handleReset}
            searchType={searchType}
            searchOptions={searchOptions}
            onSearchTypeChange={setSearchType}
            showReset={isSearchActive}
          />
          
          {isSearchActive && (
            <Badge variant="primary">
              <SearchIcon className="w-3 h-3" />
              搜索结果 ({filteredDocuments.length})
            </Badge>
          )}
          
          {/* Document List */}
          <div className="space-y-3">
            {filteredDocuments.map(doc => (
              <Card 
                key={doc.id} 
                hover
                onClick={() => onNavigate(`/collection/${collectionId}/document/${doc.id}`)}
                className={`${isSearchActive ? 'bg-[var(--color-highlight)]' : ''} p-4`}
              >
                <div className="flex items-start gap-3">
                  <FileText className="w-5 h-5 text-[var(--color-primary)] flex-shrink-0 mt-1" />
                  <div className="flex-1 min-w-0">
                    <h4 className="mb-1 truncate">{doc.title}</h4>
                    <p className="text-sm text-[var(--color-text-tertiary)] truncate">
                      {doc.file_name}
                    </p>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
        
        {/* Right Column - Chat History & RAG */}
        <div className="space-y-6">
          {/* Chat History */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3>Collection 聊天历史</h3>
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
                  onClick={() => onNavigate(`/collection/${collectionId}/chat/${chat.id}`)}
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
          
          {/* Simple RAG Search */}
          <div>
            <h3 className="mb-4">简单 Collection-RAG 搜索</h3>
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