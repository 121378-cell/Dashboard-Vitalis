import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import useNotifications, { type AtlasNotification, type NotificationFilter } from '../hooks/useNotifications';

const TYPE_ICONS: Record<string, string> = {
  daily_readiness: '\u{1f4ca}',
  insight: '\u{1f4a1}',
  hydration: '\u{1f4a7}',
  plan: '\u{1f4c5}',
  achievement: '\u{1f3c6}',
  general: '\u{1f514}',
};

const PRIORITY_BORDER: Record<string, string> = {
  urgent: 'border-l-red-500',
  high: 'border-l-orange-400',
  medium: 'border-l-blue-400',
  low: 'border-l-gray-500',
};

const FILTER_TABS: { id: NotificationFilter; label: string }[] = [
  { id: 'all', label: 'Todas' },
  { id: 'unread', label: 'Sin leer' },
  { id: 'training', label: 'Entrenamiento' },
  { id: 'recovery', label: 'Recuperaci\u00f3n' },
  { id: 'reminders', label: 'Recordatorios' },
];

function timeAgo(dateStr: string | null): string {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'Ahora';
  if (diffMin < 60) return `Hace ${diffMin} min`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `Hace ${diffH}h`;
  const diffD = Math.floor(diffH / 24);
  return `Hace ${diffD}d`;
}

export function NotificationCenter() {
  const [isOpen, setIsOpen] = useState(false);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  const {
    notifications,
    unreadCount,
    isConnected,
    filter,
    setFilter,
    markRead,
    markAllRead,
    latestToast,
    dismissToast,
  } = useNotifications();

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    }
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [isOpen]);

  const handleNotificationClick = async (n: AtlasNotification) => {
    if (!n.read_at) {
      await markRead(n.id);
    }
    if (n.action_url) {
      setIsOpen(false);
      navigate(n.action_url);
    }
    setExpandedId(expandedId === n.id ? null : n.id);
  };

  return (
    <>
      {/* Bell Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative w-10 h-10 rounded-xl flex items-center justify-center
          bg-[var(--color-surface-variant)] hover:bg-[var(--color-surface-variant)]/75
          transition-colors text-[var(--color-on-surface-variant)]"
      >
        <span className="text-lg">{'\u{1f514}'}</span>
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] font-bold
            rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
        {isConnected && (
          <span className="absolute bottom-0 right-0 w-2 h-2 bg-green-400 rounded-full" />
        )}
      </button>

      {/* Drawer Panel */}
      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 0.5 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black z-40"
              onClick={() => setIsOpen(false)}
            />
            <motion.div
              ref={panelRef}
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 300 }}
              className="fixed right-0 top-0 h-full w-96 max-w-[90vw]
                bg-[var(--color-surface-container)] border-l border-[var(--color-outline-variant)]/10
                z-50 flex flex-col shadow-2xl"
            >
              {/* Header */}
              <div className="flex items-center justify-between p-4 border-b border-[var(--color-outline-variant)]/10">
                <h2 className="text-lg font-bold text-[var(--color-text)]">Notificaciones</h2>
                <div className="flex items-center gap-2">
                  {unreadCount > 0 && (
                    <button
                      onClick={markAllRead}
                      className="text-xs text-[var(--color-primary)] hover:underline"
                    >
                      Marcar todas le\u00eddas
                    </button>
                  )}
                  <button
                    onClick={() => setIsOpen(false)}
                    className="w-8 h-8 rounded-lg flex items-center justify-center
                      text-[var(--color-on-surface-variant)] hover:bg-[var(--color-surface-variant)]"
                  >
                    \u2715
                  </button>
                </div>
              </div>

              {/* Filter Tabs */}
              <div className="flex gap-1 p-3 border-b border-[var(--color-outline-variant)]/10 overflow-x-auto">
                {FILTER_TABS.map(tab => (
                  <button
                    key={tab.id}
                    onClick={() => setFilter(tab.id)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors
                      ${filter === tab.id
                        ? 'bg-[var(--color-primary)]/20 text-[var(--color-primary)]'
                        : 'text-[var(--color-on-surface-variant)] hover:bg-[var(--color-surface-variant)]'
                      }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Notification List */}
              <div className="flex-1 overflow-y-auto">
                {notifications.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-48 text-[var(--color-on-surface-variant)]/50">
                    <span className="text-3xl mb-2">{'\u{1f514}'}</span>
                    <p className="text-sm">No hay notificaciones</p>
                  </div>
                ) : (
                  notifications.map(n => (
                    <div
                      key={n.id}
                      onClick={() => handleNotificationClick(n)}
                      className={`border-l-4 ${PRIORITY_BORDER[n.priority] || 'border-l-gray-500'}
                        p-4 border-b border-[var(--color-outline-variant)]/5 cursor-pointer
                        hover:bg-[var(--color-surface-variant)]/50 transition-colors
                        ${!n.read_at ? 'bg-[var(--color-primary)]/5' : ''}`}
                    >
                      <div className="flex items-start gap-3">
                        <span className="text-lg shrink-0 mt-0.5">
                          {TYPE_ICONS[n.notification_type] || TYPE_ICONS.general}
                        </span>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-start justify-between gap-2">
                            <p className={`text-sm ${!n.read_at ? 'font-bold text-[var(--color-text)]' : 'font-medium text-[var(--color-on-surface-variant)]'}`}>
                              {n.title}
                            </p>
                            <span className="text-[10px] text-[var(--color-on-surface-variant)]/60 whitespace-nowrap">
                              {timeAgo(n.created_at)}
                            </span>
                          </div>
                          <p className={`text-xs text-[var(--color-on-surface-variant)] mt-1
                            ${expandedId === n.id ? '' : 'line-clamp-2'}`}>
                            {n.message}
                          </p>
                          {n.action_url && (
                            <span className="inline-block mt-2 text-[10px] font-medium
                              text-[var(--color-primary)] hover:underline">
                              Ver \u2192
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Toast */}
      <AnimatePresence>
        {latestToast && (
          <motion.div
            initial={{ opacity: 0, y: -20, x: 50 }}
            animate={{ opacity: 1, y: 0, x: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
            onClick={dismissToast}
            className="fixed top-4 right-4 z-[60] max-w-sm p-4 rounded-xl
              bg-[var(--color-surface-container)] border border-[var(--color-outline-variant)]/10
              shadow-2xl cursor-pointer"
          >
            <div className="flex items-start gap-3">
              <span className="text-lg">{'\u{1f514}'}</span>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-bold text-[var(--color-text)]">{latestToast.title}</p>
                <p className="text-xs text-[var(--color-on-surface-variant)] mt-1 line-clamp-2">
                  {latestToast.message}
                </p>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}

export default NotificationCenter;
