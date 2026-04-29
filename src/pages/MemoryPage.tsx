import React, { useState, useMemo, useRef } from 'react';
import { Calendar, Plus, Trash2, Download, Upload, Filter } from 'lucide-react';
import { useMemoryEntries } from '../hooks/useDashboardData';
import { CustomTooltip } from '../components/charts/CustomTooltip';
import { ChartSkeleton } from '../components/charts/ChartSkeleton';
import { ExportButton } from '../components/common/ExportButton';
import { ChartExportButton } from '../components/common/ChartExportButton';

const MEMORY_TYPES = [
  { value: 'injury', label: 'Injury', color: '#F87171' },
  { value: 'achievement', label: 'Achievement', color: '#4ADE80' },
  { value: 'pattern', label: 'Pattern', color: '#FB923C' },
  { value: 'milestone', label: 'Milestone', color: '#E8FF47' },
  { value: 'preference', label: 'Preference', color: '#60A5FA' },
  { value: 'health_alert', label: 'Health Alert', color: '#F472B6' },
];

const IMPORTANCE_LEVELS = [
  { value: 1, label: 'Low' },
  { value: 5, label: 'Medium' },
  { value: 8, label: 'High' },
  { value: 10, label: 'Critical' },
];

interface AddMemoryModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (memory: {
    type: string;
    content: string;
    date: string;
    importance: number;
    source: string;
  }) => void;
}

const AddMemoryModal: React.FC<AddMemoryModalProps> = ({ isOpen, onClose, onAdd }) => {
  const [type, setType] = useState('pattern');
  const [content, setContent] = useState('');
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [importance, setImportance] = useState(5);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onAdd({ type, content, date, importance, source: 'user' });
    setContent('');
    setType('pattern');
    setImportance(5);
    setDate(new Date().toISOString().split('T')[0]);
    onClose();
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-[var(--color-surface-container)] rounded-xl border border-[var(--color-outline-variant)]/20 w-full max-w-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <h3 className="text-xl font-display font-bold text-[var(--color-text)]">
            Add Memory Entry
          </h3>
          <button onClick={onClose} className="p-2 hover:bg-[var(--color-surface-variant)] rounded-lg">
            <span className="text-xl">×</span>
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[var(--color-text-muted)] mb-2">
              Type
            </label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="w-full bg-[var(--color-surface)] border border-[var(--color-outline-variant)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:border-[var(--color-primary)] focus:ring-1 focus:ring-[var(--color-primary)]"
            >
              {MEMORY_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-[var(--color-text-muted)] mb-2">
              Content
            </label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              className="w-full bg-[var(--color-surface)] border border-[var(--color-outline-variant)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:border-[var(--color-primary)] focus:ring-1 focus:ring-[var(--color-primary)] resize-none"
              rows={3}
              placeholder="Describe the memory..."
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-[var(--color-text-muted)] mb-2">
                Date
              </label>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="w-full bg-[var(--color-surface)] border border-[var(--color-outline-variant)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:border-[var(--color-primary)] focus:ring-1 focus:ring-[var(--color-primary)]"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-[var(--color-text-muted)] mb-2">
                Importance
              </label>
              <select
                value={importance}
                onChange={(e) => setImportance(Number(e.target.value))}
                className="w-full bg-[var(--color-surface)] border border-[var(--color-outline-variant)] rounded-lg px-3 py-2 text-sm text-[var(--color-text)] focus:border-[var(--color-primary)] focus:ring-1 focus:ring-[var(--color-primary)]"
              >
                {IMPORTANCE_LEVELS.map((level) => (
                  <option key={level.value} value={level.value}>
                    {level.label}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="flex gap-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 rounded-lg border border-[var(--color-outline-variant)] text-[var(--color-text-muted)] hover:bg-[var(--color-surface-variant)] transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex-1 px-4 py-2 rounded-lg bg-[var(--color-primary)] text-[var(--color-on-primary)] font-medium hover:brightness-110 transition-colors"
            >
              Add Memory
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

const generateMockMemories = () => {
  const types = MEMORY_TYPES;
  const memories = [];
  const now = new Date();
  
  for (let i = 0; i < 30; i++) {
    const date = new Date(now);
    date.setDate(date.getDate() - Math.floor(Math.random() * 90));
    const type = types[Math.floor(Math.random() * types.length)];
    const contents = {
      injury: ['Ankle sprain during sprint', 'Lower back tightness after deadlifts', 'Shoulder impingement from overhead press'],
      achievement: ['New PR on bench press: 55kg', 'Completed 30-day consistency streak', 'Hit 100kg squat milestone'],
      pattern: ['Better recovery on high protein days', 'Sleep quality correlates with workout performance', 'Consistent morning training yields best results'],
      milestone: ['6 months training completed', 'Lost 5kg body fat', 'Gained 2kg lean muscle'],
      preference: ['Prefer morning workouts', 'Higher volume on upper body days', 'Active recovery on Sundays'],
      health_alert: ['HRV dropped below baseline for 3 days', 'Resting HR elevated above normal range'],
    };
    
    memories.push({
      id: i + 1,
      type: type.value,
      content: contents[type.value][Math.floor(Math.random() * contents[type.value].length)],
      date: date.toISOString().split('T')[0],
      importance: Math.floor(Math.random() * 5) + 5,
      source: 'auto',
    });
  }
  
  return memories.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
};

export const MemoryPage = () => {
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [localMemories, setLocalMemories] = useState(generateMockMemories());
  const memoryRef = useRef<HTMLDivElement>(null);

  const { data: memoryData, isLoading } = useMemoryEntries(90);

  const toggleType = (type: string) => {
    setSelectedTypes(prev =>
      prev.includes(type)
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
  };

  const filteredMemories = useMemo(() => {
    if (selectedTypes.length === 0) return localMemories;
    return localMemories.filter(m => selectedTypes.includes(m.type));
  }, [localMemories, selectedTypes]);

  const groupedMemories = useMemo(() => {
    const grouped: Record<string, any[]> = {};
    filteredMemories.forEach(memory => {
      if (!grouped[memory.date]) {
        grouped[memory.date] = [];
      }
      grouped[memory.date].push(memory);
    });
    return grouped;
  }, [filteredMemories]);

  const handleAddMemory = (newMemory: any) => {
    setLocalMemories(prev => [
      { ...newMemory, id: Date.now() },
      ...prev,
    ].sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()));
  };

  const handleDeleteMemory = (id: number) => {
    setLocalMemories(prev => prev.filter(m => m.id !== id));
  };

  const exportMemories = () => {
    const data = localMemories.map(m => ({
      Date: m.date,
      Type: MEMORY_TYPES.find(t => t.value === m.type)?.label || m.type,
      Content: m.content,
      Importance: IMPORTANCE_LEVELS.find(l => l.value === m.importance)?.label || m.importance,
      Source: m.source,
    }));
    
    const csv = [
      Object.keys(data[0]).join(','),
      ...data.map(row => Object.values(row).join(',')),
    ].join('\n');
    
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = 'memories.csv';
    link.click();
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-display font-bold text-[var(--color-text)]">
          Memory Timeline
        </h1>
        <ChartSkeleton count={3} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-bold text-[var(--color-text)]">
            Memory Timeline
          </h1>
          <p className="text-sm text-[var(--color-text-muted)]">
            Track injuries, achievements, patterns, and milestones
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-[var(--color-surface-container)] border border-[var(--color-outline-variant)] hover:border-[var(--color-primary)]/30 transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span className="text-sm">Add Memory</span>
          </button>
          <ExportButton data={localMemories} filename="memories" format="csv" onExport={exportMemories} />
        </div>
      </div>

      {/* Filter Tags */}
      <div className="flex flex-wrap gap-2">
        {MEMORY_TYPES.map(type => (
          <button
            key={type.value}
            onClick={() => toggleType(type.value)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
              selectedTypes.includes(type.value)
                ? 'opacity-100'
                : 'opacity-40 hover:opacity-70'
            }`}
            style={{
              backgroundColor: selectedTypes.includes(type.value)
                ? `${type.color}33`
                : 'transparent',
              color: type.color,
              border: `1px solid ${type.color}44`,
            }}
          >
            <span
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: type.color }}
            />
            {type.label}
          </button>
        ))}
      </div>

      {/* Timeline */}
      <div ref={memoryRef} className="relative">
        {Object.entries(groupedMemories).map(([date, memories]) => (
          <div key={date} className="mb-8">
            <div className="sticky top-0 z-10 bg-[var(--color-background)]/80 backdrop-blur-sm py-2 mb-4">
              <h3 className="text-sm font-bold text-[var(--color-text-muted)] uppercase tracking-wider">
                {new Date(date).toLocaleDateString('en-US', { 
                  weekday: 'long', 
                  year: 'numeric', 
                  month: 'long', 
                  day: 'numeric' 
                })}
              </h3>
            </div>
            <div className="space-y-4">
              {memories.map(memory => {
                const typeInfo = MEMORY_TYPES.find(t => t.value === memory.type);
                const importanceInfo = IMPORTANCE_LEVELS.find(l => l.value === memory.importance);
                
                return (
                  <div
                    key={memory.id}
                    className="group relative bg-[var(--color-surface)] rounded-lg border border-[var(--color-outline-variant)]/20 p-4 pl-12 hover:border-[var(--color-primary)]/30 transition-colors"
                  >
                    <div
                      className="absolute left-4 top-1/2 -translate-y-1/2 w-3 h-3 rounded-full"
                      style={{ backgroundColor: typeInfo?.color }}
                    />
                    <div className="absolute left-4 top-0 bottom-0 w-px"
                      style={{ backgroundColor: typeInfo?.color + '20' }}
                    />
                    <button
                      onClick={() => handleDeleteMemory(memory.id)}
                      className="absolute top-2 right-2 p-1.5 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-[var(--color-danger)]/10 text-[var(--color-text-muted)] hover:text-[var(--color-danger)] transition-all"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-medium capitalize"
                            style={{ color: typeInfo?.color }}
                          >
                            {typeInfo?.label}
                          </span>
                          <span className="text-xs px-2 py-0.5 rounded bg-[var(--color-surface-variant)] text-[var(--color-text-muted)]">
                            {importanceInfo?.label}
                          </span>
                        </div>
                        <p className="text-sm text-[var(--color-text)]">
                          {memory.content}
                        </p>
                      </div>
                      <span className="text-xs text-[var(--color-text-muted)] ml-2 flex-shrink-0">
                        {memory.source === 'auto' ? 'Auto' : 'User'}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        ))}

        {filteredMemories.length === 0 && (
          <div className="text-center py-12">
            <p className="text-[var(--color-text-muted)]">
              {selectedTypes.length > 0 ? 'No memories match the selected filters' : 'No memories yet'}
            </p>
          </div>
        )}
      </div>

      <AddMemoryModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onAdd={handleAddMemory}
      />
    </div>
  );
};
