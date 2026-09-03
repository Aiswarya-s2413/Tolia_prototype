import React from 'react';
import { 
  Bot, 
  Globe, 
  ShieldCheck, 
  Database, 
  MessageSquare, 
  Lock, 
  Unlock, 
  Activity, 
  Layers,
  ChevronDown
} from 'lucide-react';

export default function Header({ activeTab, setActiveTab, activeRole, setRole, lang, setLang }) {
  const getNavTitle = (key) => {
    switch (key) {
      case 'chat':
        return lang === 'hi' ? 'वॉयस सहायक (Voice AI)' : lang === 'mr' ? 'व्हॉईस सहाय्यक (Voice AI)' : 'Voice Assistant';
      case 'docs':
        return lang === 'hi' ? 'ज्ञान कोष (KB)' : lang === 'mr' ? 'ज्ञानकोश (KB)' : 'Knowledge Base';
      case 'security':
        return lang === 'hi' ? 'सुरक्षा नियम' : lang === 'mr' ? 'सुरक्षा नियम' : 'RBAC Security';
      default:
        return key;
    }
  };

  return (
    <header className="sticky top-0 z-50 glass-panel border-b border-slate-800/90 bg-slate-950/85 backdrop-blur-2xl">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 gap-4">
          
          {/* Brand Logo & System Title */}
          <div className="flex items-center gap-3 shrink-0">
            <div className="relative flex items-center justify-center">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 via-indigo-600 to-cyan-500 flex items-center justify-center shadow-lg shadow-indigo-500/20 ring-1 ring-white/10">
                <Bot className="w-5 h-5 text-white" />
              </div>
              <span className="absolute -top-1 -right-1 flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
              </span>
            </div>

            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-base tracking-tight text-white font-sans flex items-center gap-1.5">
                  {lang === 'hi' ? 'टोलिया वॉयस सहायक' : lang === 'mr' ? 'टोलिया व्हॉईस सहाय्यक' : 'Tolia Voice AI'}
                </span>
                <span className="hidden sm:inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 font-mono">
                  LOCAL INDIC VOICE
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-medium">
                {lang === 'hi'
                  ? 'संयंत्र एआई वॉयस सहायक एवं RAG सुरक्षा प्रणाली'
                  : lang === 'mr'
                  ? 'कारखाना एआय व्हॉईस सहाय्यक व RAG सुरक्षा प्रणाली'
                  : 'Industrial Voice-First AI & Knowledge RAG System'}
              </p>
            </div>
          </div>

          {/* Right Action Controls: Role Switcher + Language Selector */}
          <div className="flex items-center gap-2.5">
            
            {/* Quick Active Role Dropdown / Pill */}
            <div className="flex items-center bg-slate-900 p-1 rounded-xl border border-slate-800">
              <button
                onClick={() => setRole(activeRole === 'CEO' ? 'QC' : 'CEO')}
                className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-bold transition-all ${
                  activeRole === 'CEO'
                    ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30'
                    : 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30'
                }`}
                title="Click to toggle active department role"
              >
                {activeRole === 'CEO' ? (
                  <>
                    <Unlock className="w-3.5 h-3.5 text-indigo-400" />
                    <span>CEO</span>
                    <span className="hidden lg:inline text-[10px] text-slate-400 font-normal">(Sales Unlocked)</span>
                  </>
                ) : (
                  <>
                    <Lock className="w-3.5 h-3.5 text-rose-400" />
                    <span>QC Inspector</span>
                    <span className="hidden lg:inline text-[10px] text-slate-400 font-normal">(Sales Locked)</span>
                  </>
                )}
              </button>
            </div>

            {/* Dynamic Auto-Detect Multi-Language Badge */}
            <div className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900 border border-slate-800 text-xs font-semibold text-slate-300 shadow-sm">
              <Globe className="w-3.5 h-3.5 text-cyan-400 animate-pulse" />
              <span className="text-cyan-300 font-bold">Auto-Detect</span>
              <span className="text-[10px] text-slate-400 font-mono hidden sm:inline">(EN • HI • MR)</span>
            </div>

          </div>
        </div>
      </div>
    </header>
  );
}

