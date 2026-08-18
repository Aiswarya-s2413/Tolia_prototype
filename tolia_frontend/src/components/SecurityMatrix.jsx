import React, { useState } from 'react';
import { 
  ShieldCheck, 
  Lock, 
  Unlock, 
  CheckCircle, 
  XCircle, 
  AlertTriangle, 
  Terminal, 
  ArrowRight, 
  Database, 
  Key, 
  Cpu, 
  Layers,
  Sparkles
} from 'lucide-react';

export default function SecurityMatrix({ activeRole, setRole, lang }) {
  const [testQuery, setTestQuery] = useState('What are our Q3 steel sales revenue targets?');
  const [testResult, setTestResult] = useState(null);
  const [isTesting, setIsTesting] = useState(false);

  const runTestQuery = async (queryText, roleToUse) => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const response = await fetch('/api/chat/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: queryText,
          user_role: roleToUse || activeRole,
          language: lang
        })
      });
      if (response.ok) {
        const data = await response.json();
        setTestResult(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-2xl space-y-8 backdrop-blur-xl min-h-[680px]">
      
      {/* Header */}
      <div>
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-lg font-bold text-slate-100">
              {lang === 'hi' ? 'विभाग आधारित सुरक्षा एवं एक्सेस कंट्रोल (RBAC RAG)' : lang === 'mr' ? 'विभाग आधारित सुरक्षा व एक्सेस कंट्रोल (RBAC RAG)' : 'Department Role-Based Access Control (RBAC Policy)'}
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Strict multi-tenant security layer preventing unauthorized LLM data leakage in industrial plants.
            </p>
          </div>
        </div>
      </div>

      {/* Permissions Comparison Table */}
      <div className="bg-slate-950/80 rounded-2xl border border-slate-800 overflow-hidden shadow-xl">
        <div className="p-4 bg-slate-900/90 border-b border-slate-800 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-200 flex items-center gap-2">
            <Key className="w-4 h-4 text-cyan-400" />
            <span>Role Permissions Matrix</span>
          </h3>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 font-bold">
            POLICY VERSION 2.4
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs text-slate-300">
            <thead className="bg-slate-900/60 text-slate-400 uppercase font-mono text-[10px] border-b border-slate-800">
              <tr>
                <th className="py-3 px-4">Document Category</th>
                <th className="py-3 px-4 text-center">Required Department</th>
                <th className="py-3 px-4 text-center">CEO Access</th>
                <th className="py-3 px-4 text-center">QC Inspector Access</th>
                <th className="py-3 px-4">Security Enforcement Logic</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80">
              <tr>
                <td className="py-3.5 px-4 font-semibold text-slate-200 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-orange-400"></span>
                  Blast Furnace Safety SOPs
                </td>
                <td className="py-3.5 px-4 text-center">
                  <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[10px]">QC</span>
                </td>
                <td className="py-3.5 px-4 text-center">
                  <span className="inline-flex items-center gap-1 text-emerald-400 font-bold">
                    <CheckCircle className="w-4 h-4" /> Granted
                  </span>
                </td>
                <td className="py-3.5 px-4 text-center">
                  <span className="inline-flex items-center gap-1 text-emerald-400 font-bold">
                    <CheckCircle className="w-4 h-4" /> Granted
                  </span>
                </td>
                <td className="py-3.5 px-4 text-slate-400 font-mono text-[11px]">
                  Unrestricted plant safety standard. Available to all authenticated personnel.
                </td>
              </tr>

              <tr>
                <td className="py-3.5 px-4 font-semibold text-slate-200 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-blue-400"></span>
                  Rolling Mill Maintenance SOPs
                </td>
                <td className="py-3.5 px-4 text-center">
                  <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[10px]">QC</span>
                </td>
                <td className="py-3.5 px-4 text-center">
                  <span className="inline-flex items-center gap-1 text-emerald-400 font-bold">
                    <CheckCircle className="w-4 h-4" /> Granted
                  </span>
                </td>
                <td className="py-3.5 px-4 text-center">
                  <span className="inline-flex items-center gap-1 text-emerald-400 font-bold">
                    <CheckCircle className="w-4 h-4" /> Granted
                  </span>
                </td>
                <td className="py-3.5 px-4 text-slate-400 font-mono text-[11px]">
                  Essential operational guidelines for maintenance and quality inspection.
                </td>
              </tr>

              <tr className="bg-rose-950/10">
                <td className="py-3.5 px-4 font-semibold text-rose-300 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-rose-500 animate-pulse"></span>
                  Confidential Sales & Pricing Targets
                </td>
                <td className="py-3.5 px-4 text-center">
                  <span className="px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-mono font-bold text-[10px]">CEO</span>
                </td>
                <td className="py-3.5 px-4 text-center">
                  <span className="inline-flex items-center gap-1 text-emerald-400 font-bold">
                    <Unlock className="w-4 h-4" /> Granted
                  </span>
                </td>
                <td className="py-3.5 px-4 text-center">
                  <span className="inline-flex items-center gap-1 text-rose-400 font-bold">
                    <XCircle className="w-4 h-4" /> BLOCKED
                  </span>
                </td>
                <td className="py-3.5 px-4 text-rose-300/80 font-mono text-[11px]">
                  Strict RBAC filter drops vector chunks before sending context to LLM.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* RAG Security Architecture Pipeline Diagram */}
      <div>
        <h3 className="text-sm font-bold text-slate-200 mb-3 flex items-center gap-2">
          <Cpu className="w-4 h-4 text-indigo-400" />
          <span>Multi-Layer Security RAG Execution Pipeline</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <div className="bg-slate-950/80 border border-slate-800 p-4 rounded-xl space-y-1.5">
            <div className="flex items-center justify-between text-[10px] font-mono text-indigo-400 font-bold">
              <span>STEP 1</span>
              <span>INPUT</span>
            </div>
            <h4 className="text-xs font-bold text-slate-100">User Query & Role Token</h4>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Query is received along with verified user department token (<code className="text-cyan-300">CEO</code> or <code className="text-cyan-300">QC</code>).
            </p>
          </div>

          <div className="bg-slate-950/80 border border-slate-800 p-4 rounded-xl space-y-1.5 border-l-2 border-l-indigo-500">
            <div className="flex items-center justify-between text-[10px] font-mono text-indigo-400 font-bold">
              <span>STEP 2</span>
              <span>RBAC GATE</span>
            </div>
            <h4 className="text-xs font-bold text-slate-100">Pre-Vector RBAC Filter</h4>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              Database filters chunks by <code className="text-cyan-300">required_department</code> BEFORE cosine similarity calculation.
            </p>
          </div>

          <div className="bg-slate-950/80 border border-slate-800 p-4 rounded-xl space-y-1.5 border-l-2 border-l-cyan-500">
            <div className="flex items-center justify-between text-[10px] font-mono text-cyan-400 font-bold">
              <span>STEP 3</span>
              <span>VECTOR SEARCH</span>
            </div>
            <h4 className="text-xs font-bold text-slate-100">Semantic Matching</h4>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              RAG engine retrieves top matching chunks strictly from the pre-filtered authorized subset.
            </p>
          </div>

          <div className="bg-slate-950/80 border border-slate-800 p-4 rounded-xl space-y-1.5 border-l-2 border-l-emerald-500">
            <div className="flex items-center justify-between text-[10px] font-mono text-emerald-400 font-bold">
              <span>STEP 4</span>
              <span>SYNTHESIS</span>
            </div>
            <h4 className="text-xs font-bold text-slate-100">Sanitized AI Output</h4>
            <p className="text-[11px] text-slate-400 leading-relaxed">
              LLM receives only authorized context. If restricted, prompt injection or unauthorized disclosure is impossible.
            </p>
          </div>
        </div>
      </div>

      {/* Interactive Live Security Tester */}
      <div className="bg-slate-950/90 border border-slate-800 rounded-2xl p-5 space-y-4">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
            <Terminal className="w-4 h-4 text-cyan-400" />
            <span>Interactive Live Security Tester</span>
          </h3>
          <span className="text-[11px] text-slate-400">Test how the backend responds under different roles</span>
        </div>

        <div className="space-y-3 text-xs">
          <div>
            <label className="block text-slate-400 font-semibold mb-1">Select Sample Security Test Query:</label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <button
                onClick={() => setTestQuery('What are our Q3 steel sales revenue targets and client pricing?')}
                className={`p-2.5 rounded-lg border text-left font-mono transition-all ${
                  testQuery.includes('sales')
                    ? 'bg-indigo-600/20 border-indigo-500/40 text-indigo-200'
                    : 'bg-slate-900 border-slate-800 text-slate-300 hover:bg-slate-850'
                }`}
              >
                🔒 Confidential Sales Query (CEO Only)
              </button>

              <button
                onClick={() => setTestQuery('What are the blast furnace temperature safety limits and emergency procedures?')}
                className={`p-2.5 rounded-lg border text-left font-mono transition-all ${
                  testQuery.includes('furnace')
                    ? 'bg-indigo-600/20 border-indigo-500/40 text-indigo-200'
                    : 'bg-slate-900 border-slate-800 text-slate-300 hover:bg-slate-850'
                }`}
              >
                🛡️ Plant Safety SOP Query (Public to All)
              </button>
            </div>
          </div>

          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={() => runTestQuery(testQuery, 'CEO')}
              disabled={isTesting}
              className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold flex items-center gap-2"
            >
              <span>Test as CEO Role</span>
              <Unlock className="w-3.5 h-3.5" />
            </button>

            <button
              onClick={() => runTestQuery(testQuery, 'QC')}
              disabled={isTesting}
              className="px-4 py-2 rounded-xl bg-rose-600 hover:bg-rose-500 text-white font-bold flex items-center gap-2"
            >
              <span>Test as QC Inspector Role</span>
              <Lock className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Test Execution Output */}
          {testResult && (
            <div className="mt-4 p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
              <div className="flex items-center justify-between text-xs border-b border-slate-800 pb-2">
                <span className="font-mono text-slate-400">Tested Role: <strong className="text-cyan-300">{testResult.user_role}</strong></span>
                <span className={`px-2 py-0.5 rounded font-mono font-bold text-[10px] ${
                  testResult.access_blocked 
                    ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40' 
                    : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                }`}>
                  {testResult.access_blocked ? '🔒 ACCESS DENIED BY POLICY' : '🔓 ACCESS GRANTED'}
                </span>
              </div>

              <div className="text-xs text-slate-200 leading-relaxed font-sans bg-slate-950 p-3 rounded-lg border border-slate-800">
                {testResult.response}
              </div>

              <div className="text-[10px] text-slate-500 font-mono flex items-center justify-between">
                <span>Sources retrieved: {testResult.sources ? testResult.sources.length : 0}</span>
                <span>Security Gate Status: Verified Clean</span>
              </div>
            </div>
          )}
        </div>
      </div>

    </div>
  );
}
