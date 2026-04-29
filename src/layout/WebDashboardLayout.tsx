import { NavLink } from 'react-router-dom';

export const WebDashboardLayout = ({ children }) => {
  return (
    <div className="flex h-screen bg-[var(--color-background)]">
      {/* Sidebar */}
      <aside className="w-64 bg-[var(--color-surface-container)] border-r border-[var(--color-outline-variant)]/10 flex flex-col">
        {/* Logo */}
        <div className="p-6 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-[var(--color-primary)] rounded-xl flex items-center justify-center text-[var(--color-on-primary)] shadow-lg shadow-[var(--color-primary)]/20">
              {/* Assuming we have a Zap icon from lucide-react */}
              <span className="text-xl">⚡</span>
            </div>
            <div>
              <h1 className="text-xl font-[Orbitron] font-bold tracking-tighter text-[var(--color-text)]">
                ATLAS <span className="text-[var(--color-primary)]">AI</span>
              </h1>
              <p className="text-[10px] font-bold uppercase tracking-widest text-[var(--color-on-surface-variant)]">
                Personal Trainer v2.0
              </p>
            </div>
          </div>
          {/* Optional: user avatar or settings */}
          <div className="w-8 h-8 bg-[var(--color-surface-variant)] rounded-full flex items-center justify-center text-[var(--color-on-surface-variant)]">
            <span className="text-xs">👤</span>
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-4 space-y-2">
          <NavLink
            to="/overview"
            end
            className={({ isActive }) => `
              flex items-center gap-3 p-3 rounded-lg text-[var(--color-on-surface-variant)] font-medium
              ${isActive ? 'bg-[var(--color-primary)]/10 text-[var(--color-primary)]' : 'hover:bg-[var(--color-surface-variant)]'}
            `}
          >
            <span className="text-xs">📊</span>
            <span>Overview</span>
          </NavLink>
          <NavLink
            to="/biometrics"
            className={({ isActive }) => `
              flex items-center gap-3 p-3 rounded-lg text-[var(--color-on-surface-variant)] font-medium
              ${isActive ? 'bg-[var(--color-primary)]/10 text-[var(--color-primary)]' : 'hover:bg-[var(--color-surface-variant)]'}
            `}
          >
            <span className="text-xs">❤️</span>
            <span>Biometrics</span>
          </NavLink>
          <NavLink
            to="/training"
            className={({ isActive }) => `
              flex items-center gap-3 p-3 rounded-lg text-[var(--color-on-surface-variant)] font-medium
              ${isActive ? 'bg-[var(--color-primary)]/10 text-[var(--color-primary)]' : 'hover:bg-[var(--color-surface-variant)]'}
            `}
          >
            <span className="text-xs">💪</span>
            <span>Training</span>
          </NavLink>
          <NavLink
            to="/readiness"
            className={({ isActive }) => `
              flex items-center gap-3 p-3 rounded-lg text-[var(--color-on-surface-variant)] font-medium
              ${isActive ? 'bg-[var(--color-primary)]/10 text-[var(--color-primary)]' : 'hover:bg-[var(--color-surface-variant)]'}
            `}
          >
            <span className="text-xs">🎯</span>
            <span>Readiness</span>
          </NavLink>
          <NavLink
            to="/memory"
            className={({ isActive }) => `
              flex items-center gap-3 p-3 rounded-lg text-[var(--color-on-surface-variant)] font-medium
              ${isActive ? 'bg-[var(--color-primary)]/10 text-[var(--color-primary)]' : 'hover:bg-[var(--color-surface-variant)]'}
            `}
          >
            <span className="text-xs">🧠</span>
            <span>Memory</span>
          </NavLink>
        </nav>

        {/* Footer */}
        <div className="p-6 border-t border-[var(--color-outline-variant)]/10">
          {/* Version or other info */}
          <p className="text-[10px] text-[var(--color-on-surface-variant)]/70">
            v1.0.0
          </p>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col overflow-hidden">
        {/* Top Bar */}
        <header className="h-16 bg-[var(--color-surface-container)]/50 backdrop-blur-md border-b border-[var(--color-outline-variant)]/10 flex items-center justify-between px-4 lg:px-6 z-10 shrink-0">
          <div className="flex items-center gap-4">
            {/* Optional: back button or menu for mobile view */}
            <button
              onClick={() => {}}
              className="lg:hidden p-2 hover:bg-[var(--color-surface-variant)] rounded-lg"
              title="Menu"
            >
              <span className="text-[var(--color-text-muted)]">≡</span>
            </button>
            <div className="flex-1">
              <h1 className="text-xl font-[Orbitron] font-bold text-[var(--color-text)]">
                Dashboard Overview
              </h1>
              <p className="text-sm text-[var(--color-on-surface-variant)]">
                Analytics and insights for your fitness journey
              </p>
            </div>
          </div>
          <div className="flex items-center gap-4">
            {/* User selector (placeholder for future multi-user) */}
            <div className="relative">
              <button
                className="flex items-center gap-2 p-2 bg-[var(--color-surface-variant)] rounded-lg hover:bg-[var(--color-surface-variant)]/75 transition-colors"
              >
                <span className="w-8 h-8 bg-[var(--color-primary)] rounded-full flex items-center justify-center text-[var(--color-on-primary)] text-sm">
                  S
                </span>
                <div>
                  <span className="text-xs font-medium text-[var(--color-text)]">Sergi</span>
                  <span className="text-[10px] text-[var(--color-on-surface-variant)]">default_user</span>
                </div>
              </button>
              {/* Dropdown would go here */}
            </div>

            {/* Refresh button */}
            <button
              onClick={() => {}}
              className="w-10 h-10 rounded-xl glass flex items-center justify-center text-[var(--color-on-surface-variant)] hover:text-[var(--color-primary)]"
            >
              <span className="text-xl">↻</span>
            </button>
          </div>
        </header>

        {/* Page Content */}
        <section className="flex-1 overflow-y-auto p-6 lg:p-8 space-y-8">
          {children}
        </section>
      </main>
    </div>
  );
};