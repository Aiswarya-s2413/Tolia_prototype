import React from 'react';
import { ShieldCheck, HardHat, Lock, Unlock, CheckCircle2, UserCheck, AlertOctagon } from 'lucide-react';

const ROLES = [
  {
    id: 'CEO',
    name: 'CEO (Chief Executive)',
    nameHi: 'मुख्य कार्यकारी अधिकारी (CEO)',
    nameMr: 'मुख्य कार्यकारी अधिकारी (CEO)',
    icon: ShieldCheck,
    badgeColor: 'bg-indigo-500/20 border-indigo-500/30 text-indigo-300',
    canSales: true,
    descEn: 'Unrestricted plant access including confidential financial & sales metrics.',
    descHi: 'वित्तीय और बिक्री मीट्रिक सहित सभी डेटा तक पूर्ण पहुंच।',
    descMr: 'सर्व वित्तीय आणि विक्री डेटासह पूर्ण पोहोच.'
  },
  {
    id: 'QC',
    name: 'QC Inspector',
    nameHi: 'गुणवत्ता निरीक्षक (QC Inspector)',
    nameMr: 'गुणवत्ता निरीक्षक (QC Inspector)',
    icon: HardHat,
    badgeColor: 'bg-amber-500/20 border-amber-500/30 text-amber-300',
    canSales: false,
    descEn: 'Authorized for Quality, Ops & Safety SOPs. Restricted from confidential sales data.',
    descHi: 'गुणवत्ता और परिचालन दस्तावेजों तक पहुंच। बिक्री डेटा प्रतिबंधित।',
    descMr: 'गुणवत्ता आणि ऑपरेशन्स दस्तऐवजांपर्यंत पोहोच. विक्री डेटा प्रतिबंधित.'
  }
];

export default function RoleSwitcher({ activeRole, setRole, lang }) {
  const currentRoleObj = ROLES.find(r => r.id === activeRole) || ROLES[0];
  const RoleIcon = currentRoleObj.icon;

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-4 shadow-xl mb-6 backdrop-blur-xl">
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        
        {/* Active Role Status & Permissions */}
        <div className="flex items-start sm:items-center gap-3">
          <div className="p-2.5 rounded-xl bg-slate-800 border border-slate-700/80 text-cyan-400 shrink-0">
            <RoleIcon className="w-5 h-5" />
          </div>

          <div>
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                {lang === 'hi' ? 'सक्रिय उपयोगकर्ता भूमिका:' : lang === 'mr' ? 'सक्रिय वापरकर्ता भूमिका:' : 'Active Role:'}
              </span>

              <span className={`px-2.5 py-0.5 rounded-lg text-xs font-bold border flex items-center gap-1.5 ${currentRoleObj.badgeColor}`}>
                <UserCheck className="w-3.5 h-3.5" />
                <span>{lang === 'hi' ? currentRoleObj.nameHi : lang === 'mr' ? currentRoleObj.nameMr : currentRoleObj.name}</span>
              </span>

              {currentRoleObj.canSales ? (
                <span className="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 flex items-center gap-1">
                  <Unlock className="w-3 h-3" />
                  {lang === 'hi' ? 'बिक्री डेटा अनुमत' : lang === 'mr' ? 'विक्री डेटा अनुमती' : 'Sales Revenue Access Granted'}
                </span>
              ) : (
                <span className="px-2 py-0.5 rounded-md text-[11px] font-semibold bg-rose-500/15 border border-rose-500/30 text-rose-400 flex items-center gap-1">
                  <Lock className="w-3 h-3" />
                  {lang === 'hi' ? 'बिक्री डेटा प्रतिबंधित (RBAC)' : lang === 'mr' ? 'विक्री डेटा प्रतिबंधित (RBAC)' : 'Sales Data Restricted by RBAC'}
                </span>
              )}
            </div>

            <p className="text-xs text-slate-400 mt-1">
              {lang === 'hi' ? currentRoleObj.descHi : lang === 'mr' ? currentRoleObj.descMr : currentRoleObj.descEn}
            </p>
          </div>
        </div>

        {/* Switch Role Controls */}
        <div className="flex items-center gap-2 self-start lg:self-center shrink-0">
          <span className="text-xs text-slate-400 font-medium hidden xl:inline">Switch Role:</span>
          {ROLES.map((r) => {
            const Icon = r.icon;
            const isSelected = activeRole === r.id;
            return (
              <button
                key={r.id}
                onClick={() => setRole(r.id)}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs font-bold transition-all ${
                  isSelected
                    ? 'bg-gradient-to-r from-indigo-600 to-indigo-700 text-white shadow-md shadow-indigo-600/30 ring-1 ring-indigo-400/30'
                    : 'bg-slate-800/90 hover:bg-slate-700/80 text-slate-300 border border-slate-700/70'
                }`}
                title={lang === 'hi' ? r.descHi : lang === 'mr' ? r.descMr : r.descEn}
              >
                <Icon className="w-4 h-4" />
                <span>{r.id === 'CEO' ? 'CEO' : 'QC Inspector'}</span>
                {isSelected && <CheckCircle2 className="w-3.5 h-3.5 text-cyan-300" />}
              </button>
            );
          })}
        </div>

      </div>
    </div>
  );
}
