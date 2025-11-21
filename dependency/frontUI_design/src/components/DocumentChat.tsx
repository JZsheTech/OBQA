import React, { useState, useRef } from 'react';
import { Send, FileText, MessageSquare, Database, ArrowLeft } from 'lucide-react';
import { Button, IconButton } from './ui/Button';
import { Card } from './ui/Card';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  evidences?: { id: string; label: string; page: number }[];
}

interface Chat {
  id: string;
  name: string;
}

interface DocumentChatProps {
  collectionId: string;
  collectionName: string;
  documentId: string;
  documentTitle: string;
  chatId: string;
  chatName: string;
  onNavigate: (path: string) => void;
}

export function DocumentChat({ 
  collectionId,
  collectionName,
  documentId,
  documentTitle,
  chatId,
  chatName,
  onNavigate 
}: DocumentChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'user',
      content: '什么是自注意力机制？'
    },
    {
      id: '2',
      role: 'assistant',
      content: '自注意力机制（Self-Attention）是Transformer的核心组件。它允许模型在处理一个序列时，计算序列中每个位置与其他所有位置之间的关系。通过查询（Query）、键（Key）和值（Value）三个向量的计算，模型可以确定应该关注输入的哪些部分。',
      evidences: [
        { id: 'e1', label: 'Evidence#1', page: 3 },
        { id: 'e2', label: 'Evidence#2', page: 4 }
      ]
    }
  ]);
  
  const [inputMessage, setInputMessage] = useState('');
  const [currentPage, setCurrentPage] = useState(1);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [leftWidth, setLeftWidth] = useState(45);
  const [isDragging, setIsDragging] = useState(false);
  
  const containerRef = useRef<HTMLDivElement>(null);
  
  const chats: Chat[] = [
    { id: '1', name: 'Attention机制解析' },
    { id: '2', name: '模型架构讨论' }
  ];
  
  const handleSendMessage = () => {
    if (inputMessage.trim()) {
      const newMessage: Message = {
        id: Date.now().toString(),
        role: 'user',
        content: inputMessage
      };
      setMessages([...messages, newMessage]);
      setInputMessage('');
      
      setTimeout(() => {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: '这是一个基于文档的模拟回答，展示了如何从单个PDF中检索证据并生成回答。',
          evidences: [{ id: 'e3', label: 'Evidence#1', page: 6 }]
        };
        setMessages(prev => [...prev, assistantMessage]);
      }, 1000);
    }
  };
  
  const handleEvidenceClick = (page: number) => {
    setCurrentPage(page);
  };
  
  const handleMouseDown = (e: React.MouseEvent) => {
    setIsDragging(true);
    e.preventDefault();
  };
  
  const handleMouseMove = (e: MouseEvent) => {
    if (!isDragging || !containerRef.current) return;
    
    const container = containerRef.current;
    const containerRect = container.getBoundingClientRect();
    const newLeftWidth = ((e.clientX - containerRect.left) / containerRect.width) * 100;
    
    if (newLeftWidth >= 30 && newLeftWidth <= 70) {
      setLeftWidth(newLeftWidth);
    }
  };
  
  const handleMouseUp = () => {
    setIsDragging(false);
  };
  
  React.useEffect(() => {
    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging]);
  
  return (
    <div className="min-h-screen flex flex-col bg-[var(--color-background)]">
      {/* Top App Bar */}
      <header className="bg-[var(--color-surface)] border-b border-[var(--color-border)] px-8 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-[var(--color-primary)] to-blue-600 rounded-lg flex items-center justify-center">
              <Database className="w-6 h-6 text-white" />
            </div>
            <h2 className="text-[var(--color-text-primary)]">EvidenceQA</h2>
          </div>
          <div className="w-10 h-10 bg-gradient-to-br from-slate-600 to-slate-700 rounded-full flex items-center justify-center text-white">
            <span>U</span>
          </div>
        </div>
      </header>
      
      {/* Tab Bar */}
      <div className="bg-[var(--color-surface)] border-b border-[var(--color-border)] px-8">
        <div className="flex gap-1">
          <button
            onClick={() => onNavigate('/')}
            className="px-6 py-3 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
          >
            知识库主页
          </button>
          <button
            onClick={() => onNavigate('/chat-history')}
            className="px-6 py-3 text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)] transition-colors"
          >
            Chat 历史
          </button>
        </div>
      </div>
      
      {/* Breadcrumb & Actions */}
      <div className="bg-[var(--color-surface)] px-8 py-3 border-b border-[var(--color-border)]">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <IconButton onClick={() => onNavigate(`/collection/${collectionId}/document/${documentId}`)}>
              <ArrowLeft className="w-5 h-5" />
            </IconButton>
            <button 
              onClick={() => onNavigate(`/collection/${collectionId}`)}
              className="text-[var(--color-primary)] hover:underline"
            >
              {collectionName}
            </button>
            <span className="text-[var(--color-text-tertiary)]">›</span>
            <button 
              onClick={() => onNavigate(`/collection/${collectionId}/document/${documentId}`)}
              className="text-[var(--color-primary)] hover:underline"
            >
              {documentTitle}
            </button>
            <span className="text-[var(--color-text-tertiary)]">›</span>
            <span className="text-[var(--color-text-secondary)]">{chatName || 'Chat'}</span>
          </div>
          <Button 
            variant="secondary" 
            size="sm"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            <MessageSquare className="w-4 h-4" />
            聊天历史
          </Button>
        </div>
      </div>
      
      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden relative" ref={containerRef}>
        {/* Left Panel - Chat */}
        <div 
          className="flex flex-col border-r border-[var(--color-border)] bg-[var(--color-surface)]"
          style={{ width: `${leftWidth}%` }}
        >
          <div className="p-6 border-b border-[var(--color-border)]">
            <h3>针对 Document 的问答</h3>
            <p className="text-sm text-[var(--color-text-secondary)] mt-1">
              {documentTitle}
            </p>
          </div>
          
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.map(message => (
              <div key={message.id} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div className={`max-w-[85%] ${message.role === 'user' ? 'bg-[var(--color-primary)] text-white' : 'bg-[var(--color-background)]'} rounded-2xl px-4 py-3`}>
                  <p className="text-sm leading-relaxed">{message.content}</p>
                  {message.evidences && (
                    <div className="flex flex-wrap gap-2 mt-3">
                      {message.evidences.map(evidence => (
                        <button
                          key={evidence.id}
                          onClick={() => handleEvidenceClick(evidence.page)}
                          className="px-2.5 py-1 bg-[var(--color-evidence-highlight)] text-[var(--color-text-primary)] rounded-md text-xs hover:bg-yellow-200 transition-colors"
                        >
                          {evidence.label}
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
          
          <div className="p-6 border-t border-[var(--color-border)]">
            <div className="flex gap-2">
              <textarea
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && (e.preventDefault(), handleSendMessage())}
                placeholder="输入你的问题... (Shift + Enter 换行)"
                rows={3}
                className="flex-1 px-4 py-2.5 bg-[var(--color-background)] border border-[var(--color-border)] rounded-lg outline-none focus:border-[var(--color-primary)] transition-colors resize-none"
              />
              <Button onClick={handleSendMessage} className="self-end">
                <Send className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </div>
        
        {/* Resize Handle */}
        <div
          onMouseDown={handleMouseDown}
          className="w-1 bg-[var(--color-border)] hover:bg-[var(--color-primary)] cursor-col-resize transition-colors relative group"
        >
          <div className="absolute inset-y-0 -left-1 -right-1" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-1 h-12 bg-[var(--color-text-tertiary)] rounded-full opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
        
        {/* Right Panel - PDF Viewer */}
        <div className="flex-1 flex flex-col bg-[var(--color-background)] relative">
          <div className="p-4 border-b border-[var(--color-border)] bg-[var(--color-surface)]">
            <h4 className="text-center">{documentTitle || 'Attention Is All You Need'}</h4>
          </div>
          
          <div className="flex-1 overflow-auto p-8">
            <Card className="max-w-3xl mx-auto aspect-[8.5/11] bg-white shadow-lg relative">
              <div className="absolute inset-0 flex items-center justify-center text-[var(--color-text-tertiary)]">
                <div className="text-center">
                  <FileText className="w-16 h-16 mx-auto mb-4 opacity-30" />
                  <p>PDF 预览区域</p>
                  <p className="text-sm mt-2">页码: {currentPage}</p>
                </div>
              </div>
              <div className="absolute top-[40%] left-[10%] right-[10%] h-[12%] bg-[var(--color-evidence-highlight)] opacity-40 rounded" />
            </Card>
          </div>
          
          {/* Overlay Sidebar - Chat History */}
          {sidebarOpen && (
            <>
              <div 
                className="absolute inset-0 bg-black/10 backdrop-blur-sm z-10"
                onClick={() => setSidebarOpen(false)}
              />
              <div className="absolute right-0 top-0 bottom-0 w-80 bg-[var(--color-surface)] border-l border-[var(--color-border)] shadow-xl z-20 flex flex-col">
                <div className="p-4 border-b border-[var(--color-border)] flex items-center justify-between">
                  <h4>Document 聊天历史</h4>
                  <IconButton size="sm" onClick={() => setSidebarOpen(false)}>
                    <ArrowLeft className="w-4 h-4" />
                  </IconButton>
                </div>
                
                <div className="flex-1 overflow-y-auto p-4 space-y-2">
                  {chats.map(chat => (
                    <Card
                      key={chat.id}
                      hover
                      onClick={() => onNavigate(`/collection/${collectionId}/document/${documentId}/chat/${chat.id}`)}
                      className={`p-3 ${chat.id === chatId ? 'bg-[var(--color-primary-light)] border-[var(--color-primary)]' : ''}`}
                    >
                      <div className="flex items-center gap-2">
                        <MessageSquare className="w-4 h-4 text-[var(--color-primary)] flex-shrink-0" />
                        <p className="text-sm truncate">{chat.name}</p>
                      </div>
                    </Card>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}