import React from 'react';
import { Flame, ShieldAlert, Wrench, DollarSign, Sparkles, Lock, ArrowRight } from 'lucide-react';

const SUGGESTIONS = [
  {
    icon: Flame,
    category: 'SAFETY SOP',
    categoryColor: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    textEn: 'Blast furnace temperature safety guidelines & emergency shutdown procedure',
    textHi: 'ब्लास्ट फर्नेस का तापमान और आपातकालीन सुरक्षा नियम क्या हैं?',
    textMr: 'ब्लास्ट फर्नेसचे तापमान आणि आपत्कालीन सुरक्षा नियम काय आहेत?',
  },
  {
    icon: Wrench,
    category: 'MAINTENANCE',
    categoryColor: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    textEn: 'Rolling Mill gearbox hydraulic pressure & routine maintenance checklist',
    textHi: 'रोलिंग मिल रखरखाव और हाइड्रोलिक दबाव चेकलिस्ट बताएं',
    textMr: 'रोलिंग मिल देखभाल आणि हायड्रोलिक दाब चेकलिस्ट सांगा',
  },
  {
    icon: ShieldAlert,
    category: 'PPE PROTOCOL',
    categoryColor: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    textEn: 'What are the PPE kit requirements for melt shop floor operators?',
    textHi: 'कारखाना परिसर में पीपीई किट पहनना क्यों अनिवार्य है?',
    textMr: 'कारखाना परिसरात पीपीई किट घालणे का अनिवार्य आहे?',
  },
  {
    icon: DollarSign,
    category: 'FINANCIAL TARGETS',
    categoryColor: 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30',
    isSales: true,
    textEn: 'What are our Q3 steel sales revenue targets and wholesale client prices?',
    textHi: 'Q3 स्टील बिक्री लक्ष्य और थोक ग्राहक मूल्य सूची क्या है?',
    textMr: 'Q3 पोलाद विक्री उद्दिष्टे आणि घाऊक ग्राहक दरसूची काय आहे?',
  }
];

export default function QuickPrompts({ onSelectPrompt, lang, activeRole }) {
  return (
    <div className="mb-6">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-bold text-slate-300 uppercase tracking-wider">
            {lang === 'hi' ? 'त्वरित प्रश्न सुझाव' : lang === 'mr' ? 'त्वरित प्रश्न सूचना' : 'Quick Prompt Templates'}
          </span>
        </div>
        <span className="text-[11px] text-slate-400">
          {lang === 'hi' ? 'प्रश्न पर क्लिक करें' : lang === 'mr' ? 'प्रश्नावर क्लिक करा' : 'Click any template to ask'}
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        {SUGGESTIONS.map((item, idx) => {
          const Icon = item.icon;
          const promptText = lang === 'hi' ? item.textHi : lang === 'mr' ? item.textMr : item.textEn;
          const isRestrictedForUser = item.isSales && activeRole !== 'CEO';

          return (
            <button
              key={idx}
              onClick={() => onSelectPrompt(promptText)}
              className={`group flex items-start gap-3 p-3.5 rounded-xl text-left text-xs transition-all border ${
                isRestrictedForUser
                  ? 'bg-rose-950/20 border-rose-500/30 text-slate-200 hover:bg-rose-950/40 hover:border-rose-500/50'
                  : 'bg-slate-900/80 border-slate-800 hover:border-indigo-500/50 hover:bg-slate-800/80 text-slate-200 shadow-sm'
              }`}
            >
              <div className={`p-2 rounded-lg shrink-0 mt-0.5 transition-transform group-hover:scale-105 ${
                item.isSales 
                  ? 'bg-indigo-500/20 text-indigo-400 border border-indigo-500/30' 
                  : 'bg-slate-800 text-cyan-400 border border-slate-700'
              }`}>
                <Icon className="w-4 h-4" />
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase font-mono ${item.categoryColor}`}>
                    {item.category}
                  </span>
                  {item.isSales && (
                    <span className={`text-[10px] font-bold px-1.5 py-0.2 rounded font-mono ${
                      isRestrictedForUser ? 'text-rose-400 bg-rose-500/10' : 'text-emerald-400 bg-emerald-500/10'
                    }`}>
                      {isRestrictedForUser ? '🔒 Sales Restricted' : '🔓 CEO Access'}
                    </span>
                  )}
                </div>

                <p className="line-clamp-2 text-slate-300 group-hover:text-white transition-colors leading-relaxed font-medium">
                  {promptText}
                </p>
              </div>

              <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-indigo-400 group-hover:translate-x-0.5 transition-all shrink-0 self-center" />
            </button>
          );
        })}
      </div>
    </div>
  );
}
