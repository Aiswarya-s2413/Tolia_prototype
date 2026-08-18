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
        return lang === 'hi' ? 'एआई सहायक' : lang === 'mr' ? 'एआय सहाय्यक' : 'AI Assistant';
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
                  {lang === 'hi' ? 'एआई कारखाना सहायक' : lang === 'mr' ? 'एआय कारखाना सहाय्यक' : 'AI Assistant'}
                </span>
                <span className="hidden sm:inline-block px-2 py-0.5 rounded text-[10px] font-bold bg-indigo-500/15 text-indigo-300 border border-indigo-500/30 font-mono">
                  ENTERPRISE RAG
                </span>
              </div>
              <p className="text-[11px] text-slate-400 font-medium">
                {lang === 'hi'
                  ? 'संयंत्र एआई सहायक एवं सुरक्षा प्रणाली'
                  : lang === 'mr'
                  ? 'कारखाना एआय सहाय्यक व सुरक्षा प्रणाली'
                  : 'Industrial AI Assistant & Knowledge RAG System'}
              </p>
            </div>
          </div>

          {/* Navigation View Tabs */}
          <nav className="hidden md:flex items-center gap-1 bg-slate-900/90 p-1 rounded-xl border border-slate-800">
            <button
              onClick={() => setActiveTab('chat')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'chat'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <MessageSquare className="w-3.5 h-3.5" />
              <span>{getNavTitle('chat')}</span>
            </button>

            <button
              onClick={() => setActiveTab('docs')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'docs'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <Database className="w-3.5 h-3.5" />
              <span>{getNavTitle('docs')}</span>
            </button>

            <button
              onClick={() => setActiveTab('security')}
              className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                activeTab === 'security'
                  ? 'bg-indigo-600 text-white shadow-md shadow-indigo-600/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
              }`}
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              <span>{getNavTitle('security')}</span>
            </button>
          </nav>

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

            {/* Language Switcher */}
            <div className="relative flex items-center">
              <Globe className="w-3.5 h-3.5 text-cyan-400 absolute left-2.5 pointer-events-none z-10" />
              <select
                value={lang}
                onChange={(e) => setLang(e.target.value)}
                className="bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 rounded-xl pl-8 pr-7 py-1.5 text-xs font-semibold transition-all shadow-sm focus:outline-none focus:border-indigo-500 appearance-none cursor-pointer"
                title="Select Language"
              >
                <option value="en">English (EN)</option>
                <option value="hi">हिंदी (HI)</option>
                <option value="mr">मराठी (MR)</option>
              </select>
              <ChevronDown className="w-3 h-3 text-slate-400 absolute right-2.5 pointer-events-none" />
            </div>

          </div>
        </div>

        {/* Mobile Subnav Bar */}
        <div className="flex md:hidden items-center justify-around py-2 border-t border-slate-800/80">
          <button
            onClick={() => setActiveTab('chat')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold ${
              activeTab === 'chat' ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/40' : 'text-slate-400'
            }`}
          >
            <MessageSquare className="w-3.5 h-3.5" />
            <span>Assistant</span>
          </button>

          <button
            onClick={() => setActiveTab('docs')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold ${
              activeTab === 'docs' ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/40' : 'text-slate-400'
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            <span>Knowledge Base</span>
          </button>

          <button
            onClick={() => setActiveTab('security')}
            className={`flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs font-semibold ${
              activeTab === 'security' ? 'bg-indigo-600/30 text-indigo-300 border border-indigo-500/40' : 'text-slate-400'
            }`}
          >
            <ShieldCheck className="w-3.5 h-3.5" />
            <span>Security Matrix</span>
          </button>
        </div>

      </div>
    </header>
  );
}
