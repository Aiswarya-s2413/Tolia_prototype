import React, { useState } from 'react';
import Header from './components/Header';
import RoleSwitcher from './components/RoleSwitcher';
import ChatWindow from './components/ChatWindow';
import { ShieldCheck } from 'lucide-react';

export default function App() {
  const [activeRole, setActiveRole] = useState('CEO'); // 'CEO' | 'QC'

  return (
    <div className="min-h-screen bg-[#0b0f17] text-slate-100 flex flex-col font-sans selection:bg-indigo-500 selection:text-white">
      
      {/* Background Ambient Industrial Glow */}
      <div className="fixed top-0 left-1/4 w-[500px] h-[500px] bg-indigo-600/10 rounded-full filter blur-[150px] pointer-events-none"></div>
      <div className="fixed bottom-0 right-1/4 w-[500px] h-[500px] bg-cyan-500/10 rounded-full filter blur-[150px] pointer-events-none"></div>

      {/* Top Application Header */}
      <Header
        activeRole={activeRole}
        setRole={setActiveRole}
      />

      {/* Main Container Viewport - Voice AI Assistant */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 lg:p-8">
        <div className="space-y-6">
          <RoleSwitcher activeRole={activeRole} setRole={setActiveRole} />
          <ChatWindow activeRole={activeRole} />
        </div>
      </main>

      {/* Standard Enterprise Footer */}
      <footer className="mt-12 border-t border-slate-800/90 bg-slate-950/90 py-5 px-6 text-xs text-slate-400 backdrop-blur-xl">
        <div className="max-w-7xl mx-auto flex items-center justify-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
          <span className="font-medium text-slate-300">
            Steel Plant AI Voice RAG System — Protected by Department Security Policy (RBAC)
          </span>
        </div>
      </footer>

    </div>
  );
}
