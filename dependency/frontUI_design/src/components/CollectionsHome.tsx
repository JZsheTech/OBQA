import React, { useState } from 'react';
import { Plus, Calendar, Search as SearchIcon, Database } from 'lucide-react';
import { Button, IconButton } from './ui/Button';
import { Card } from './ui/Card';
import { Badge } from './ui/Badge';
import { Modal } from './ui/Modal';
import { SearchBar } from './ui/SearchBar';

interface Collection {
  id: string;
  name: string;
  description: string;
  created_at: string;
}

interface CollectionsHomeProps {
  onNavigate: (path: string) => void;
}

export function CollectionsHome({ onNavigate }: CollectionsHomeProps) {
  const [collections, setCollections] = useState<Collection[]>([
    {
      id: '1',
      name: 'Machine Learning Papers',
      description: '关于深度学习和强化学习的最新研究论文集合，包含NIPS、ICML、ICLR等顶级会议的论文',
      created_at: '2024-11-15 14:30:00'
    },
    {
      id: '2',
      name: 'Natural Language Processing',
      description: 'NLP领域的重要论文，涵盖Transformer、BERT、GPT等模型的研究',
      created_at: '2024-11-10 09:15:00'
    },
    {
      id: '3',
      name: 'Computer Vision',
      description: '计算机视觉相关论文，包括图像分类、目标检测、图像分割等主题',
      created_at: '2024-11-05 16:45:00'
    }
  ]);
  
  const [searchQuery, setSearchQuery] = useState('');
  const [searchType, setSearchType] = useState('name');
  const [isSearchActive, setIsSearchActive] = useState(false);
  const [showNewCollectionModal, setShowNewCollectionModal] = useState(false);
  const [newCollectionName, setNewCollectionName] = useState('');
  const [newCollectionDescription, setNewCollectionDescription] = useState('');
  
  const searchOptions = [
    { value: 'name', label: '按 name 搜索' },
    { value: 'description', label: '按 description 搜索' }
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
  
  const handleCreateCollection = () => {
    if (newCollectionName.trim()) {
      const newCollection: Collection = {
        id: Date.now().toString(),
        name: newCollectionName,
        description: newCollectionDescription,
        created_at: new Date().toLocaleString('zh-CN')
      };
      setCollections([newCollection, ...collections]);
      setShowNewCollectionModal(false);
      setNewCollectionName('');
      setNewCollectionDescription('');
    }
  };
  
  const filteredCollections = isSearchActive
    ? collections.filter(col => {
        const searchLower = searchQuery.toLowerCase();
        if (searchType === 'name') {
          return col.name.toLowerCase().includes(searchLower);
        } else {
          return col.description.toLowerCase().includes(searchLower);
        }
      })
    : collections;
  
  return (
    <div className="max-w-7xl mx-auto px-8 py-8">
      {/* Page Title */}
      <div className="mb-6">
        <div className="flex items-center gap-3 mb-2">
          <div className="w-12 h-12 bg-gradient-to-br from-[var(--color-primary)] to-blue-600 rounded-xl flex items-center justify-center">
            <Database className="w-6 h-6 text-white" />
          </div>
          <div className="flex-1">
            <h1 className="mb-1">知识库主页</h1>
            <p className="text-sm text-[var(--color-text-tertiary)]">
              浏览和管理您的 Collection 集合
            </p>
          </div>
          <Button onClick={() => setShowNewCollectionModal(true)}>
            <Plus className="w-5 h-5" />
            新建 Collection
          </Button>
        </div>
      </div>
      
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <h2>我的 Collections</h2>
      </div>
      
      {/* Search Bar */}
      <div className="mb-6">
        <SearchBar
          placeholder="按 name 或 description 搜索 Collection"
          value={searchQuery}
          onChange={setSearchQuery}
          onSearch={handleSearch}
          onReset={handleReset}
          searchType={searchType}
          searchOptions={searchOptions}
          onSearchTypeChange={setSearchType}
          showReset={isSearchActive}
        />
      </div>
      
      {/* Search Result Badge */}
      {isSearchActive && (
        <div className="mb-4">
          <Badge variant="primary">
            <SearchIcon className="w-3 h-3" />
            搜索结果 ({filteredCollections.length})
          </Badge>
        </div>
      )}
      
      {/* Collections List */}
      <div className="grid gap-4">
        {filteredCollections.map(collection => (
          <Card 
            key={collection.id} 
            hover
            onClick={() => onNavigate(`/collection/${collection.id}`)}
            className={isSearchActive ? 'bg-[var(--color-highlight)]' : ''}
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h3 className="mb-2">{collection.name}</h3>
                <p className="text-[var(--color-text-secondary)] mb-3 line-clamp-2">
                  {collection.description}
                </p>
                <div className="flex items-center gap-2 text-sm text-[var(--color-text-tertiary)]">
                  <Calendar className="w-4 h-4" />
                  <span>创建时间：{collection.created_at}</span>
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>
      
      {/* Empty State */}
      {filteredCollections.length === 0 && (
        <div className="text-center py-16">
          <div className="text-[var(--color-text-tertiary)] mb-4">
            <SearchIcon className="w-12 h-12 mx-auto mb-3 opacity-50" />
            <p>未找到匹配的 Collection</p>
          </div>
        </div>
      )}
      
      {/* New Collection Modal */}
      <Modal
        isOpen={showNewCollectionModal}
        onClose={() => setShowNewCollectionModal(false)}
        title="新建 Collection"
      >
        <div className="space-y-4">
          <div>
            <label className="block text-sm mb-2 text-[var(--color-text-secondary)]">
              Collection Name *
            </label>
            <input
              type="text"
              value={newCollectionName}
              onChange={(e) => setNewCollectionName(e.target.value)}
              placeholder="输入 Collection 名称"
              className="w-full px-4 py-2.5 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg outline-none focus:border-[var(--color-primary)] transition-colors"
            />
          </div>
          
          <div>
            <label className="block text-sm mb-2 text-[var(--color-text-secondary)]">
              Description
            </label>
            <textarea
              value={newCollectionDescription}
              onChange={(e) => setNewCollectionDescription(e.target.value)}
              placeholder="输入描述信息（可选）"
              rows={4}
              className="w-full px-4 py-2.5 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg outline-none focus:border-[var(--color-primary)] transition-colors resize-none"
            />
          </div>
          
          <div className="flex gap-3 pt-4">
            <Button 
              onClick={handleCreateCollection}
              disabled={!newCollectionName.trim()}
              className="flex-1"
            >
              创建
            </Button>
            <Button 
              variant="secondary" 
              onClick={() => setShowNewCollectionModal(false)}
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