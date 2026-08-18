import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { 
  Send, 
  Mic, 
  MicOff, 
  Volume2, 
  VolumeX, 
  ShieldAlert, 
  FileText, 
  Bot, 
  User, 
  RefreshCw, 
  AudioLines, 
  Copy, 
  Check, 
  Info, 
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Sparkles
} from 'lucide-react';

export default function ChatWindow({ activeRole, lang }) {
  const getInitialWelcomeMessage = (currentLang) => ({
    sender: 'bot',
    text: currentLang === 'hi' 
      ? 'नमस्कार! मैं आपका **कारखाना एआई सहायक** हूँ।\n\nआप मुझसे वॉयस द्वारा या टाइप करके प्रश्न पूछ सकते हैं, जैसे:\n- ब्लास्ट फर्नेस का सुरक्षा तापमान और आपातकालीन नियम\n- रोलिंग मिल गियरबॉक्स हाइड्रोलिक प्रेशर\n- संयंत्र पीपीई किट मानक'
      : currentLang === 'mr'
      ? 'नमस्कार! मी आपला **कारखाना एआय सहाय्यक** आहे.\n\nआपण मला व्हॉईसद्वारे किंवा टाइप करून प्रश्न विचारू शकता, जसे:\n- ब्लास्ट फर्नेसचे सुरक्षा तापमान आणि आपत्कालीन नियम\n- रोलिंग मिल गिअरबॉक्स हायड्रोलिक दाब\n- कारखाना पीपीई किट मानक'
      : 'Hello! I am your **Enterprise AI Industrial Assistant**.\n\nYou can ask questions via speech or text regarding:\n- **Safety SOPs** & emergency blast furnace procedures\n- **Equipment Maintenance** (gearbox hydraulic pressure, lubrication)\n- **Department Security** & RBAC access policies',
    sources: [],
    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  });

  const getLangCode = (l) => (l === 'hi' ? 'hi-IN' : l === 'mr' ? 'mr-IN' : 'en-US');

  const [messages, setMessages] = useState([getInitialWelcomeMessage(lang)]);
  const [inputQuery, setInputQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [autoSpeak, setAutoSpeak] = useState(false);
  const [speakingIndex, setSpeakingIndex] = useState(null);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [expandedSourceIndex, setExpandedSourceIndex] = useState(null);

  const messagesContainerRef = useRef(null);
  const recognitionRef = useRef(null);

  const scrollToBottom = () => {
    if (messagesContainerRef.current) {
      messagesContainerRef.current.scrollTop = messagesContainerRef.current.scrollHeight;
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  useEffect(() => {
    setMessages(prev => {
      if (prev.length === 1 && prev[0].sender === 'bot') {
        return [getInitialWelcomeMessage(lang)];
      }
      return prev;
    });
  }, [lang]);

  // Speech Recognition (STT) setup
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = getLangCode(lang);

      recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        if (transcript.trim()) {
          setInputQuery(transcript);
          setIsListening(false);
          handleSendMessage(transcript);
        }
      };

      recognition.onerror = (err) => {
        console.error('Speech recognition error:', err);
        setIsListening(false);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    }
  }, [lang]);

  const toggleListening = () => {
    if (!recognitionRef.current) {
      alert(
        lang === 'hi'
          ? 'आपका ब्राउज़र वॉयस इनपुट का समर्थन नहीं करता है।'
          : lang === 'mr'
          ? 'तुमचा ब्राउझर व्हॉईस इनपुटला सपोर्ट करत नाही.'
          : 'Speech recognition is not supported in this browser. Please use Chrome or Edge.'
      );
      return;
    }

    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      recognitionRef.current.lang = getLangCode(lang);
      try {
        recognitionRef.current.start();
        setIsListening(true);
      } catch (e) {
        console.error("Speech recognition start failed:", e);
      }
    }
  };

  // Text to Speech (TTS)
  const speakText = (text, index) => {
    if (!('speechSynthesis' in window)) {
      alert('Text-to-speech is not supported in your browser.');
      return;
    }

    if (speakingIndex === index) {
      window.speechSynthesis.cancel();
      setSpeakingIndex(null);
      return;
    }

    window.speechSynthesis.cancel();

    const cleanText = text
      .replace(/[*_#`~]/g, '')
      .replace(/⚠️|💡|📌|▶️|✅/g, '')
      .replace(/\[(.*?)\]\(.*?\)/g, '$1')
      .replace(/https?:\/\/\S+/g, '')
      .trim();

    const utterance = new SpeechSynthesisUtterance(cleanText);
    const langCode = getLangCode(lang);
    utterance.lang = langCode;
    utterance.rate = 0.95;
    utterance.pitch = 1.0;

    const voices = window.speechSynthesis.getVoices();
    const matchingVoice = voices.find(v => v.lang === langCode || v.lang.startsWith(lang));
    if (matchingVoice) {
      utterance.voice = matchingVoice;
    }

    utterance.onend = () => setSpeakingIndex(null);
    utterance.onerror = () => setSpeakingIndex(null);

    setSpeakingIndex(index);
    window.speechSynthesis.speak(utterance);
  };

  const copyToClipboard = (text, index) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const handleSendMessage = async (queryToSend) => {
    const query = (queryToSend || inputQuery).trim();
    if (!query || isLoading) return;

    const userMsg = {
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    setInputQuery('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/chat/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query,
          user_role: activeRole,
          language: lang
        })
      });

      if (!response.ok) {
        throw new Error('API server error');
      }

      const data = await response.json();

      const botMsg = {
        sender: 'bot',
        text: data.response,
        sources: data.sources || [],
        access_blocked: data.access_blocked,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages(prev => {
        const nextMessages = [...prev, botMsg];
        const newMsgIndex = nextMessages.length - 1;

        if (autoSpeak) {
          setTimeout(() => speakText(data.response, newMsgIndex), 300);
        }
        return nextMessages;
      });

    } catch (err) {
      console.error(err);
      setMessages(prev => [
        ...prev,
        {
          sender: 'bot',
          text: lang === 'hi'
            ? '⚠️ सर्वर से कनेक्ट करने में असमर्थ। कृपया जांचें कि बैकएंड सर्वर चल रहा है।'
            : lang === 'mr'
            ? '⚠️ सर्व्हरशी कनेक्ट करण्यात अक्षम. कृपया बॅकएंड सर्व्हर चालू असल्याची खात्री करा.'
            : '⚠️ Unable to connect to backend server. Please verify Django server is running.',
          sources: [],
          access_blocked: false,
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="bg-slate-900/90 border border-slate-800 rounded-2xl shadow-2xl overflow-hidden flex flex-col h-[680px] backdrop-blur-xl">
      
      {/* Console Top Header */}
      <div className="px-5 py-3.5 bg-slate-950/80 border-b border-slate-800 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="relative">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-indigo-500 to-cyan-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
              <Bot className="w-5 h-5" />
            </div>
            <div className="absolute -bottom-0.5 -right-0.5 w-3 h-3 bg-emerald-500 rounded-full border-2 border-slate-950"></div>
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              <span>{lang === 'hi' ? 'एआई कारखाना सहायक' : lang === 'mr' ? 'एआय कारखाना सहाय्यक' : 'AI Assistant'}</span>
              <span className="text-[9px] px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 font-mono border border-indigo-500/30 font-bold">
                LOCAL RAG + STT
              </span>
            </h2>
            <p className="text-[11px] text-slate-400">
              {lang === 'hi' 
                ? 'सुरक्षित RAG उत्तर इंजन' 
                : lang === 'mr' 
                ? 'सुरक्षित RAG उत्तर इंजिन' 
                : 'RBAC-Gated Knowledge Engine'}
            </p>
          </div>
        </div>

        {/* Toolbar Controls */}
        <div className="flex items-center gap-2">
          {/* Voice Auto-Read Toggle */}
          <button
            onClick={() => {
              if (speakingIndex !== null) window.speechSynthesis.cancel();
              setAutoSpeak(!autoSpeak);
            }}
            className={`px-3 py-1.5 rounded-lg border text-xs font-semibold flex items-center gap-1.5 transition-all ${
              autoSpeak
                ? 'bg-cyan-500/20 border-cyan-500/40 text-cyan-300 shadow-sm'
                : 'bg-slate-800/80 border-slate-700 text-slate-400 hover:text-slate-200'
            }`}
            title={lang === 'hi' ? 'स्वचालित आवाज़ उत्तर चालू/बंद करें' : lang === 'mr' ? 'आपोआप आवाजात उत्तर सुरू/बंद करा' : 'Toggle Voice Auto-Speak'}
          >
            <AudioLines className={`w-3.5 h-3.5 ${autoSpeak ? 'text-cyan-400 animate-pulse' : ''}`} />
            <span className="hidden sm:inline">{autoSpeak ? 'Voice Output: ON' : 'Voice Output: OFF'}</span>
          </button>

          {/* Reset History */}
          <button 
            onClick={() => {
              window.speechSynthesis.cancel();
              setSpeakingIndex(null);
              setMessages([getInitialWelcomeMessage(lang)]);
            }}
            className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-all border border-slate-700/60"
            title={lang === 'hi' ? 'संवाद रीसेट करें' : lang === 'mr' ? 'चॅट रिसेट करा' : 'Reset Conversation'}
          >
            <RefreshCw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Message Stream */}
      <div ref={messagesContainerRef} className="flex-1 p-5 overflow-y-auto space-y-4">
        {messages.map((msg, idx) => {
          const isUser = msg.sender === 'user';
          const isSpeaking = speakingIndex === idx;
          const isCopied = copiedIndex === idx;

          return (
            <div
              key={idx}
              className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : ''}`}
            >
              {/* Avatar Icon */}
              <div className={`w-8 h-8 rounded-xl shrink-0 flex items-center justify-center text-xs font-bold shadow-md ${
                isUser 
                  ? 'bg-indigo-600 text-white shadow-indigo-600/30' 
                  : 'bg-slate-800 text-cyan-400 border border-slate-700'
              }`}>
                {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>

              {/* Message Content Bubble */}
              <div className={`max-w-[85%] rounded-2xl p-4 shadow-lg ${
                isUser
                  ? 'bg-gradient-to-r from-indigo-600 to-indigo-700 text-white rounded-tr-none'
                  : msg.access_blocked
                  ? 'bg-rose-950/35 border border-rose-500/40 text-slate-100 rounded-tl-none'
                  : 'bg-slate-800/80 border border-slate-700/70 text-slate-100 rounded-tl-none'
              }`}>

                {/* Security Restriction Banner if blocked */}
                {msg.access_blocked && (
                  <div className="flex items-center gap-2 mb-3 pb-2 border-b border-rose-500/30 text-rose-400 text-xs font-bold">
                    <ShieldAlert className="w-4 h-4 shrink-0" />
                    <span>{lang === 'hi' ? 'सुरक्षा चेतावनी: पहुंच प्रतिबंधित (RBAC Policy)' : lang === 'mr' ? 'सुरक्षा इशारा: डेटा प्रवेश नाकारला (RBAC Policy)' : 'SECURITY RESTRICTION: ACCESS DENIED (RBAC Policy)'}</span>
                  </div>
                )}

                {/* Markdown Formatted Text */}
                <div className="text-xs sm:text-sm leading-relaxed prose prose-invert max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5">
                  <ReactMarkdown>{msg.text}</ReactMarkdown>
                </div>

                {/* Verified Sources Badges */}
                {msg.sources && msg.sources.length > 0 && (
                  <div className="mt-3.5 pt-3 border-t border-slate-700/60">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[11px] text-slate-400 font-bold uppercase tracking-wider flex items-center gap-1.5">
                        <FileText className="w-3.5 h-3.5 text-cyan-400" />
                        {lang === 'hi' ? 'सत्यापित संयंत्र स्रोत:' : lang === 'mr' ? 'सत्यापित स्रोत दस्तऐवज:' : 'Verified Plant Sources:'}
                      </span>
                    </div>

                    <div className="flex flex-wrap gap-1.5">
                      {msg.sources.map((src, sIdx) => {
                        const isExpanded = expandedSourceIndex === `${idx}-${sIdx}`;
                        return (
                          <div key={sIdx} className="w-full">
                            <button
                              onClick={() => setExpandedSourceIndex(isExpanded ? null : `${idx}-${sIdx}`)}
                              className="w-full text-left px-3 py-1.5 rounded-lg bg-slate-950/80 hover:bg-slate-950 border border-slate-700/80 text-[11px] text-cyan-300 flex items-center justify-between gap-2 transition-all"
                            >
                              <div className="flex items-center gap-2 truncate">
                                <span className="w-1.5 h-1.5 rounded-full bg-cyan-400 shrink-0"></span>
                                <span className="font-semibold truncate">{src.doc_title}</span>
                              </div>

                              <div className="flex items-center gap-2 shrink-0">
                                <span className="text-[9px] px-1.5 py-0.5 rounded bg-cyan-500/20 font-mono text-cyan-200 font-bold">
                                  {src.required_department}
                                </span>
                                {isExpanded ? <ChevronUp className="w-3 h-3 text-slate-400" /> : <ChevronDown className="w-3 h-3 text-slate-400" />}
                              </div>
                            </button>

                            {/* Expanded Source Snippet Drawer */}
                            {isExpanded && (
                              <div className="mt-1 p-3 rounded-lg bg-slate-950 border border-cyan-500/30 text-xs text-slate-300 font-mono space-y-1">
                                <div className="text-[10px] text-cyan-400 font-bold uppercase">Source Snippet:</div>
                                <p className="leading-relaxed bg-slate-900 p-2 rounded border border-slate-800 text-slate-300">
                                  "{src.snippet}"
                                </p>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Footer Controls: Audio Listen, Copy & Timestamp */}
                <div className="mt-3 pt-2 flex items-center justify-between text-[11px] text-slate-400 border-t border-slate-700/30">
                  <span>{msg.timestamp}</span>

                  {!isUser && (
                    <div className="flex items-center gap-2">
                      {/* Copy Button */}
                      <button
                        onClick={() => copyToClipboard(msg.text, idx)}
                        className="flex items-center gap-1 px-2 py-1 rounded hover:bg-slate-700/60 text-slate-400 hover:text-slate-200 transition-all text-xs"
                        title="Copy answer"
                      >
                        {isCopied ? (
                          <>
                            <Check className="w-3.5 h-3.5 text-emerald-400" />
                            <span className="text-emerald-400">Copied</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3.5 h-3.5" />
                            <span>Copy</span>
                          </>
                        )}
                      </button>

                      {/* Listen Button */}
                      <button
                        onClick={() => speakText(msg.text, idx)}
                        className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-semibold transition-all ${
                          isSpeaking
                            ? 'bg-cyan-500/30 text-cyan-300 border border-cyan-500/50 shadow-sm'
                            : 'hover:bg-slate-700/60 text-slate-400 hover:text-slate-200'
                        }`}
                        title={lang === 'hi' ? 'आवाज़ में सुनें' : lang === 'mr' ? 'आवाजात ऐका' : 'Listen via Voice Speech'}
                      >
                        {isSpeaking ? (
                          <>
                            <VolumeX className="w-3.5 h-3.5 text-cyan-400" />
                            <div className="flex items-end gap-0.5 h-3">
                              <span className="w-0.5 bg-cyan-400 wave-bar-1"></span>
                              <span className="w-0.5 bg-cyan-400 wave-bar-2"></span>
                              <span className="w-0.5 bg-cyan-400 wave-bar-3"></span>
                            </div>
                            <span>Stop</span>
                          </>
                        ) : (
                          <>
                            <Volume2 className="w-3.5 h-3.5" />
                            <span>Listen</span>
                          </>
                        )}
                      </button>
                    </div>
                  )}
                </div>

              </div>
            </div>
          );
        })}

        {/* Listening Microphone Soundwave Banner */}
        {isListening && (
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-rose-600 text-white flex items-center justify-center animate-pulse">
              <Mic className="w-4 h-4" />
            </div>
            <div className="bg-rose-950/40 border border-rose-500/40 px-4 py-3 rounded-2xl text-xs text-rose-300 flex items-center gap-3">
              <div className="flex items-end gap-1 h-3.5">
                <span className="w-1 bg-rose-400 wave-bar-1"></span>
                <span className="w-1 bg-rose-400 wave-bar-2"></span>
                <span className="w-1 bg-rose-400 wave-bar-3"></span>
              </div>
              <span className="font-semibold">
                {lang === 'hi' 
                  ? 'माइक्रोफ़ोन सक्रिय है... बोलकर प्रश्न पूछें...' 
                  : lang === 'mr' 
                  ? 'मायक्रोफोन सक्रिय आहे... बोलून प्रश्न विचारा...' 
                  : 'Microphone Listening... Speak your query clearly...'}
              </span>
            </div>
          </div>
        )}

        {/* Searching Loading Spinner */}
        {isLoading && (
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-xl bg-slate-800 flex items-center justify-center text-cyan-400 border border-slate-700">
              <Bot className="w-4 h-4 animate-spin" />
            </div>
            <div className="bg-slate-800/90 border border-slate-700/80 px-4 py-3 rounded-2xl text-xs text-slate-300 flex items-center gap-2.5">
              <span className="relative flex h-2.5 w-2.5">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-cyan-500"></span>
              </span>
              <span className="font-medium">
                {lang === 'hi' ? 'RAG विक्टर सर्च और RBAC सुरक्षा सत्यापन प्रगति पर...' : lang === 'mr' ? 'RAG व्हेक्टर शोध व RBAC सुरक्षा पडताळणी सुरु...' : 'RAG Vector Index Search & Security RBAC Check in progress...'}
              </span>
            </div>
          </div>
        )}

      </div>

      {/* Input Bar */}
      <div className="p-4 bg-slate-950/90 border-t border-slate-800">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSendMessage();
          }}
          className="flex items-center gap-2"
        >
          {/* Voice Input STT Button */}
          <button
            type="button"
            onClick={toggleListening}
            className={`p-3 rounded-xl border transition-all shrink-0 ${
              isListening
                ? 'bg-rose-600 text-white border-rose-500 animate-mic-active shadow-lg shadow-rose-600/30'
                : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border-slate-700'
            }`}
            title={lang === 'hi' ? 'माइक दबाकर बोलें' : lang === 'mr' ? 'माईक दाबून बोला' : 'Click to Speak (Speech-to-Text)'}
          >
            {isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5 text-cyan-400" />}
          </button>

          {/* Text Input Field */}
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            placeholder={
              isListening
                ? (lang === 'hi' ? 'सुन रहा हूँ... बोलिए...' : lang === 'mr' ? 'ऐकत आहे... बोला...' : 'Listening... Speak your query now...')
                : (lang === 'hi' ? 'प्रश्न लिखें या माइक दबाकर बोलें...' : lang === 'mr' ? 'प्रश्न लिहा किंवा माईक दाबून बोला...' : 'Ask about plant safety SOPs, gearbox pressure, PPE or sales targets...')
            }
            className="flex-1 bg-slate-900 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/50 shadow-inner"
          />

          {/* Send Button */}
          <button
            type="submit"
            disabled={!inputQuery.trim() || isLoading}
            className="px-5 py-3 rounded-xl bg-gradient-to-r from-indigo-600 to-indigo-700 hover:from-indigo-500 hover:to-indigo-600 text-white font-bold text-xs sm:text-sm transition-all disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-2 shadow-lg shadow-indigo-600/25 shrink-0"
          >
            <span>{lang === 'hi' ? 'पूछें' : lang === 'mr' ? 'विचारा' : 'Ask AI'}</span>
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>

    </div>
  );
}
