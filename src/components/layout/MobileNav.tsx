// Mobile Navigation
// ===================
// Bottom navigation bar for mobile app

import { motion } from 'framer-motion';
import { useAtlasStore } from '../../store/atlasStore';
import { TABS } from '../../config';

export const MobileNav = () => {
  const { activeTab, setActiveTab } = useAtlasStore();

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 safe-bottom">
      <div className="glass border-t border-[var(--color-outline)]">
        <div className="flex items-center justify-around px-2 py-2">
          {TABS.map((tab) => (
            <motion.button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex flex-col items-center gap-1 px-3 py-2 rounded-xl transition-colors ${
                activeTab === tab.id
                  ? 'text-[var(--color-primary)]'
                  : 'text-[var(--color-text-muted)]'
              }`}
              whileTap={{ scale: 0.95 }}
            >
              <span className="text-xl">{tab.icon}</span>
              <span className="text-xs font-medium">{tab.label}</span>
              {activeTab === tab.id && (
                <motion.div
                  layoutId="activeTab"
                  className="absolute bottom-1 w-1 h-1 rounded-full bg-[var(--color-primary)]"
                />
              )}
            </motion.button>
          ))}
        </div>
      </div>
    </nav>
  );
};

export default MobileNav;
