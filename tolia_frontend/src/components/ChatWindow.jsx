import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { 
  Mic, 
  MicOff, 
  Volume2, 
  VolumeX, 
  Play,
  Pause,
  Square,
  ShieldAlert, 
  FileText, 
  Bot, 
  User, 
  RefreshCw, 
  AudioLines, 
  Copy, 
  Check, 
  Send,
  Sparkles,
  ChevronDown,
  ChevronUp,
  Radio,
  Headphones,
  Sliders
} from 'lucide-react';

export default function ChatWindow({ activeRole, lang }) {
  const getInitialWelcomeMessage = (currentLang) => ({
    sender: 'bot',
    text: currentLang === 'hi' 
      ? 'नमस्कार! मैं आपका **टोलिया वॉयस एआई सहायक** हूँ।\n\nआप माइक पर क्लिक करके अपनी भाषा (**हिंदी, मराठी या अंग्रेजी**) में प्रश्न बोल सकते हैं:\n- *"ब्लास्ट फर्नेस का सुरक्षा तापमान और आपातकालीन नियम क्या हैं?"*\n- *"रोलिंग मिल गियरबॉक्स तेल चेकलिस्ट बताएं"*\n- *"संयंत्र पीपीई किट सुरक्षा मानक क्या हैं?"*'
      : currentLang === 'mr'
      ? 'नमस्कार! मी आपला **टोलिया व्हॉईस एआय सहाय्यक** आहे.\n\nआपण माईकवर क्लिक करून आपल्या भाषेत (**मराठी, हिंदी किंवा इंग्रजी**) प्रश्न विचारू शकता:\n- *"ब्लास्ट फर्नेसचे सुरक्षा तापमान आणि आपत्कालीन नियम काय आहेत?"*\n- *"रोलिंग मिल गिअरबॉक्स ऑइल चेकलिस्ट सांगा"*\n- *"कारखाना पीपीई किट सुरक्षा मानक काय आहेत?"*'
      : 'Hello! I am your **Tolia Voice-First AI Assistant**.\n\nTap the **Microphone** to speak in **English, Hindi, or Marathi** regarding:\n- *"What are the emergency shutdown steps for the Blast Furnace?"*\n- *"Rolling Mill hydraulic pressure and gearbox lubrication SOP"*\n- *"Plant PPE compliance and security guidelines"*',
    sources: [],
    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  });

  const getLangCode = (l) => (l === 'hi' ? 'hi-IN' : l === 'mr' ? 'mr-IN' : 'en-US');

  const [messages, setMessages] = useState([getInitialWelcomeMessage(lang)]);
  const [inputQuery, setInputQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [autoSpeak, setAutoSpeak] = useState(true); // Voice is primary, so default to ON
  const [speakingIndex, setSpeakingIndex] = useState(null);
  const [isVoicePaused, setIsVoicePaused] = useState(false);
  const [activeAudioEngine, setActiveAudioEngine] = useState(null); // 'html5' | 'webspeech' | null
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [expandedSourceIndex, setExpandedSourceIndex] = useState(null);
  const [showTextInput, setShowTextInput] = useState(false);
  const [wsConnected, setWsConnected] = useState(false); // Live WebSocket status

  const messagesContainerRef = useRef(null);
  const recognitionRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const wsRef = useRef(null);
  const currentMsgHandlerRef = useRef(null);

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

  const [liveTranscript, setLiveTranscript] = useState('');
  const silenceTimerRef = useRef(null);

  // Persistent Full-Duplex WebSocket Connection
  useEffect(() => {
    let socket = null;
    let reconnectTimeout = null;
    let isComponentMounted = true;

    const connectWebSocket = () => {
      try {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        // Connect directly to backend port 8000 in dev or relative host in production
        const host = window.location.port === '5173' ? `${window.location.hostname}:8000` : window.location.host;
        const wsUrl = `${protocol}//${host}/ws/chat/`;

        socket = new WebSocket(wsUrl);
        wsRef.current = socket;

        socket.onopen = () => {
          if (!isComponentMounted) return;
          console.log('⚡ Full-Duplex WebSocket Connected to Tolia Backend');
          setWsConnected(true);
        };

        socket.onmessage = (event) => {
          if (!isComponentMounted) return;
          try {
            const data = JSON.parse(event.data);
            if (currentMsgHandlerRef.current) {
              currentMsgHandlerRef.current(data);
            }
          } catch (e) {
            console.warn('WS message parse error:', e);
          }
        };

        socket.onerror = (err) => {
          console.warn('WebSocket status:', err);
          if (isComponentMounted) setWsConnected(false);
        };

        socket.onclose = () => {
          if (isComponentMounted) {
            setWsConnected(false);
            reconnectTimeout = setTimeout(connectWebSocket, 3000);
          }
        };
      } catch (err) {
        console.warn('WebSocket init failed:', err);
        if (isComponentMounted) setWsConnected(false);
      }
    };

    connectWebSocket();

    return () => {
      isComponentMounted = false;
      if (reconnectTimeout) clearTimeout(reconnectTimeout);
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
      }
    };
  }, []);

  // Audio player, utterance, and streaming queue references
  const currentAudioRef = useRef(null);
  const currentUtteranceRef = useRef(null);
  const abortControllerRef = useRef(null);
  const audioQueueRef = useRef([]);
  const isPlayingQueueRef = useRef(false);
  const hasQueuedAudioRef = useRef(false);

  // Speech Recognition (STT) setup with ChatGPT-style Auto-Silence & Interim Streaming
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = true;
      recognition.interimResults = true;
      recognition.lang = getLangCode(lang);

      recognition.onstart = () => {
        setIsListening(true);
        setLiveTranscript('');
      };

      recognition.onresult = (event) => {
        let currentTranscript = '';
        let isFinalChunk = false;

        for (let i = 0; i < event.results.length; ++i) {
          currentTranscript += event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            isFinalChunk = true;
          }
        }

        if (currentTranscript.trim()) {
          setLiveTranscript(currentTranscript);
          setInputQuery(currentTranscript);

          // ChatGPT-style Auto-Silence: automatically submit after 1.4s of quiet
          if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
          silenceTimerRef.current = setTimeout(() => {
            if (currentTranscript.trim()) {
              try { recognition.stop(); } catch(e) {}
              setIsListening(false);
              setLiveTranscript('');
              handleSendMessage(currentTranscript.trim());
            }
          }, 1400);
        }
      };

      recognition.onerror = (err) => {
        console.warn('Speech recognition notice:', err.error);
        if (err.error !== 'no-speech') {
          setIsListening(false);
        }
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    }
  }, [lang]);

  const startMediaRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioChunksRef.current = [];
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        const formData = new FormData();
        formData.append('audio', audioBlob, 'audio.webm');
        formData.append('language', lang);

        try {
          const res = await fetch('/api/voice/transcribe/', {
            method: 'POST',
            body: formData,
          });
          const data = await res.json();
          if (data && data.text && data.text.trim()) {
            setInputQuery(data.text);
            handleSendMessage(data.text.trim());
          }
        } catch (err) {
          console.error('VEXYL-STT transcription error:', err);
        }
      };

      mediaRecorder.start();
      setIsListening(true);
      setLiveTranscript(lang === 'hi' ? 'बोलिए...' : lang === 'mr' ? 'बोला...' : 'Listening...');
    } catch (err) {
      console.error('Microphone access denied:', err);
    }
  };

  const stopMediaRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
      if (mediaRecorderRef.current.stream) {
        mediaRecorderRef.current.stream.getTracks().forEach((track) => track.stop());
      }
    }
    setIsListening(false);
    setLiveTranscript('');
  };

  // Fluid Voice Toggle & Barge-In (Tap to Speak / Tap to Interrupt)
  const toggleListening = () => {
    unlockAudioContext();
    // 1. If bot is speaking, tap instantly interrupts AI and starts listening
    const isBotSpeaking = isPlayingQueueRef.current || (currentAudioRef.current && !currentAudioRef.current.paused) || (window.speechSynthesis && window.speechSynthesis.speaking) || speakingIndex !== null;
    if (isBotSpeaking) {
      stopVoice();
    }

    if (isListening) {
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      if (recognitionRef.current) {
        try { recognitionRef.current.stop(); } catch(e) {}
      }
      stopMediaRecording();
      setIsListening(false);
      if (inputQuery.trim()) {
        handleSendMessage(inputQuery.trim());
      }
    } else {
      stopVoice();
      if (recognitionRef.current) {
        try {
          recognitionRef.current.lang = getLangCode(lang);
          recognitionRef.current.start();
          setIsListening(true);
          setLiveTranscript('');
        } catch (e) {
          console.warn("Speech recognition restart, activating VEXYL-STT backup:", e);
          startMediaRecording();
        }
      } else {
        startMediaRecording();
      }
    }
  };

  // Preload speech synthesis voices
  const [availableVoices, setAvailableVoices] = useState([]);
  useEffect(() => {
    if ('speechSynthesis' in window) {
      const updateVoices = () => {
        const v = window.speechSynthesis.getVoices();
        if (v && v.length > 0) setAvailableVoices(v);
      };
      updateVoices();
      window.speechSynthesis.onvoiceschanged = updateVoices;
    }
  }, []);

  // Pre-unlock audio permission on user interaction for smooth mobile & desktop playback
  const unlockAudioContext = () => {
    try {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (AudioCtx) {
        if (!window._sharedAudioCtx) {
          window._sharedAudioCtx = new AudioCtx();
        }
        if (window._sharedAudioCtx.state === 'suspended') {
          window._sharedAudioCtx.resume();
        }
      }
      if (!window._audioUnlocked) {
        const dummyAudio = new Audio('data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA');
        dummyAudio.play().then(() => {
          dummyAudio.pause();
          window._audioUnlocked = true;
        }).catch(() => {});
      }
    } catch (e) {}
  };

  // Stop all active voice audio and cancel streaming (Zero-Latency Barge-In)
  const stopVoice = () => {
    // 1. Send instant cancel frame over WebSocket to halt backend RAG/LLM immediately
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      try {
        wsRef.current.send(JSON.stringify({ action: 'cancel' }));
      } catch (e) {}
    }

    // 2. Abort in-flight SSE stream
    if (abortControllerRef.current) {
      try { abortControllerRef.current.abort(); } catch (e) {}
      abortControllerRef.current = null;
    }

    // 3. Stop and clear active HTML5 audio
    if (currentAudioRef.current) {
      try {
        currentAudioRef.current.pause();
        currentAudioRef.current.onended = null;
        currentAudioRef.current.onerror = null;
        currentAudioRef.current.onplay = null;
        currentAudioRef.current.src = '';
      } catch (e) {}
      currentAudioRef.current = null;
    }

    // 4. Clear sentence audio queue
    audioQueueRef.current.forEach((item) => {
      if (item.audio) {
        try {
          item.audio.pause();
          item.audio.onended = null;
          item.audio.onerror = null;
          item.audio.onplay = null;
          item.audio.src = '';
        } catch (e) {}
      }
    });
    audioQueueRef.current = [];
    isPlayingQueueRef.current = false;
    hasQueuedAudioRef.current = false;

    // 5. Cancel Web Speech
    if ('speechSynthesis' in window) {
      try {
        window.speechSynthesis.cancel();
      } catch (e) {}
    }

    setSpeakingIndex(null);
    setIsVoicePaused(false);
    setActiveAudioEngine(null);
  };

  // Play next audio sentence in queue (Gapless Voice Pipelining)
  const playNextInQueue = (msgIndex) => {
    const targetIdx = msgIndex !== undefined && msgIndex !== null ? msgIndex : getLatestBotMessageIndex();

    if (audioQueueRef.current.length === 0) {
      isPlayingQueueRef.current = false;
      setActiveAudioEngine(null);
      setSpeakingIndex(null);
      return;
    }

    // Ensure zero overlap with any lingering speech synthesis
    if ('speechSynthesis' in window) {
      try { window.speechSynthesis.cancel(); } catch (e) {}
    }

    isPlayingQueueRef.current = true;
    const nextItem = audioQueueRef.current.shift();
    if (!nextItem || !nextItem.audio) {
      playNextInQueue(targetIdx);
      return;
    }

    const audio = nextItem.audio;
    currentAudioRef.current = audio;

    audio.onplay = () => {
      setActiveAudioEngine('html5');
      setSpeakingIndex(targetIdx);
      setIsVoicePaused(false);
      // Gapless pre-buffering: start downloading next audio sentence immediately while current one is playing
      if (audioQueueRef.current.length > 0 && audioQueueRef.current[0]?.audio) {
        try {
          audioQueueRef.current[0].audio.load();
        } catch (e) {}
      }
    };

    audio.onended = () => {
      playNextInQueue(targetIdx);
    };

    audio.onerror = (e) => {
      console.warn("HTML5 audio playback error on chunk:", e);
      playNextInQueue(targetIdx);
    };

    const playPromise = audio.play();
    if (playPromise !== undefined) {
      playPromise.catch((err) => {
        if (err.name !== 'AbortError') {
          console.warn("Audio play rejected, recovering queue:", err);
          playNextInQueue(targetIdx);
        }
      });
    }
  };

  // Queue sentence chunks for sub-second TTS playback
  const queueSentenceForTTS = (sentenceText, msgIndex) => {
    const cleanText = sentenceText
      .replace(/[*_#`~]/g, '')
      .replace(/⚠️|💡|📌|▶️|✅|🛡️|🏢|👥|📋|📜/g, '')
      .replace(/\[(.*?)\]\(.*?\)/g, '$1')
      .replace(/https?:\/\/\S+/g, '')
      .trim();

    // Ignore tiny fragments (e.g. single numbers or symbols) to prevent fragmented audio gaps
    if (!cleanText || cleanText.length < 8) return;

    const targetIdx = msgIndex !== undefined && msgIndex !== null ? msgIndex : getLatestBotMessageIndex();
    const audioUrl = `/api/voice/synthesize/?text=${encodeURIComponent(cleanText)}&lang=${encodeURIComponent(lang)}`;
    const audio = new Audio(audioUrl);
    audio.preload = 'auto';

    audioQueueRef.current.push({ text: cleanText, audio: audio });

    if (!isPlayingQueueRef.current) {
      playNextInQueue(targetIdx);
    }
  };

  // Pause active voice audio
  const pauseVoice = () => {
    if (activeAudioEngine === 'html5' && currentAudioRef.current) {
      currentAudioRef.current.pause();
      setIsVoicePaused(true);
    } else if ('speechSynthesis' in window && window.speechSynthesis.speaking) {
      window.speechSynthesis.pause();
      setIsVoicePaused(true);
    }
  };

  // Resume paused voice audio
  const resumeVoice = () => {
    if (activeAudioEngine === 'html5' && currentAudioRef.current) {
      currentAudioRef.current.play().catch((err) => {
        console.warn("Resume audio playback failed:", err);
      });
      setIsVoicePaused(false);
    } else if ('speechSynthesis' in window && (window.speechSynthesis.paused || isVoicePaused)) {
      window.speechSynthesis.resume();
      setIsVoicePaused(false);
    }
  };

  // Get latest bot response index
  const getLatestBotMessageIndex = () => {
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].sender === 'bot') return i;
    }
    return -1;
  };

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopVoice();
    };
  }, []);

  // Text to Speech (TTS) - For manual replay or full playback
  const speakText = (text, index) => {
    stopVoice();

    const cleanText = text
      .replace(/[*_#`~]/g, '')
      .replace(/⚠️|💡|📌|▶️|✅|🛡️|🏢|👥|📋|📜/g, '')
      .replace(/\[(.*?)\]\(.*?\)/g, '$1')
      .replace(/https?:\/\/\S+/g, '')
      .trim();

    if (!cleanText) {
      stopVoice();
      return;
    }

    const targetIdx = index !== undefined && index !== null && index >= 0 ? index : getLatestBotMessageIndex();

    // High-Speed Backend Voice (/api/voice/synthesize/)
    const audioUrl = `/api/voice/synthesize/?text=${encodeURIComponent(cleanText)}&lang=${encodeURIComponent(lang)}`;
    const audio = new Audio(audioUrl);
    currentAudioRef.current = audio;

    audio.onplay = () => {
      setActiveAudioEngine('html5');
      setSpeakingIndex(targetIdx);
      setIsVoicePaused(false);
    };

    audio.onended = () => {
      stopVoice();
    };

    audio.onerror = () => {
      console.warn("Backend audio error");
      stopVoice();
    };

    const playPromise = audio.play();
    if (playPromise !== undefined) {
      playPromise.catch((err) => {
        if (err.name !== 'AbortError') {
          console.warn("Audio play rejected:", err);
        }
        stopVoice();
      });
    }
  };

  const copyToClipboard = (text, index) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  // Zero-Latency Streaming + Pipelined Voice Message Handler
  const handleSendMessage = async (queryToSend) => {
    const query = (queryToSend || inputQuery).trim();
    if (!query || isLoading) return;

    // Zero-Latency Barge-In: immediately cut off any playing speech
    unlockAudioContext();
    stopVoice();
    hasQueuedAudioRef.current = false;

    const botMsgId = 'bot_' + Date.now() + '_' + Math.floor(Math.random() * 10000);
    const userMsg = {
      id: 'usr_' + Date.now(),
      sender: 'user',
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    const initialBotMsg = {
      id: botMsgId,
      sender: 'bot',
      text: '',
      sources: [],
      access_blocked: false,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      isStreaming: true
    };

    setMessages(prev => [...prev, userMsg, initialBotMsg]);
    setInputQuery('');
    setIsLoading(true);

    // -------------------------------------------------------------------------
    // High-Speed Direct Token & Voice Sentence Stream (SSE)
    // -------------------------------------------------------------------------
    const abortController = new AbortController();
    abortControllerRef.current = abortController;

    try {
      const response = await fetch('/api/chat/stream/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query,
          user_role: activeRole,
          language: lang
        }),
        signal: abortController.signal
      });

      if (!response.ok) {
        throw new Error('Streaming API server error');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder('utf-8');
      let buffer = '';
      let accumulatedText = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          const trimmed = line.trim();
          if (trimmed.startsWith('data: ')) {
            try {
              const data = JSON.parse(trimmed.slice(6));

              if (data.type === 'meta') {
                setMessages(prev => prev.map(m => m.id === botMsgId ? {
                  ...m,
                  sources: data.sources || [],
                  access_blocked: data.access_blocked || false
                } : m));
              } else if (data.type === 'token') {
                accumulatedText += data.token;
                setMessages(prev => prev.map(m => m.id === botMsgId ? {
                  ...m,
                  text: accumulatedText
                } : m));
              } else if (data.type === 'sentence') {
                if (autoSpeak && data.text) {
                  hasQueuedAudioRef.current = true;
                  const currentIdx = getLatestBotMessageIndex();
                  queueSentenceForTTS(data.text, currentIdx >= 0 ? currentIdx : 1);
                }
              } else if (data.type === 'done') {
                setMessages(prev => prev.map(m => m.id === botMsgId ? {
                  ...m,
                  isStreaming: false
                } : m));
                // Fallback ONLY if no sentence audio was queued at all during streaming
                if (autoSpeak && !hasQueuedAudioRef.current && accumulatedText) {
                  const currentIdx = getLatestBotMessageIndex();
                  speakText(accumulatedText, currentIdx >= 0 ? currentIdx : 1);
                }
              }
            } catch (err) {
              console.warn('SSE parse error:', err);
            }
          }
        }
      }

    } catch (err) {
      if (err.name === 'AbortError') {
        return;
      }
      console.error('Streaming error:', err);
      setMessages(prev => prev.map(m => m.id === botMsgId ? {
        ...m,
        text: m.text || (
          lang === 'hi'
            ? '⚠️ सर्वर से कनेक्ट करने में असमर्थ। कृपया जांचें कि बैकएंड सर्वर चल रहा है।'
            : lang === 'mr'
            ? '⚠️ सर्व्हरशी कनेक्ट करण्यात अक्षम. कृपया बॅकएंड सर्व्हर चालू असल्याची खात्री करा.'
            : '⚠️ Unable to connect to backend server. Please verify Django server is running.'
        ),
        isStreaming: false
      } : m));
    } finally {
      setIsLoading(false);
    }
  };

  const sampleVoicePrompts = lang === 'hi' ? [
    'ब्लास्ट फर्नेस आपातकालीन सुरक्षा नियम क्या हैं?',
    'रोलिंग मिल गियरबॉक्स हाइड्रोलिक प्रेशर कितना होना चाहिए?',
    'संयंत्र में अनिवार्य पीपीई किट नियम क्या हैं?',
    'Q1 वित्तीय एवं बिक्री लक्ष्य क्या है?'
  ] : lang === 'mr' ? [
    'ब्लास्ट फर्नेस आपत्कालीन सुरक्षा नियम काय आहेत?',
    'रोलिंग मिल गिअरबॉक्स हायड्रोलिक दाब किती असावा?',
    'कारखान्यातील अनिवार्य पीपीई किट नियम काय आहेत?',
    'Q1 विक्री आणि आर्थिक टार्गेट काय आहे?'
  ] : [
    'What are the emergency shutdown steps for Blast Furnace?',
    'What is the standard hydraulic pressure for Rolling Mill?',
    'What are the plant PPE safety requirements?',
    'What are our Q1 confidential sales and revenue targets?'
  ];

  return (
    <div className="space-y-6">
      
      {/* ========================================================================= */}
      {/* HERO VOICE ORB & INTERACTIVE CONTROLLER (MAIN HERO VIEW) */}
      {/* ========================================================================= */}
      <div className="relative overflow-hidden rounded-3xl bg-gradient-to-b from-slate-900 via-slate-900/95 to-slate-950 border border-slate-800/90 shadow-2xl p-6 sm:p-8 backdrop-blur-2xl">
        
        {/* Ambient Industrial Energy Ring */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-indigo-500/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-cyan-500/10 rounded-full blur-2xl pointer-events-none"></div>

        <div className="relative flex flex-col items-center text-center max-w-2xl mx-auto space-y-6">
          
          {/* Top Status Pill */}
          <div className="flex flex-wrap items-center justify-center gap-2">
            <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-slate-800/80 border border-slate-700/70 text-xs font-semibold">
              <span className="relative flex h-2.5 w-2.5">
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${isListening ? 'bg-rose-400' : speakingIndex !== null ? 'bg-cyan-400' : 'bg-emerald-400'} opacity-75`}></span>
                <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${isListening ? 'bg-rose-500' : speakingIndex !== null ? 'bg-cyan-500' : 'bg-emerald-500'}`}></span>
              </span>
              <span className="text-slate-300 font-mono">
                {isListening 
                  ? (lang === 'hi' ? 'माइक्रोफ़ोन सक्रिय: आवाज़ सुन रहा हूँ...' : lang === 'mr' ? 'मायक्रोफोन सक्रिय: ऐकत आहे...' : 'Listening to Speech...') 
                  : speakingIndex !== null 
                  ? (lang === 'hi' ? 'एआई वॉयस बोल रहा है...' : lang === 'mr' ? 'एआय व्हॉईस बोलत आहे...' : 'AI Speaking Response...')
                  : isLoading
                  ? (lang === 'hi' ? 'RAG खोज एवं विश्लेषण जारी...' : lang === 'mr' ? 'RAG शोध व विश्लेषण सुरु...' : 'RAG Vector Index Query...')
                  : (lang === 'hi' ? 'वॉयस मोड तैयार — बोलकर प्रश्न पूछें' : lang === 'mr' ? 'व्हॉईस मोड तयार — बोलून प्रश्न विचारा' : 'Voice Mode Ready — Tap & Speak')}
              </span>
            </div>
          </div>

          {/* Central Pulsing AI Voice Orb */}
          <div className="relative flex items-center justify-center">
            
            {/* Outer Dynamic Sound Ring */}
            <div className={`absolute w-36 h-36 rounded-full border border-dashed transition-all duration-700 ${
              isListening
                ? 'border-rose-500/60 scale-125 animate-spin'
                : speakingIndex !== null
                ? 'border-cyan-400/60 scale-115 animate-spin'
                : 'border-slate-700/40 scale-100'
            }`}></div>

            {/* Glowing Orb Action Button */}
            <button
              onClick={toggleListening}
              className={`relative z-10 w-28 h-28 rounded-full flex flex-col items-center justify-center transition-all duration-300 transform active:scale-95 shadow-2xl ${
                isListening
                  ? 'bg-gradient-to-tr from-rose-600 to-rose-500 text-white animate-mic-active shadow-rose-600/40 ring-4 ring-rose-400/30'
                  : speakingIndex !== null
                  ? 'bg-gradient-to-tr from-cyan-600 via-indigo-600 to-cyan-500 text-white animate-orb-speaking shadow-cyan-500/40 ring-4 ring-cyan-400/30'
                  : 'bg-gradient-to-tr from-indigo-600 via-indigo-700 to-cyan-600 hover:from-indigo-500 hover:to-cyan-500 text-white animate-orb-idle shadow-indigo-600/30 ring-4 ring-indigo-500/20'
              }`}
              title="Click to Speak / Stop"
            >
              {isListening ? (
                <>
                  <MicOff className="w-9 h-9" />
                  <span className="text-[10px] font-bold mt-1 uppercase tracking-wider">Stop</span>
                </>
              ) : speakingIndex !== null ? (
                <>
                  <Volume2 className="w-9 h-9 animate-pulse" />
                  <span className="text-[10px] font-bold mt-1 uppercase tracking-wider">Speaking</span>
                </>
              ) : (
                <>
                  <Mic className="w-9 h-9 text-white drop-shadow-md" />
                  <span className="text-[10px] font-extrabold mt-1 tracking-wider uppercase">Tap & Speak</span>
                </>
              )}
            </button>
          </div>

          {/* Dynamic Audio Equalizer Bars */}
          <div className="flex items-center justify-center gap-1.5 h-8">
            <span className={`w-1.5 rounded-full transition-all duration-200 ${isListening ? 'bg-rose-400 wave-bar-1' : speakingIndex !== null ? 'bg-cyan-400 wave-bar-1' : 'h-1.5 bg-slate-700'}`}></span>
            <span className={`w-1.5 rounded-full transition-all duration-200 ${isListening ? 'bg-rose-400 wave-bar-2' : speakingIndex !== null ? 'bg-cyan-400 wave-bar-2' : 'h-1.5 bg-slate-700'}`}></span>
            <span className={`w-1.5 rounded-full transition-all duration-200 ${isListening ? 'bg-rose-400 wave-bar-3' : speakingIndex !== null ? 'bg-cyan-400 wave-bar-3' : 'h-1.5 bg-slate-700'}`}></span>
            <span className={`w-1.5 rounded-full transition-all duration-200 ${isListening ? 'bg-rose-400 wave-bar-4' : speakingIndex !== null ? 'bg-cyan-400 wave-bar-4' : 'h-1.5 bg-slate-700'}`}></span>
            <span className={`w-1.5 rounded-full transition-all duration-200 ${isListening ? 'bg-rose-400 wave-bar-5' : speakingIndex !== null ? 'bg-cyan-400 wave-bar-5' : 'h-1.5 bg-slate-700'}`}></span>
            <span className={`w-1.5 rounded-full transition-all duration-200 ${isListening ? 'bg-rose-400 wave-bar-6' : speakingIndex !== null ? 'bg-cyan-400 wave-bar-6' : 'h-1.5 bg-slate-700'}`}></span>
          </div>

          {/* Main Voice Audio Controls Bar (Play, Pause, Resume, Stop) */}
          <div className="flex flex-wrap items-center justify-center gap-2.5 p-2 bg-slate-950/80 border border-cyan-500/30 rounded-2xl shadow-lg backdrop-blur-md">
            {/* Play Button */}
            <button
              onClick={() => {
                if (speakingIndex !== null && isVoicePaused) {
                  resumeVoice();
                } else {
                  const idx = getLatestBotMessageIndex();
                  if (idx >= 0) speakText(messages[idx].text, idx);
                }
              }}
              disabled={isLoading || getLatestBotMessageIndex() === -1}
              className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold transition-all shadow-sm ${
                speakingIndex !== null && !isVoicePaused
                  ? 'bg-cyan-600/30 text-cyan-300 border border-cyan-500/50'
                  : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 hover:border-cyan-500/40 disabled:opacity-40 disabled:hover:bg-slate-800'
              }`}
              title="Play AI Voice Response"
            >
              <Play className="w-3.5 h-3.5 fill-current text-cyan-400" />
              <span>{lang === 'hi' ? 'प्ले' : lang === 'mr' ? 'प्ले' : 'Play'}</span>
            </button>

            {/* Pause Button */}
            <button
              onClick={pauseVoice}
              disabled={speakingIndex === null || isVoicePaused}
              className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold transition-all shadow-sm ${
                speakingIndex !== null && !isVoicePaused
                  ? 'bg-amber-600 hover:bg-amber-500 text-white shadow-amber-600/30 border border-amber-500'
                  : 'bg-slate-800 text-slate-500 border border-slate-800/80 cursor-not-allowed opacity-40'
              }`}
              title="Pause Voice Audio"
            >
              <Pause className="w-3.5 h-3.5 fill-current" />
              <span>{lang === 'hi' ? 'रोकें' : lang === 'mr' ? 'थांबवा' : 'Pause'}</span>
            </button>

            {/* Resume Button */}
            <button
              onClick={resumeVoice}
              disabled={speakingIndex === null || !isVoicePaused}
              className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold transition-all shadow-sm ${
                speakingIndex !== null && isVoicePaused
                  ? 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/30 border border-emerald-500 animate-pulse'
                  : 'bg-slate-800 text-slate-500 border border-slate-800/80 cursor-not-allowed opacity-40'
              }`}
              title="Resume Voice Audio"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>{lang === 'hi' ? 'पुनः चालू' : lang === 'mr' ? 'पुढे सुरू' : 'Resume'}</span>
            </button>

            {/* Stop Button */}
            <button
              onClick={stopVoice}
              disabled={speakingIndex === null}
              className={`flex items-center gap-1.5 px-3.5 py-2 rounded-xl text-xs font-bold transition-all shadow-sm ${
                speakingIndex !== null
                  ? 'bg-rose-600/90 hover:bg-rose-600 text-white shadow-rose-600/30 border border-rose-500'
                  : 'bg-slate-800 text-slate-500 border border-slate-800/80 cursor-not-allowed opacity-40'
              }`}
              title="Stop Voice Audio"
            >
              <Square className="w-3.5 h-3.5 fill-current" />
              <span>{lang === 'hi' ? 'बंद करें' : lang === 'mr' ? 'बंद करा' : 'Stop'}</span>
            </button>
          </div>

          {/* Live Speech Recognition Transcript Box */}
          {isListening && (
            <div className="w-full bg-rose-950/40 border border-rose-500/50 rounded-2xl p-4 text-center animate-pulse">
              <div className="text-[11px] font-bold text-rose-400 uppercase tracking-wider mb-1 flex items-center justify-center gap-1.5">
                <Mic className="w-3.5 h-3.5 animate-ping" />
                <span>{lang === 'hi' ? 'आपकी आवाज़ सुनी जा रही है...' : lang === 'mr' ? 'आपला आवाज ऐकला जात आहे...' : 'Listening to your speech (auto-submits on pause)...'}</span>
              </div>
              <p className="text-sm font-semibold text-slate-100 italic">
                {liveTranscript || (lang === 'hi' ? 'बोलना शुरू करें...' : lang === 'mr' ? 'बोलायला सुरुवात करा...' : 'Speak now...')}
              </p>
            </div>
          )}

          {/* Quick Voice Chips */}
          <div className="w-full space-y-2">
            <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider flex items-center justify-center gap-1.5">
              <Headphones className="w-3.5 h-3.5 text-cyan-400" />
              <span>{lang === 'hi' ? 'सुझाए गए वॉयस प्रश्न (Tap to Ask):' : lang === 'mr' ? 'सुचवलेले व्हॉईस प्रश्न (Tap to Ask):' : 'Suggested Voice Queries (Tap to Ask):'}</span>
            </div>

            <div className="flex flex-wrap justify-center gap-2">
              {sampleVoicePrompts.map((prompt, pIdx) => (
                <button
                  key={pIdx}
                  onClick={() => handleSendMessage(prompt)}
                  disabled={isLoading}
                  className="px-3.5 py-1.5 rounded-xl bg-slate-800/80 hover:bg-slate-800 border border-slate-700/80 hover:border-cyan-500/40 text-xs text-slate-300 hover:text-cyan-200 font-medium transition-all shadow-sm flex items-center gap-2 group text-left"
                >
                  <Radio className="w-3 h-3 text-cyan-400 group-hover:animate-ping shrink-0" />
                  <span className="truncate max-w-xs">{prompt}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Voice Toolbar: Auto-Speak + Text Input Drawer Toggle */}
          <div className="flex items-center justify-between w-full pt-4 border-t border-slate-800/80 text-xs">
            
            {/* Auto-Voice Output Switch */}
            <button
              onClick={() => {
                if (speakingIndex !== null) stopVoice();
                setAutoSpeak(!autoSpeak);
              }}
              className={`px-3 py-1.5 rounded-lg border flex items-center gap-1.5 font-semibold transition-all ${
                autoSpeak
                  ? 'bg-cyan-500/20 border-cyan-500/40 text-cyan-300'
                  : 'bg-slate-800 border-slate-700 text-slate-400'
              }`}
            >
              <AudioLines className={`w-3.5 h-3.5 ${autoSpeak ? 'text-cyan-400 animate-pulse' : ''}`} />
              <span>{autoSpeak ? 'Auto Voice Playback: ON' : 'Auto Voice Playback: OFF'}</span>
            </button>

            {/* Toggle Manual Text Input Option */}
            <button
              onClick={() => setShowTextInput(!showTextInput)}
              className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 flex items-center gap-1.5 font-medium transition-all"
            >
              <span>{showTextInput ? 'Hide Text Bar' : 'Type Question Instead'}</span>
              {showTextInput ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>

          </div>

          {/* Collapsible Secondary Text Input */}
          {showTextInput && (
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSendMessage();
              }}
              className="w-full flex items-center gap-2 pt-2"
            >
              <input
                type="text"
                value={inputQuery}
                onChange={(e) => setInputQuery(e.target.value)}
                placeholder={lang === 'hi' ? 'वैकल्पिक रूप से प्रश्न टाइप करें...' : lang === 'mr' ? 'पर्यायी प्रश्न टाईप करा...' : 'Optionally type your question here...'}
                className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-xs sm:text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
              <button
                type="submit"
                disabled={!inputQuery.trim() || isLoading}
                className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs flex items-center gap-1.5 disabled:opacity-40"
              >
                <span>Send</span>
                <Send className="w-3.5 h-3.5" />
              </button>
            </form>
          )}

        </div>
      </div>

      {/* ========================================================================= */}
      {/* CONVERSATION TRANSCRIPT & AUDIO HISTORY FEED */}
      {/* ========================================================================= */}
      <div className="bg-slate-900/90 border border-slate-800 rounded-2xl shadow-xl overflow-hidden flex flex-col backdrop-blur-xl">
        
        {/* Header Bar */}
        <div className="px-5 py-3.5 bg-slate-950/80 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <AudioLines className="w-4 h-4 text-cyan-400" />
            <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider">
              {lang === 'hi' ? 'वॉयस संवाद इतिहास (Audio Transcript)' : lang === 'mr' ? 'व्हॉईस संवाद इतिहास (Audio Transcript)' : 'Voice Conversation & Audio Feed'}
            </h3>
          </div>

          <button 
            onClick={() => {
              stopVoice();
              setMessages([getInitialWelcomeMessage(lang)]);
            }}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-all border border-slate-700/60"
            title="Clear Conversation"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Message Cards Feed */}
        <div ref={messagesContainerRef} className="p-5 max-h-[500px] overflow-y-auto space-y-4">
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

                {/* Content Bubble */}
                <div className={`max-w-[88%] rounded-2xl p-4 shadow-lg ${
                  isUser
                    ? 'bg-gradient-to-r from-indigo-600 to-indigo-700 text-white rounded-tr-none'
                    : msg.access_blocked
                    ? 'bg-rose-950/35 border border-rose-500/40 text-slate-100 rounded-tl-none'
                    : 'bg-slate-800/85 border border-slate-700/70 text-slate-100 rounded-tl-none'
                }`}>

                  {/* Security Alert Header */}
                  {msg.access_blocked && (
                    <div className="flex items-center gap-2 mb-3 pb-2 border-b border-rose-500/30 text-rose-400 text-xs font-bold">
                      <ShieldAlert className="w-4 h-4 shrink-0" />
                      <span>{lang === 'hi' ? 'सुरक्षा प्रतिबंध: पहुंच अस्वीकृत (RBAC Guardrail)' : lang === 'mr' ? 'सुरक्षा निर्बंध: डेटा प्रवेश नाकारला (RBAC Guardrail)' : 'SECURITY RESTRICTION: ACCESS DENIED (RBAC Guardrail)'}</span>
                    </div>
                  )}

                  {/* Markdown Answer Text / Loading Indicator */}
                  <div className="text-xs sm:text-sm leading-relaxed prose prose-invert max-w-none prose-p:my-1 prose-ul:my-1 prose-ol:my-1 prose-li:my-0.5">
                    {msg.text ? (
                      <ReactMarkdown>{msg.text}</ReactMarkdown>
                    ) : (
                      <div className="flex items-center gap-2.5 py-1 text-xs text-cyan-300 font-medium">
                        <span className="relative flex h-2 w-2">
                          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-cyan-400 opacity-75"></span>
                          <span className="relative inline-flex rounded-full h-2 w-2 bg-cyan-400"></span>
                        </span>
                        <span>{lang === 'hi' ? 'RAG विक्टर सर्च और RBAC सुरक्षा विश्लेषण जारी...' : lang === 'mr' ? 'RAG व्हेक्टर शोध व RBAC सुरक्षा पडताळणी सुरु...' : 'RAG Vector Index Search & Security RBAC Check in progress...'}</span>
                      </div>
                    )}
                  </div>

                  {/* Verified Sources */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-3.5 pt-3 border-t border-slate-700/60">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider flex items-center gap-1">
                          <FileText className="w-3.5 h-3.5 text-cyan-400" />
                          <span>{lang === 'hi' ? 'सत्यापित संयंत्र दस्तावेज़:' : lang === 'mr' ? 'सत्यापित कारखाना दस्तऐवज:' : 'Verified Plant Sources:'}</span>
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

                              {isExpanded && (
                                <div className="mt-1 p-3 rounded-lg bg-slate-950 border border-cyan-500/30 text-xs text-slate-300 font-mono space-y-1">
                                  <div className="text-[10px] text-cyan-400 font-bold uppercase">Source SOP Snippet:</div>
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

                  {/* Message Footer (Timestamp & Copy Only) */}
                  {msg.text && (
                    <div className="mt-3 pt-2.5 flex items-center justify-between text-[11px] text-slate-400 border-t border-slate-700/30">
                      <span>{msg.timestamp}</span>

                      {!isUser && (
                        <div className="flex items-center gap-2">
                          {/* Copy */}
                          <button
                            onClick={() => copyToClipboard(msg.text, idx)}
                            className="flex items-center gap-1 px-2 py-1 rounded hover:bg-slate-700/60 text-slate-400 hover:text-slate-200 transition-all text-xs"
                            title="Copy text"
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
                        </div>
                      )}
                    </div>
                  )}

                </div>
              </div>
            );
          })}

        </div>

        {/* Persistent Floating Audio Controller Dock when Voice is Active/Paused */}
        {speakingIndex !== null && (
          <div className="p-3.5 bg-slate-950/95 border-t border-cyan-500/40 flex items-center justify-between gap-3 backdrop-blur-md animate-in fade-in slide-in-from-bottom-2">
            <div className="flex items-center gap-3 min-w-0">
              {/* Visual Waveform */}
              <div className="flex items-end gap-1 h-5 px-1">
                <span className={`w-1 bg-cyan-400 rounded-full transition-all ${!isVoicePaused ? 'h-5 animate-pulse' : 'h-2'}`}></span>
                <span className={`w-1 bg-cyan-300 rounded-full transition-all ${!isVoicePaused ? 'h-3 animate-bounce' : 'h-2'}`} style={{ animationDelay: '150ms' }}></span>
                <span className={`w-1 bg-cyan-400 rounded-full transition-all ${!isVoicePaused ? 'h-4 animate-pulse' : 'h-2'}`} style={{ animationDelay: '300ms' }}></span>
                <span className={`w-1 bg-cyan-300 rounded-full transition-all ${!isVoicePaused ? 'h-2 animate-bounce' : 'h-2'}`} style={{ animationDelay: '75ms' }}></span>
              </div>
              <div className="min-w-0">
                <div className="text-xs font-bold text-cyan-300 flex items-center gap-1.5">
                  <AudioLines className="w-3.5 h-3.5 text-cyan-400" />
                  <span>
                    {isVoicePaused 
                      ? (lang === 'hi' ? 'वॉयस ऑडियो रुका हुआ है' : lang === 'mr' ? 'व्हॉईस ऑडिओ थांबवला आहे' : 'Voice Audio Paused') 
                      : (lang === 'hi' ? 'वॉयस ऑडियो चल रहा है...' : lang === 'mr' ? 'व्हॉईस ऑडिओ सुरू आहे...' : 'Playing Voice Audio...')}
                  </span>
                </div>
                <div className="text-[11px] text-slate-400 truncate max-w-xs sm:max-w-md">
                  {messages[speakingIndex]?.text?.replace(/[*_#`~]/g, '') || ''}
                </div>
              </div>
            </div>

            {/* Controls Bar */}
            <div className="flex items-center gap-2 shrink-0">
              {isVoicePaused ? (
                <button
                  onClick={resumeVoice}
                  className="px-3 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs flex items-center gap-1.5 shadow-md shadow-emerald-600/30 transition-all"
                  title="Resume Audio"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                  <span>{lang === 'hi' ? 'पुनः चालू करें' : lang === 'mr' ? 'पुढे सुरू करा' : 'Resume'}</span>
                </button>
              ) : (
                <button
                  onClick={pauseVoice}
                  className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs flex items-center gap-1.5 shadow-md shadow-amber-600/30 transition-all"
                  title="Pause Audio"
                >
                  <Pause className="w-3.5 h-3.5 fill-current" />
                  <span>{lang === 'hi' ? 'रोकें' : lang === 'mr' ? 'थांबवा' : 'Pause'}</span>
                </button>
              )}

              <button
                onClick={stopVoice}
                className="px-3 py-1.5 rounded-lg bg-rose-600/90 hover:bg-rose-600 text-white font-bold text-xs flex items-center gap-1.5 shadow-md shadow-rose-600/30 transition-all"
                title="Stop Audio"
              >
                <Square className="w-3 h-3 fill-current" />
                <span>{lang === 'hi' ? 'बंद करें' : lang === 'mr' ? 'बंद करा' : 'Stop'}</span>
              </button>
            </div>
          </div>
        )}

      </div>

    </div>
  );
}
