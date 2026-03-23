import React from 'react';
import {
  LayoutDashboard,
  Activity,
  Microscope,
  Sliders,
  User,
  RefreshCw,
  Bell,
  UserCircle,
  AlertTriangle,
  ShieldAlert,
  Dumbbell,
  CheckCircle2,
  MoreHorizontal,
  Lock,
  Zap,
  Wand2,
  History
} from 'lucide-react';

export default function App() {
  return (
    <div className="min-h-screen bg-background text-on-surface font-body selection:bg-primary-container selection:text-on-primary-container">
      {/* SideNavBar Component */}
      <aside className="h-screen w-64 fixed left-0 top-0 border-r border-opacity-10 border-outline-variant bg-surface-container-low font-headline antialiased flex flex-col py-8 z-50">
        <div className="px-6 mb-12">
          <h1 className="text-xl font-bold tracking-tighter text-[#00F2FF]">Vitalis Omni</h1>
          <p className="text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">Elite Recovery</p>
        </div>
        <nav className="flex-1 space-y-2">
          <a className="flex items-center gap-4 text-on-surface-variant hover:text-[#00F2FF] transition-colors pl-4 py-3 hover:bg-surface-variant duration-200" href="#">
            <LayoutDashboard size={20} />
            <span className="text-sm font-medium">Dashboard</span>
          </a>
          <a className="flex items-center gap-4 text-on-surface-variant hover:text-[#00F2FF] transition-colors pl-4 py-3 hover:bg-surface-variant duration-200" href="#">
            <Activity size={20} />
            <span className="text-sm font-medium">Pentagon Console</span>
          </a>
          <a className="flex items-center gap-4 text-on-surface-variant hover:text-[#00F2FF] transition-colors pl-4 py-3 hover:bg-surface-variant duration-200" href="#">
            <Microscope size={20} />
            <span className="text-sm font-medium">Biomechanical Lab</span>
          </a>
          <a className="flex items-center gap-4 text-[#00F2FF] font-bold border-l-2 border-[#00F2FF] pl-4 py-3 hover:bg-surface-variant duration-200" href="#">
            <Sliders size={20} />
            <span className="text-sm font-medium">Command Center</span>
          </a>
        </nav>
        <div className="px-6 mt-auto">
          <div className="flex items-center gap-3 p-3 bg-surface-container rounded-lg border border-outline-variant border-opacity-10">
            <div className="w-8 h-8 rounded-full bg-primary-container/20 flex items-center justify-center">
              <User size={18} className="text-[#00F2FF]" />
            </div>
            <div className="overflow-hidden">
              <p className="text-xs font-bold truncate">Dr. Sterling</p>
              <p className="text-[10px] text-on-surface-variant truncate">Clinician Profile</p>
            </div>
          </div>
        </div>
      </aside>

      {/* TopNavBar Component */}
      <header className="fixed top-0 right-0 w-[calc(100%-16rem)] h-14 z-40 bg-background/80 backdrop-blur-xl flex items-center justify-between px-6 border-b border-opacity-5 border-outline-variant font-body text-sm tracking-wide">
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-primary shadow-[0_0_8px_rgba(153,247,255,0.4)]"></span>
            <span className="text-on-surface-variant">Syncing with Garmin</span>
          </div>
          <div className="h-4 w-[1px] bg-outline-variant opacity-20"></div>
          <div className="flex items-center gap-2">
            <span className="font-semibold text-primary">Readiness: 94</span>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <div className="flex items-center gap-4 text-on-surface-variant">
            <button className="hover:text-white transition-colors opacity-80 hover:opacity-100">
              <RefreshCw size={20} />
            </button>
            <button className="hover:text-white transition-colors opacity-80 hover:opacity-100">
              <Bell size={20} />
            </button>
            <button className="hover:text-white transition-colors opacity-80 hover:opacity-100">
              <UserCircle size={20} />
            </button>
          </div>
          <button className="bg-primary-container text-on-primary-container px-4 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider hover:brightness-110 transition-all">
            System Status
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="ml-64 pt-20 p-8 min-h-screen">
        <div className="max-w-6xl mx-auto space-y-8">
          
          {/* Page Header & TSB Alert */}
          <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <h2 className="font-headline text-3xl font-bold tracking-tight mb-2">Routine Command</h2>
              <p className="text-on-surface-variant text-sm">Real-time biomechanical load adjustment and session logging.</p>
            </div>
            
            {/* Power of Veto / Critical Recovery Card */}
            <div className="relative bg-tertiary-container/10 border border-tertiary/20 rounded-xl p-6 overflow-hidden">
              <div className="absolute top-0 right-0 p-4 opacity-10">
                <AlertTriangle size={80} className="text-tertiary fill-tertiary" />
              </div>
              <div className="relative z-10">
                <div className="flex items-center gap-2 text-tertiary mb-2">
                  <ShieldAlert size={18} className="fill-tertiary" />
                  <span className="text-xs font-bold uppercase tracking-widest">Power of Veto Active</span>
                </div>
                <h3 className="text-xl font-headline font-bold mb-1">TSB: -24 (Critical)</h3>
                <p className="text-on-surface-variant text-xs leading-relaxed">
                  System has detected high physiological strain. Strength generation is locked for 24h to prevent overuse injury.
                </p>
              </div>
            </div>
          </section>

          {/* Workout Interaction Area */}
          <div className="grid grid-cols-1 xl:grid-cols-4 gap-8">
            
            {/* Main Routine Table */}
            <section className="xl:col-span-3 space-y-6">
              <div className="bg-surface-container rounded-xl overflow-hidden shadow-2xl">
                <div className="p-6 flex items-center justify-between border-b border-outline-variant/10">
                  <div className="flex items-center gap-4">
                    <span className="bg-primary/10 text-primary p-2 rounded-lg">
                      <Dumbbell size={24} />
                    </span>
                    <div>
                      <h4 className="font-bold">Active Protocol: Hybrid Strength A</h4>
                      <p className="text-[10px] text-on-surface-variant uppercase tracking-tighter">Hypertrophy & Neuromuscular Focus</p>
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button className="px-4 py-2 text-xs font-bold border border-outline-variant/30 rounded-lg hover:bg-surface-variant transition-colors">
                      MODIFY
                    </button>
                    <button className="px-4 py-2 text-xs font-bold bg-primary-container text-on-primary-container rounded-lg hover:brightness-110 transition-all">
                      SAVE SESSION
                    </button>
                  </div>
                </div>
                
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse">
                    <thead>
                      <tr className="bg-surface-container-low text-[10px] font-bold uppercase tracking-widest text-on-surface-variant">
                        <th className="px-6 py-4">Exercise</th>
                        <th className="px-6 py-4">Reps</th>
                        <th className="px-6 py-4">Weight (kg)</th>
                        <th className="px-6 py-4">RPE</th>
                        <th className="px-6 py-4 text-right">Log Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-outline-variant/10">
                      <tr className="hover:bg-surface-container-high transition-colors group">
                        <td className="px-6 py-5">
                          <div className="flex flex-col">
                            <span className="font-medium text-primary">Barbell Back Squat</span>
                            <span className="text-[10px] text-on-surface-variant">Set 1 of 4 • Tempo 3-0-1</span>
                          </div>
                        </td>
                        <td className="px-6 py-5">
                          <input className="w-16 bg-surface-container-lowest border-none rounded-lg text-center font-bold text-lg focus:ring-1 focus:ring-primary py-3 outline-none" type="number" defaultValue="8" />
                        </td>
                        <td className="px-6 py-5">
                          <input className="w-24 bg-surface-container-lowest border-none rounded-lg text-center font-bold text-lg focus:ring-1 focus:ring-primary py-3 outline-none" type="number" defaultValue="102.5" />
                        </td>
                        <td className="px-6 py-5">
                          <select className="bg-surface-container-lowest border-none rounded-lg text-sm font-bold focus:ring-1 focus:ring-primary py-3 px-4 outline-none appearance-none">
                            <option>7.0</option>
                            <option selected>8.5</option>
                            <option>9.0</option>
                            <option>10</option>
                          </select>
                        </td>
                        <td className="px-6 py-5 text-right">
                          <button className="w-10 h-10 rounded-full bg-primary/10 text-primary flex items-center justify-center group-hover:scale-110 transition-transform ml-auto">
                            <CheckCircle2 size={20} />
                          </button>
                        </td>
                      </tr>
                      <tr className="hover:bg-surface-container-high transition-colors group">
                        <td className="px-6 py-5">
                          <div className="flex flex-col">
                            <span className="font-medium">ROManian Deadlift</span>
                            <span className="text-[10px] text-on-surface-variant">Set 1 of 3 • Focus on Eccentric</span>
                          </div>
                        </td>
                        <td className="px-6 py-5">
                          <input className="w-16 bg-surface-container-lowest border-none rounded-lg text-center font-bold text-lg focus:ring-1 focus:ring-primary py-3 outline-none" placeholder="0" type="number" />
                        </td>
                        <td className="px-6 py-5">
                          <input className="w-24 bg-surface-container-lowest border-none rounded-lg text-center font-bold text-lg focus:ring-1 focus:ring-primary py-3 outline-none" placeholder="0.0" type="number" />
                        </td>
                        <td className="px-6 py-5">
                          <select className="bg-surface-container-lowest border-none rounded-lg text-sm font-bold focus:ring-1 focus:ring-primary py-3 px-4 outline-none appearance-none text-center">
                            <option disabled selected>-</option>
                            <option>7.0</option>
                            <option>8.0</option>
                            <option>9.0</option>
                          </select>
                        </td>
                        <td className="px-6 py-5 text-right">
                          <button className="w-10 h-10 rounded-full bg-surface-variant text-on-surface-variant flex items-center justify-center ml-auto">
                            <MoreHorizontal size={20} />
                          </button>
                        </td>
                      </tr>
                      <tr className="hover:bg-surface-container-high transition-colors group">
                        <td className="px-6 py-5">
                          <div className="flex flex-col">
                            <span className="font-medium">Plyometric Box Jumps</span>
                            <span className="text-[10px] text-on-surface-variant">Set 1 of 3 • Max Power Output</span>
                          </div>
                        </td>
                        <td className="px-6 py-5">
                          <input className="w-16 bg-surface-container-lowest border-none rounded-lg text-center font-bold text-lg focus:ring-1 focus:ring-primary py-3 outline-none" placeholder="5" type="number" />
                        </td>
                        <td className="px-6 py-5">
                          <span className="text-xs text-on-surface-variant italic">Bodyweight</span>
                        </td>
                        <td className="px-6 py-5">
                          <select className="bg-surface-container-lowest border-none rounded-lg text-sm font-bold focus:ring-1 focus:ring-primary py-3 px-4 outline-none appearance-none text-center">
                            <option disabled selected>-</option>
                            <option>Explosive</option>
                            <option>Controlled</option>
                          </select>
                        </td>
                        <td className="px-6 py-5 text-right">
                          <button className="w-10 h-10 rounded-full bg-surface-variant text-on-surface-variant flex items-center justify-center ml-auto">
                            <MoreHorizontal size={20} />
                          </button>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Generation Actions */}
              <div className="flex flex-col md:flex-row gap-4">
                <div className="flex-1 bg-surface-container p-6 rounded-xl border border-outline-variant/10 relative overflow-hidden group">
                  {/* Overlay for disabled state */}
                  <div className="absolute inset-0 bg-surface-container-lowest/80 backdrop-blur-sm z-20 flex flex-col items-center justify-center text-center p-6 border border-tertiary/20">
                    <Lock size={24} className="text-tertiary mb-2" />
                    <h5 className="text-sm font-bold text-tertiary uppercase tracking-widest">Strength Engine Locked</h5>
                    <p className="text-[10px] text-on-surface-variant mt-1">Recovery Threshold Not Met. Manual Override Only.</p>
                  </div>
                  <div className="flex items-start justify-between opacity-30">
                    <div>
                      <h5 className="font-headline font-bold mb-2">Generate Strength Training</h5>
                      <p className="text-xs text-on-surface-variant">AI-curated progressive overload based on your 1RM history.</p>
                    </div>
                    <Zap size={24} className="text-primary" />
                  </div>
                  <button className="mt-6 w-full bg-primary/20 text-primary-dim/40 cursor-not-allowed py-3 rounded-lg font-bold text-xs uppercase tracking-widest border border-primary/10" disabled>
                    GENERATE SESSION
                  </button>
                </div>
                
                <div className="flex-1 bg-surface-container p-6 rounded-xl border border-outline-variant/10 group hover:border-primary/30 transition-all">
                  <div className="flex items-start justify-between">
                    <div>
                      <h5 className="font-headline font-bold mb-2">Generate Mobility & Prep</h5>
                      <p className="text-xs text-on-surface-variant">Active recovery sequence optimized for current tissue stiffness.</p>
                    </div>
                    <Wand2 size={24} className="text-secondary" />
                  </div>
                  <button className="mt-6 w-full bg-secondary text-on-secondary py-3 rounded-lg font-bold text-xs uppercase tracking-widest hover:brightness-110 transition-all">
                    GENERATE FLOW
                  </button>
                </div>
              </div>
            </section>

            {/* Sidebar Content: History & Stats */}
            <aside className="space-y-6">
              {/* Session History */}
              <div className="bg-surface-container p-6 rounded-xl">
                <h5 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-4 flex items-center gap-2">
                  <History size={16} />
                  Previous Sessions
                </h5>
                <div className="space-y-4">
                  <div className="p-3 bg-surface-container-low rounded-lg border-l-2 border-primary">
                    <p className="text-[10px] text-on-surface-variant">OCT 24, 08:32 AM</p>
                    <p className="text-sm font-bold">Endurance Recovery 2</p>
                    <div className="flex items-center gap-2 mt-2">
                      <span className="px-1.5 py-0.5 bg-surface-variant text-[9px] rounded uppercase font-bold text-on-surface-variant">92 MIN</span>
                      <span className="px-1.5 py-0.5 bg-surface-variant text-[9px] rounded uppercase font-bold text-on-surface-variant">Low Load</span>
                    </div>
                  </div>
                  <div className="p-3 bg-surface-container-low rounded-lg border-l-2 border-tertiary">
                    <p className="text-[10px] text-on-surface-variant">OCT 22, 05:45 PM</p>
                    <p className="text-sm font-bold">Max Power Testing</p>
                    <div className="flex items-center gap-2 mt-2">
                      <span className="px-1.5 py-0.5 bg-surface-variant text-[9px] rounded uppercase font-bold text-on-surface-variant">45 MIN</span>
                      <span className="px-1.5 py-0.5 bg-tertiary/20 text-tertiary text-[9px] rounded uppercase font-bold">Incomplete</span>
                    </div>
                  </div>
                  <div className="p-3 bg-surface-container-low rounded-lg border-l-2 border-primary">
                    <p className="text-[10px] text-on-surface-variant">OCT 20, 06:15 AM</p>
                    <p className="text-sm font-bold">Hybrid Strength A</p>
                    <div className="flex items-center gap-2 mt-2">
                      <span className="px-1.5 py-0.5 bg-surface-variant text-[9px] rounded uppercase font-bold text-on-surface-variant">78 MIN</span>
                      <span className="px-1.5 py-0.5 bg-primary/20 text-primary text-[9px] rounded uppercase font-bold">Optimal</span>
                    </div>
                  </div>
                </div>
                <button className="w-full mt-4 text-[10px] font-bold text-primary hover:underline uppercase tracking-widest">
                  View Full Archive
                </button>
              </div>

              {/* Readiness HUD (Quick Glance) */}
              <div className="bg-surface-container-lowest p-6 rounded-xl border border-outline-variant/10">
                <h5 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-6">Readiness HUD</h5>
                <div className="space-y-6">
                  <div className="space-y-2">
                    <div className="flex justify-between text-[10px] uppercase font-bold">
                      <span>CNS Recovery</span>
                      <span className="text-primary">88%</span>
                    </div>
                    <div className="h-1 w-full bg-surface-variant rounded-full overflow-hidden">
                      <div className="h-full bg-primary" style={{ width: '88%' }}></div>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-[10px] uppercase font-bold">
                      <span>Metabolic Efficiency</span>
                      <span className="text-secondary">62%</span>
                    </div>
                    <div className="h-1 w-full bg-surface-variant rounded-full overflow-hidden">
                      <div className="h-full bg-secondary" style={{ width: '62%' }}></div>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-[10px] uppercase font-bold">
                      <span>HRV Baseline</span>
                      <span className="text-tertiary">Critical</span>
                    </div>
                    <div className="h-1 w-full bg-surface-variant rounded-full overflow-hidden">
                      <div className="h-full bg-tertiary" style={{ width: '24%' }}></div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Visual Accent Card */}
              <div className="relative h-48 rounded-xl overflow-hidden group">
                <img 
                  alt="Workout focus" 
                  className="absolute inset-0 w-full h-full object-cover grayscale opacity-40 group-hover:scale-110 transition-transform duration-700" 
                  src="https://images.unsplash.com/photo-1517836357463-d25dfeac3438?q=80&w=2070&auto=format&fit=crop" 
                />
                <div className="absolute inset-0 bg-gradient-to-t from-background via-transparent to-transparent"></div>
                <div className="absolute bottom-0 left-0 p-4">
                  <p className="text-[10px] text-primary font-bold uppercase tracking-widest">Technique Focus</p>
                  <h6 className="text-sm font-headline font-bold">The Squat Wedge</h6>
                </div>
              </div>
            </aside>
          </div>
        </div>
      </main>
    </div>
  );
}
