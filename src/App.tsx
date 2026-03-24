import React, { useState, useEffect } from 'react';
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
  History,
  BrainCircuit,
  Loader2,
  X,
  TrendingUp,
  Target,
  Heart,
  Zap as PowerIcon,
  Activity as ActivityIcon
} from 'lucide-react';
import { GoogleGenAI } from "@google/genai";
import { motion, AnimatePresence } from "motion/react";

// Initialize Gemini
const genAI = new GoogleGenAI({ apiKey: process.env.GEMINI_API_KEY });

export default function App() {
  const [syncing, setSyncing] = useState(false);
  const [syncStatus, setSyncStatus] = useState<{ type: 'success' | 'error' | null, message: string }>({ type: null, message: "" });
  const [lastSync, setLastSync] = useState<string | null>(null);
  const [garminData, setGarminData] = useState<any>(null);
  const [wgerData, setWgerData] = useState<any>(null);
  const [coachAdvice, setCoachAdvice] = useState<string>("");
  const [loadingAdvice, setLoadingAdvice] = useState(false);
  const [showPentagonModal, setShowPentagonModal] = useState(false);
  const [showBioLabModal, setShowBioLabModal] = useState(false);

  const handleSync = async () => {
    setSyncing(true);
    setSyncStatus({ type: null, message: "" });
    try {
      // Sync Garmin
      const garminRes = await fetch('/api/sync/garmin', { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      let garminJson;
      const garminText = await garminRes.text();
      try {
        garminJson = JSON.parse(garminText);
      } catch (e) {
        throw new Error(`Garmin server error: ${garminRes.status}. Please check server logs.`);
      }
      
      let currentGarminData = null;
      if (garminJson.success) {
        setGarminData(garminJson.data);
        currentGarminData = garminJson.data;
      } else {
        console.error("Garmin sync error:", garminJson.error);
        setSyncStatus({ type: 'error', message: `Garmin: ${garminJson.error}` });
      }

      // Sync wger
      const wgerRes = await fetch('/api/sync/wger', { 
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      let wgerJson;
      const wgerText = await wgerRes.text();
      try {
        wgerJson = JSON.parse(wgerText);
      } catch (e) {
        console.error("wger parse error:", wgerText);
        // Don't throw here, let Garmin data be used if it succeeded
        wgerJson = { success: false, error: "Invalid response from wger sync" };
      }
      
      let currentWgerData = null;
      if (wgerJson.success) {
        setWgerData(wgerJson.data);
        currentWgerData = wgerJson.data;
      } else {
        console.error("wger sync error:", wgerJson.error);
        if (!syncStatus.message) {
          setSyncStatus({ type: 'error', message: `wger: ${wgerJson.error}` });
        }
      }

      if (garminJson.success || wgerJson.success) {
        setLastSync(new Date().toLocaleTimeString());
        if (!syncStatus.message || syncStatus.type === 'success') {
          setSyncStatus({ type: 'success', message: "Sync Completed" });
        }
        // Generate AI Advice after sync
        generateCoachAdvice(currentGarminData, currentWgerData);
      }
    } catch (error: any) {
      console.error("Sync failed:", error);
      setSyncStatus({ type: 'error', message: error.message || "Network error during sync" });
    } finally {
      setSyncing(false);
    }
  };

  const generateCoachAdvice = async (garmin?: any, wger?: any) => {
    setLoadingAdvice(true);
    try {
      const model = "gemini-3-flash-preview";
      const prompt = `
        You are an elite AI Fitness Coach. 
        Based on the following data, provide a concise, high-impact training and recovery recommendation.
        
        Garmin Data: ${JSON.stringify(garmin || "No data yet")}
        wger Data: ${JSON.stringify(wger || "No data yet")}
        
        Focus on:
        1. Readiness for today's session.
        2. Biomechanical load adjustments.
        3. Recovery priorities.
        
        Keep it under 150 words.
      `;

      const response = await genAI.models.generateContent({
        model,
        contents: prompt,
      });
      setCoachAdvice(response.text || "No advice available at the moment.");
    } catch (error) {
      console.error("AI Coach failed:", error);
      setCoachAdvice("Error generating AI advice. Please check your API key.");
    } finally {
      setLoadingAdvice(false);
    }
  };

  return (
    <div className="min-h-screen bg-background text-on-surface font-body selection:bg-primary-container selection:text-on-primary-container">
      {/* SideNavBar Component */}
      <aside className="h-screen w-64 fixed left-0 top-0 border-r border-opacity-10 border-outline-variant bg-surface-container-low font-headline antialiased flex flex-col py-8 z-50">
        <div className="px-6 mb-12">
          <h1 className="text-xl font-bold tracking-tighter text-[#00F2FF]">Vitalis Omni</h1>
          <p className="text-[10px] uppercase tracking-[0.2em] text-on-surface-variant">Elite Recovery</p>
        </div>
        <nav className="flex-1 space-y-2">
          <button 
            onClick={() => {}} 
            className="w-full flex items-center gap-4 text-on-surface-variant hover:text-[#00F2FF] transition-colors pl-4 py-3 hover:bg-surface-variant duration-200"
          >
            <LayoutDashboard size={20} />
            <span className="text-sm font-medium">Dashboard</span>
          </button>
          <button 
            onClick={() => setShowPentagonModal(true)} 
            className="w-full flex items-center gap-4 text-on-surface-variant hover:text-[#00F2FF] transition-colors pl-4 py-3 hover:bg-surface-variant duration-200"
          >
            <Activity size={20} />
            <span className="text-sm font-medium">Pentagon Console</span>
          </button>
          <button 
            onClick={() => setShowBioLabModal(true)} 
            className="w-full flex items-center gap-4 text-on-surface-variant hover:text-[#00F2FF] transition-colors pl-4 py-3 hover:bg-surface-variant duration-200"
          >
            <Microscope size={20} />
            <span className="text-sm font-medium">Biomechanical Lab</span>
          </button>
          <button 
            className="w-full flex items-center gap-4 text-[#00F2FF] font-bold border-l-2 border-[#00F2FF] pl-4 py-3 hover:bg-surface-variant duration-200"
          >
            <Sliders size={20} />
            <span className="text-sm font-medium">Command Center</span>
          </button>
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
            <span className={`w-2 h-2 rounded-full ${syncing ? 'bg-secondary animate-pulse' : (syncStatus.type === 'error' ? 'bg-tertiary' : 'bg-primary shadow-[0_0_8px_rgba(153,247,255,0.4)]')}`}></span>
            <span className="text-on-surface-variant">
              {syncing ? 'Syncing Data...' : (syncStatus.type === 'error' ? 'Sync Error' : 'System Online')}
            </span>
          </div>
          {lastSync && (
            <>
              <div className="h-4 w-[1px] bg-outline-variant opacity-20"></div>
              <div className="text-[10px] text-on-surface-variant uppercase tracking-widest">
                Last Sync: {lastSync}
              </div>
            </>
          )}
          <div className="h-4 w-[1px] bg-outline-variant opacity-20"></div>
          <div className="flex items-center gap-2">
            <span className="font-semibold text-primary">
              {garminData ? (
                `HR: ${garminData.heartRate?.averageHeartRate || '--'} bpm`
              ) : (
                'Readiness: 94'
              )}
            </span>
          </div>
        </div>
        <div className="flex items-center gap-6">
          {syncStatus.message && (
            <div className={`text-[10px] font-bold uppercase tracking-widest px-3 py-1 rounded-full ${syncStatus.type === 'error' ? 'bg-tertiary/10 text-tertiary' : 'bg-primary/10 text-primary'}`}>
              {syncStatus.message}
            </div>
          )}
          <div className="flex items-center gap-4 text-on-surface-variant">
            <button 
              onClick={handleSync}
              disabled={syncing}
              className={`hover:text-white transition-colors opacity-80 hover:opacity-100 ${syncing ? 'animate-spin' : ''}`}
            >
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
            <div className={`relative border rounded-xl p-6 overflow-hidden transition-all duration-500 ${
              (garminData?.sleep?.score < 60 || garminData?.heartRate?.averageHeartRate > 80) 
                ? 'bg-tertiary-container/10 border-tertiary/20' 
                : 'bg-primary-container/5 border-primary/10'
            }`}>
              <div className="absolute top-0 right-0 p-4 opacity-10">
                <AlertTriangle size={80} className={(garminData?.sleep?.score < 60 || garminData?.heartRate?.averageHeartRate > 80) ? 'text-tertiary fill-tertiary' : 'text-primary fill-primary'} />
              </div>
              <div className="relative z-10">
                <div className={`flex items-center gap-2 mb-2 ${
                  (garminData?.sleep?.score < 60 || garminData?.heartRate?.averageHeartRate > 80) ? 'text-tertiary' : 'text-primary'
                }`}>
                  <ShieldAlert size={18} className="fill-current" />
                  <span className="text-xs font-bold uppercase tracking-widest">
                    {(garminData?.sleep?.score < 60 || garminData?.heartRate?.averageHeartRate > 80) ? 'Power of Veto Active' : 'System Ready'}
                  </span>
                </div>
                <h3 className="text-xl font-headline font-bold mb-1">
                  {(garminData?.sleep?.score < 60 || garminData?.heartRate?.averageHeartRate > 80) ? 'TSB: -24 (Critical)' : 'TSB: +12 (Optimal)'}
                </h3>
                <p className="text-on-surface-variant text-xs leading-relaxed">
                  {(garminData?.sleep?.score < 60 || garminData?.heartRate?.averageHeartRate > 80) 
                    ? 'System has detected high physiological strain. Strength generation is locked for 24h to prevent overuse injury.'
                    : 'Physiological markers are within optimal ranges. Full strength generation is available for today\'s session.'}
                </p>
              </div>
            </div>
          </section>

          {/* AI Coach Section */}
          <section className="bg-surface-container rounded-xl p-6 border border-primary/20 shadow-[0_0_20px_rgba(153,247,255,0.05)]">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-primary/10 rounded-lg text-primary">
                <BrainCircuit size={24} />
              </div>
              <div>
                <h4 className="font-headline font-bold">AI Coach Insights</h4>
                <p className="text-[10px] text-on-surface-variant uppercase tracking-widest">Real-time Biometric Analysis</p>
              </div>
            </div>
            <div className="bg-surface-container-low p-4 rounded-lg border border-outline-variant/10 min-h-[100px] flex flex-col items-center justify-center gap-4">
              {loadingAdvice ? (
                <div className="flex flex-col items-center gap-2 text-on-surface-variant">
                  <Loader2 size={24} className="animate-spin" />
                  <span className="text-xs">Analyzing biometric load...</span>
                </div>
              ) : (
                <>
                  <p className="text-sm text-on-surface leading-relaxed italic text-center">
                    {coachAdvice || "Sync your data to receive personalized AI coaching insights based on your Garmin and wger activity."}
                  </p>
                  {wgerData && wgerData.length > 0 && (
                    <div className="flex items-center gap-2 px-3 py-1 bg-secondary/10 text-secondary rounded-full text-[10px] font-bold uppercase tracking-widest">
                      <Dumbbell size={12} />
                      Last Workout: {wgerData[0].comment || "Strength Session"}
                    </div>
                  )}
                </>
              )}
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
                          <select defaultValue="8.5" className="bg-surface-container-lowest border-none rounded-lg text-sm font-bold focus:ring-1 focus:ring-primary py-3 px-4 outline-none appearance-none">
                            <option>7.0</option>
                            <option>8.5</option>
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
                          <select defaultValue="-" className="bg-surface-container-lowest border-none rounded-lg text-sm font-bold focus:ring-1 focus:ring-primary py-3 px-4 outline-none appearance-none text-center">
                            <option disabled>-</option>
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
                          <select defaultValue="-" className="bg-surface-container-lowest border-none rounded-lg text-sm font-bold focus:ring-1 focus:ring-primary py-3 px-4 outline-none appearance-none text-center">
                            <option disabled>-</option>
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
                      <span className="text-primary">{garminData?.sleep?.score || 88}%</span>
                    </div>
                    <div className="h-1 w-full bg-surface-variant rounded-full overflow-hidden">
                      <div className="h-full bg-primary" style={{ width: `${garminData?.sleep?.score || 88}%` }}></div>
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
                      <span className="text-tertiary">{garminData?.heartRate?.minHeartRate ? 'Optimal' : 'Critical'}</span>
                    </div>
                    <div className="h-1 w-full bg-surface-variant rounded-full overflow-hidden">
                      <div className="h-full bg-tertiary" style={{ width: garminData?.heartRate?.minHeartRate ? '85%' : '24%' }}></div>
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

      {/* Pentagon Console Modal */}
      <AnimatePresence>
        {showPentagonModal && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowPentagonModal(false)}
              className="absolute inset-0 bg-background/80 backdrop-blur-md"
            />
            <motion.div 
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              className="relative w-full max-w-4xl bg-surface-container rounded-2xl border border-primary/20 shadow-2xl overflow-hidden"
            >
              <div className="p-6 border-b border-outline-variant/10 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-primary/10 rounded-lg text-primary">
                    <Activity size={24} />
                  </div>
                  <div>
                    <h3 className="font-headline font-bold text-xl">Pentagon Console</h3>
                    <p className="text-[10px] text-on-surface-variant uppercase tracking-widest">Multi-dimensional Performance Analysis</p>
                  </div>
                </div>
                <button 
                  onClick={() => setShowPentagonModal(false)}
                  className="p-2 hover:bg-surface-variant rounded-full transition-colors"
                >
                  <X size={20} />
                </button>
              </div>
              <div className="p-8 grid grid-cols-1 md:grid-cols-2 gap-8">
                <div className="space-y-6">
                  <h4 className="text-xs font-bold uppercase tracking-widest text-primary">Biometric Vectors</h4>
                  <div className="grid grid-cols-2 gap-4">
                    {[
                      { label: 'Strength', value: 88, icon: PowerIcon, color: 'text-primary' },
                      { label: 'Endurance', value: 72, icon: ActivityIcon, color: 'text-secondary' },
                      { label: 'Recovery', value: 94, icon: Heart, color: 'text-tertiary' },
                      { label: 'Focus', value: 81, icon: Target, color: 'text-primary' },
                    ].map((stat) => (
                      <div key={stat.label} className="bg-surface-container-low p-4 rounded-xl border border-outline-variant/10">
                        <div className="flex items-center gap-2 mb-2">
                          <stat.icon size={14} className={stat.color} />
                          <span className="text-[10px] uppercase font-bold text-on-surface-variant">{stat.label}</span>
                        </div>
                        <div className="text-2xl font-headline font-bold">{stat.value}%</div>
                      </div>
                    ))}
                  </div>
                  <div className="bg-primary/5 p-4 rounded-xl border border-primary/10">
                    <div className="flex items-center gap-2 mb-2 text-primary">
                      <TrendingUp size={16} />
                      <span className="text-xs font-bold uppercase tracking-widest">Performance Trend</span>
                    </div>
                    <p className="text-xs text-on-surface-variant leading-relaxed">
                      Your neuromuscular efficiency has increased by 4.2% over the last 7 days. Recommended load adjustment: +2.5kg on primary lifts.
                    </p>
                  </div>
                </div>
                <div className="flex items-center justify-center relative">
                  {/* Radar Chart Placeholder */}
                  <div className="w-64 h-64 rounded-full border border-primary/20 flex items-center justify-center relative">
                    <div className="absolute inset-0 border border-primary/10 rounded-full scale-75"></div>
                    <div className="absolute inset-0 border border-primary/10 rounded-full scale-50"></div>
                    <div className="absolute inset-0 border border-primary/10 rounded-full scale-25"></div>
                    {/* Pentagon Shape */}
                    <svg className="w-full h-full text-primary/40 fill-primary/10" viewBox="0 0 100 100">
                      <polygon points="50,10 90,40 75,90 25,90 10,40" stroke="currentColor" strokeWidth="1" />
                      <circle cx="50" cy="10" r="2" fill="currentColor" />
                      <circle cx="90" cy="40" r="2" fill="currentColor" />
                      <circle cx="75" cy="90" r="2" fill="currentColor" />
                      <circle cx="25" cy="90" r="2" fill="currentColor" />
                      <circle cx="10" cy="40" r="2" fill="currentColor" />
                    </svg>
                    <div className="absolute top-0 text-[8px] font-bold uppercase tracking-tighter">Strength</div>
                    <div className="absolute right-0 top-1/3 text-[8px] font-bold uppercase tracking-tighter translate-x-4">Endurance</div>
                    <div className="absolute right-4 bottom-0 text-[8px] font-bold uppercase tracking-tighter">Recovery</div>
                    <div className="absolute left-4 bottom-0 text-[8px] font-bold uppercase tracking-tighter">Mobility</div>
                    <div className="absolute left-0 top-1/3 text-[8px] font-bold uppercase tracking-tighter -translate-x-4">Focus</div>
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Biomechanical Lab Modal */}
      <AnimatePresence>
        {showBioLabModal && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-4">
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setShowBioLabModal(false)}
              className="absolute inset-0 bg-background/80 backdrop-blur-md"
            />
            <motion.div 
              initial={{ opacity: 0, scale: 0.9, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              exit={{ opacity: 0, scale: 0.9, y: 20 }}
              className="relative w-full max-w-4xl bg-surface-container rounded-2xl border border-secondary/20 shadow-2xl overflow-hidden"
            >
              <div className="p-6 border-b border-outline-variant/10 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-secondary/10 rounded-lg text-secondary">
                    <Microscope size={24} />
                  </div>
                  <div>
                    <h3 className="font-headline font-bold text-xl">Biomechanical Lab</h3>
                    <p className="text-[10px] text-on-surface-variant uppercase tracking-widest">Kinetic & Kinematic Diagnostics</p>
                  </div>
                </div>
                <button 
                  onClick={() => setShowBioLabModal(false)}
                  className="p-2 hover:bg-surface-variant rounded-full transition-colors"
                >
                  <X size={20} />
                </button>
              </div>
              <div className="p-8">
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                  {[
                    { label: 'Joint Stiffness', value: 'Low', status: 'Optimal', color: 'text-primary' },
                    { label: 'Neural Drive', value: 'High', status: 'Peaking', color: 'text-secondary' },
                    { label: 'Muscle Tone', value: 'Med', status: 'Recovered', color: 'text-tertiary' },
                  ].map((item) => (
                    <div key={item.label} className="bg-surface-container-low p-4 rounded-xl border border-outline-variant/10">
                      <span className="text-[10px] uppercase font-bold text-on-surface-variant block mb-1">{item.label}</span>
                      <div className="flex items-baseline gap-2">
                        <span className="text-xl font-headline font-bold">{item.value}</span>
                        <span className={`text-[9px] font-bold uppercase ${item.color}`}>{item.status}</span>
                      </div>
                    </div>
                  ))}
                </div>
                
                <div className="bg-surface-container-lowest p-6 rounded-xl border border-outline-variant/10">
                  <h4 className="text-xs font-bold uppercase tracking-widest text-on-surface-variant mb-4">Kinetic Chain Analysis</h4>
                  <div className="space-y-4">
                    {[
                      { part: 'Ankle Dorsiflexion', score: 92 },
                      { part: 'Hip Internal Rotation', score: 78 },
                      { part: 'Thoracic Extension', score: 85 },
                      { part: 'Shoulder Flexion', score: 94 },
                    ].map((part) => (
                      <div key={part.part} className="space-y-1">
                        <div className="flex justify-between text-[10px] uppercase font-bold">
                          <span>{part.part}</span>
                          <span className="text-secondary">{part.score}%</span>
                        </div>
                        <div className="h-1.5 w-full bg-surface-variant rounded-full overflow-hidden">
                          <motion.div 
                            initial={{ width: 0 }}
                            animate={{ width: `${part.score}%` }}
                            transition={{ duration: 1, delay: 0.2 }}
                            className="h-full bg-secondary"
                          />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
