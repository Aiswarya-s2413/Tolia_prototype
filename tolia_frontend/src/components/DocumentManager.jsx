import React, { useState, useEffect } from 'react';
import { 
  FileText, 
  Plus, 
  Lock, 
  Unlock, 
  ShieldCheck, 
  Database, 
  RefreshCw, 
  AlertCircle, 
  Search, 
  Filter, 
  X, 
  CheckCircle2, 
  Sparkles,
  Layers,
  BookOpen
} from 'lucide-react';

export default function DocumentManager({ activeRole, lang }) {
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedDeptFilter, setSelectedDeptFilter] = useState('ALL');
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [seedMessage, setSeedMessage] = useState('');
  const [selectedDocDetails, setSelectedDocDetails] = useState(null);

  // New Document Form State
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('GENERAL_SAFETY');
  const [requiredDept, setRequiredDept] = useState('QC');
  const [content, setContent] = useState('');
  const [isConfidential, setIsConfidential] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const fetchDocuments = async () => {
    setIsLoading(true);
    try {
      const res = await fetch(`/api/documents/?role=${activeRole}`);
      if (res.ok) {
        const data = await res.json();
        setDocuments(data);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, [activeRole]);

  const handleSeedData = async () => {
    setIsLoading(true);
    try {
      const res = await fetch('/api/seed/', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setSeedMessage(data.message);
        fetchDocuments();
        setTimeout(() => setSeedMessage(''), 5000);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAddDocument = async (e) => {
    e.preventDefault();
    if (!title.trim() || !content.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      const res = await fetch('/api/documents/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title,
          category,
          required_department: requiredDept,
          content,
          is_confidential: isConfidential
        })
      });

      if (res.ok) {
        setShowUploadModal(false);
        setTitle('');
        setContent('');
        fetchDocuments();
      }
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Filter documents by search and department pill
  const filteredDocs = documents.filter(doc => {
    const matchesSearch = doc.title.toLowerCase().includes(searchQuery.toLowerCase()) || 
                          doc.content.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          doc.category.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesDept = selectedDeptFilter === 'ALL' || doc.required_department === selectedDeptFilter;
    return matchesSearch && matchesDept;
  });

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl p-5 sm:p-6 shadow-2xl min-h-[680px] flex flex-col justify-between backdrop-blur-xl">
      
      <div>
        {/* Knowledge Base Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-6">
          <div>
            <div className="flex items-center gap-2">
              <div className="p-2 rounded-xl bg-indigo-500/20 text-cyan-400 border border-indigo-500/30">
                <Database className="w-5 h-5" />
              </div>
              <h2 className="text-lg font-bold text-slate-100">
                {lang === 'hi' ? 'संयंत्र ज्ञान कोष एवं सुरक्षा टैगिंग' : lang === 'mr' ? 'कारखाना ज्ञानकोश व सुरक्षा टॅगिंग' : 'Plant Knowledge Base & RAG Index'}
              </h2>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              {lang === 'hi'
                ? 'केवल वही दस्तावेज़ प्रदर्शित होंगे जिनके लिए वर्तमान भूमिका अधिकृत है।'
                : lang === 'mr'
                ? 'सध्याच्या भूमिकेनुसार फक्त अधिकृत दस्तऐवजच दिसतील.'
                : 'Indexed SOP documents filtered strictly by authenticated department security policy (RBAC).'}
            </p>
          </div>

          <div className="flex items-center gap-2 self-start md:self-auto">
            {/* Add Document Modal Trigger */}
            <button
              onClick={() => setShowUploadModal(true)}
              className="px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold flex items-center gap-1.5 transition-all shadow-md shadow-indigo-600/30"
            >
              <Plus className="w-4 h-4" />
              <span>{lang === 'hi' ? 'नया दस्तावेज़ जोड़ें' : lang === 'mr' ? 'नवीन दस्तऐवज जोडा' : 'Upload Plant SOP'}</span>
            </button>

            {/* Reseed Data */}
            <button
              onClick={handleSeedData}
              disabled={isLoading}
              className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700/80 text-xs font-semibold flex items-center gap-1.5 transition-all"
              title="Reset database with demo documents"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-cyan-400 ${isLoading ? 'animate-spin' : ''}`} />
              <span className="hidden sm:inline">Reseed DB</span>
            </button>
          </div>
        </div>

        {seedMessage && (
          <div className="mb-4 p-3 rounded-xl bg-emerald-500/15 border border-emerald-500/30 text-emerald-300 text-xs flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{seedMessage}</span>
          </div>
        )}

        {/* Search & Department Filters Bar */}
        <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 mb-6 bg-slate-950/70 p-3 rounded-xl border border-slate-800">
          
          {/* Search Input */}
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search indexed documents by title, category, or content..."
              className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-4 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
            />
            {searchQuery && (
              <button 
                onClick={() => setSearchQuery('')}
                className="absolute right-2.5 top-2 text-slate-400 hover:text-white"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            )}
          </div>

          {/* Department Filter Pills */}
          <div className="flex items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
            <span className="text-[11px] text-slate-400 font-semibold uppercase tracking-wider hidden lg:inline mr-1">Filter:</span>
            {['ALL', 'QC', 'CEO'].map((dept) => (
              <button
                key={dept}
                onClick={() => setSelectedDeptFilter(dept)}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all shrink-0 ${
                  selectedDeptFilter === dept
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'bg-slate-900 text-slate-400 hover:bg-slate-800 border border-slate-800'
                }`}
              >
                {dept === 'ALL' ? 'All Docs' : dept === 'CEO' ? 'CEO / Sales' : 'QC / Ops'}
              </button>
            ))}
          </div>

        </div>

        {/* Document Cards Grid */}
        {isLoading ? (
          <div className="py-20 text-center text-slate-400 text-sm">
            <RefreshCw className="w-8 h-8 animate-spin mx-auto mb-3 text-indigo-400" />
            <span>Fetching indexed vector store...</span>
          </div>
        ) : filteredDocs.length === 0 ? (
          <div className="py-16 text-center bg-slate-950/60 rounded-xl border border-dashed border-slate-800 p-8">
            <AlertCircle className="w-10 h-10 text-slate-500 mx-auto mb-3" />
            <p className="text-slate-200 text-sm font-bold">No Accessible Documents Found</p>
            <p className="text-slate-400 text-xs mt-1 max-w-md mx-auto">
              {activeRole === 'QC' && searchQuery.toLowerCase().includes('sales')
                ? 'Sales documents are restricted under your QC Inspector role.'
                : 'No matching documents found in the local vector index for your current role/search criteria.'}
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredDocs.map((doc) => {
              const isSalesDoc = doc.required_department === 'CEO';

              return (
                <div
                  key={doc.id}
                  onClick={() => setSelectedDocDetails(doc)}
                  className={`group rounded-xl p-4 border transition-all cursor-pointer ${
                    isSalesDoc
                      ? 'bg-indigo-950/20 border-indigo-500/30 hover:border-indigo-500/70 hover:bg-indigo-950/30'
                      : 'bg-slate-950/60 border-slate-800 hover:border-cyan-500/50 hover:bg-slate-900/90'
                  }`}
                >
                  <div className="flex items-start justify-between gap-3 mb-2.5">
                    <div className="flex items-center gap-2.5">
                      <div className={`p-2 rounded-lg ${isSalesDoc ? 'bg-indigo-500/20 text-indigo-400' : 'bg-slate-800 text-cyan-400'}`}>
                        <FileText className="w-4 h-4" />
                      </div>
                      <div>
                        <h3 className="text-sm font-bold text-slate-100 group-hover:text-cyan-300 transition-colors line-clamp-1">
                          {doc.title}
                        </h3>
                        <span className="text-[10px] text-slate-400 uppercase font-mono font-bold">
                          {doc.category}
                        </span>
                      </div>
                    </div>

                    {/* Security Badge */}
                    <span className={`px-2.5 py-1 rounded-md text-[10px] font-extrabold border flex items-center gap-1 shrink-0 ${
                      isSalesDoc 
                        ? 'bg-indigo-500/20 border-indigo-500/40 text-indigo-300' 
                        : 'bg-emerald-500/20 border-emerald-500/40 text-emerald-300'
                    }`}>
                      {isSalesDoc ? <Lock className="w-3 h-3 text-indigo-400" /> : <Unlock className="w-3 h-3 text-emerald-400" />}
                      <span>{doc.required_department}</span>
                    </span>
                  </div>

                  <p className="text-xs text-slate-300 line-clamp-3 bg-slate-900/90 p-3 rounded-lg font-mono border border-slate-800/80 leading-relaxed">
                    {doc.content}
                  </p>

                  <div className="mt-3 flex items-center justify-between text-[11px] text-slate-400 pt-2 border-t border-slate-800/80">
                    <span className="flex items-center gap-1 text-slate-500">
                      <BookOpen className="w-3 h-3" />
                      Click to inspect vector details
                    </span>
                    {doc.is_confidential && (
                      <span className="text-rose-400 font-bold text-[10px] uppercase tracking-wider">
                        🔒 Confidential
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Document Count Footer Info */}
      <div className="mt-6 pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
        <span>Showing <strong className="text-slate-200">{filteredDocs.length}</strong> indexed documents for active role (<strong className="text-indigo-400">{activeRole}</strong>)</span>
        <span className="font-mono text-[11px] text-slate-500">Vector Embeddings: 150 words/chunk</span>
      </div>

      {/* Add Document Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-4 border-b border-slate-800 pb-3">
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <FileText className="w-5 h-5 text-indigo-400" />
                <span>Upload New Plant Document / SOP</span>
              </h3>
              <button 
                onClick={() => setShowUploadModal(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleAddDocument} className="space-y-4 text-xs">
              <div>
                <label className="block font-bold text-slate-300 mb-1">Document Title</label>
                <input
                  type="text"
                  required
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="e.g. Rolling Mill Safety Procedure 2026"
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3.5 py-2.5 text-slate-200 focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-300 mb-1">Category</label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="GENERAL_SAFETY">GENERAL_SAFETY</option>
                    <option value="MAINTENANCE">MAINTENANCE</option>
                    <option value="OPERATIONS">OPERATIONS</option>
                    <option value="CONFIDENTIAL_SALES">CONFIDENTIAL_SALES</option>
                  </select>
                </div>

                <div>
                  <label className="block font-bold text-slate-300 mb-1">Required Department Access</label>
                  <select
                    value={requiredDept}
                    onChange={(e) => setRequiredDept(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2 text-slate-200 focus:outline-none focus:border-indigo-500"
                  >
                    <option value="QC">QC (Quality & Ops)</option>
                    <option value="CEO">CEO (Restricted / Sales)</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-bold text-slate-300 mb-1">Document Full Content</label>
                <textarea
                  required
                  rows={5}
                  value={content}
                  onChange={(e) => setContent(e.target.value)}
                  placeholder="Type or paste the complete SOP text, operating guidelines or machine manual content..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-slate-200 font-mono text-xs focus:outline-none focus:border-indigo-500"
                ></textarea>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="confidential"
                  checked={isConfidential}
                  onChange={(e) => setIsConfidential(e.target.checked)}
                  className="rounded border-slate-700 bg-slate-950 text-indigo-600 focus:ring-indigo-500"
                />
                <label htmlFor="confidential" className="text-slate-300 font-medium cursor-pointer">
                  Mark as Highly Confidential Document
                </label>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 hover:bg-slate-700 font-semibold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold flex items-center gap-2"
                >
                  {isSubmitting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                  <span>Save & Index Document</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Inspect Document Detail Modal */}
      {selectedDocDetails && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-xl w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-cyan-400" />
                <h3 className="text-base font-bold text-slate-100">{selectedDocDetails.title}</h3>
              </div>
              <button 
                onClick={() => setSelectedDocDetails(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="flex items-center gap-3 text-xs">
              <span className="px-2.5 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300 font-mono">
                Category: <strong>{selectedDocDetails.category}</strong>
              </span>
              <span className="px-2.5 py-1 rounded bg-indigo-500/20 border border-indigo-500/30 text-indigo-300 font-mono">
                RBAC Access: <strong>{selectedDocDetails.required_department}</strong>
              </span>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Full Document Text:</label>
              <div className="bg-slate-950 p-4 rounded-xl border border-slate-800 text-xs text-slate-200 font-mono max-h-60 overflow-y-auto whitespace-pre-wrap leading-relaxed">
                {selectedDocDetails.content}
              </div>
            </div>

            <div className="flex items-center justify-end pt-2">
              <button
                onClick={() => setSelectedDocDetails(null)}
                className="px-4 py-2 rounded-xl bg-slate-800 text-slate-200 font-semibold text-xs hover:bg-slate-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
