import React, { useState, useMemo, useRef } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import api from '../services/api';
import { MemoryEntry } from '../types';
import { ChartSkeleton } from '../components/charts/ChartSkeleton';
import { ExportButton } from '../components/common/ExportButton';

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
  isSubmitting: boolean;
}

const AddMemoryModal: React.FC<AddMemoryModalProps> = ({ isOpen, onClose, onAdd, isSubmitting }) => {
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
              disabled={isSubmitting}
              className="flex-1 px-4 py-2 rounded-lg bg-[var(--color-primary)] text-[var(--color-on-primary)] font-medium hover:brightness-110 transition-colors disabled:opacity-50"
            >
              {isSubmitting ? 'Adding...' : 'Add Memory'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export const MemoryPage = () => {
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const memoryRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();

  const { data: memoryData, isLoading, isError, error } = useQuery({
    queryKey: ['memory', 90],
    queryFn: async () => {
      const response = await api.get('/memory/summary', { params: { days: 90 } });
      return response.data;
    },
    staleTime: 30 * 60 * 1000,
  });

  const addMutation = useMutation({
    mutationFn: async (newMemory: { type: string; content: string; date: string; importance: number; source: string }) => {
      const response = await api.post('/memory/entry', newMemory);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['memory'] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (memoryId: number) => {
      await api.delete(`/memory/${memoryId}`);
      return memoryId;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['memory'] });
    },
  });

  const memories: MemoryEntry[] = memoryData?.memories ?? [];

  const toggleType = (type: string) => {
    setSelectedTypes(prev =>
      prev.includes(type)
        ? prev.filter(t => t !== type)
        : [...prev, type]
    );
  };

  const filteredMemories = useMemo(() => {
    if (selectedTypes.length === 0) return memories;
    return memories.filter(m => selectedTypes.includes(m.type));
  }, [memories, selectedTypes]);

  const groupedMemories = useMemo(() => {
    const grouped: Record<string, MemoryEntry[]> = {};
    filteredMemories.forEach(memory => {
      if (!grouped[memory.date]) {
        grouped[memory.date] = [];
      }
      grouped[memory.date].push(memory);
    });
    return grouped;
  }, [filteredMemories]);

  const handleAddMemory = (newMemory: { type: string; content: string; date: string; importance: number; source: string }) => {
    addMutation.mutate(newMemory);
  };

  const handleDeleteMemory = (id: number) => {
    deleteMutation.mutate(id);
  };

  const exportMemories = () => {
    if (memories.length === 0) return;
    const data = memories.map(m => ({
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

  if (isError) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-display font-bold text-[var(--color-text)]">
          Memory Timeline
        </h1>
        <div className="bg-[var(--color-danger)]/10 border border-[var(--color-danger)]/20 rounded-lg p-4">
          <p className="text-[var(--color-danger)] text-sm">Error loading memories: {error instanceof Error ? error.message : 'Unknown error'}</p>
        </div>
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
          <ExportButton data={memories} filename="memories" format="csv" onExport={exportMemories} />
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
        {Object.entries(groupedMemories).map(([date, dateMemories]) => (
          <div key={date} className="mb-8">
            <div className="sticky top-0 z-10 bg-[var(--color-background)]/80 backdrop-blur-sm py-2 mb-4">
              <h3 className="text-sm font-bold text-[var(--color-text-muted)] uppercase tracking-wider">
                {new Date(date).toLocaleDateString('en-US', {
                  weekday: 'long',
                  year: 'numeric',
                  month: 'long',
                  day: 'numeric',
                })}
              </h3>
            </div>
            <div className="space-y-4">
              {dateMemories.map(memory => {
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
                      disabled={deleteMutation.isPending}
                      className="absolute top-2 right-2 p-1.5 rounded-lg opacity-0 group-hover:opacity-100 hover:bg-[var(--color-danger)]/10 text-[var(--color-text-muted)] hover:text-[var(--color-danger)] transition-all disabled:opacity-30"
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
                        {memory.source === 'auto' || memory.source === 'garmin_sync' ? 'Auto' : 'User'}
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
              {selectedTypes.length > 0 ? 'No memories match the selected filters' : 'No memories yet — add your first memory or sync Garmin data to auto-generate entries'}
            </p>
          </div>
        )}
      </div>

      <AddMemoryModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onAdd={handleAddMemory}
        isSubmitting={addMutation.isPending}
      />
    </div>
  );
};
