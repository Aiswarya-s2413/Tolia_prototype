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

export default function ChatWindow({ activeRole }) {
  const getInitialWelcomeMessage = () => ({
    sender: 'bot',
    text: 'Hello! / नमस्कार! I am your **Tolia Voice-First AI Assistant**.\n\nSpeak or type naturally in **English**, **हिंदी (Hindi)**, or **मराठी (Marathi)** — I dynamically detect and respond in your language:\n- *"What are the emergency shutdown steps for the Blast Furnace?"*\n- *"ब्लास्ट फर्नेस का सुरक्षा तापमान और आपातकालीन नियम क्या हैं?"*\n- *"रोलिंग मिल गिअरबॉक्स ऑइल आणि हायड्रोलिक दाब SOP सांगा"*\n- *"संयंत्र में अनिवार्य पीपीई किट नियम क्या हैं?"*',
    sources: [],
    language: 'en',
    timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  });

  const [messages, setMessages] = useState([getInitialWelcomeMessage()]);
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
  const [currentDetectedLang, setCurrentDetectedLang] = useState('en');

  const messagesContainerRef = useRef(null);
  const mediaStreamRef = useRef(null);
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

  const audioAnalyserRef = useRef(null);
  const micAnimFrameRef = useRef(null);
  const [micVolume, setMicVolume] = useState(0);
  const speechDetectedRef = useRef(false);
  const vadIntervalRef = useRef(null);

  const startMediaRecording = async () => {
    try {
      if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
      if (vadIntervalRef.current) clearInterval(vadIntervalRef.current);
      if (micAnimFrameRef.current) cancelAnimationFrame(micAnimFrameRef.current);

      if (mediaStreamRef.current) {
        mediaStreamRef.current.getTracks().forEach((track) => track.stop());
        mediaStreamRef.current = null;
      }

      speechDetectedRef.current = false;
      setIsListening(true);
      setLiveTranscript('Listening (100% On-Premise VEXYL STT)... Speak now...');

      // 100% Local Microphone Stream with robust audio constraint fallback
      let stream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({ 
          audio: { 
            echoCancellation: true, 
            noiseSuppression: true, 
            autoGainControl: true 
          } 
        });
      } catch (cErr) {
        console.warn("Hardware constraints not supported, falling back to basic audio stream:", cErr);
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      }
      mediaStreamRef.current = stream;
      audioChunksRef.current = [];

      let mimeType = 'audio/webm;codecs=opus';
      if (!MediaRecorder.isTypeSupported('audio/webm;codecs=opus')) {
        mimeType = MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : 'audio/mp4';
      }

      const mediaRecorder = new MediaRecorder(stream, mimeType ? { mimeType } : undefined);
      mediaRecorderRef.current = mediaRecorder;

      // Real-time Adaptive Time-Domain RMS Audio Level Analyzer & Dynamic VAD
      try {
        const AudioCtx = window.AudioContext || window.webkitAudioContext;
        if (AudioCtx) {
          const ctx = new AudioCtx();
          if (ctx.state === 'suspended') await ctx.resume();
          const source = ctx.createMediaStreamSource(stream);
          const analyser = ctx.createAnalyser();
          analyser.fftSize = 256;
          analyser.smoothingTimeConstant = 0.2;
          source.connect(analyser);
          audioAnalyserRef.current = { ctx, analyser };

          let ambientFloor = 5;
          let calibrationCount = 0;
          let calibrationSum = 0;
          let speechFrames = 0;
          let silenceStart = 0;

          const timeData = new Uint8Array(analyser.fftSize);
          const checkLevel = () => {
            if (!analyser || !mediaStreamRef.current) return;
            analyser.getByteTimeDomainData(timeData);

            let sumSquares = 0;
            for (let i = 0; i < timeData.length; i++) {
              const norm = (timeData[i] - 128) / 128;
              sumSquares += norm * norm;
            }
            const rms = Math.sqrt(sumSquares / timeData.length);
            const currentVol = Math.min(100, Math.round(rms * 220));
            setMicVolume(currentVol);

            const now = Date.now();
            if (currentVol >= 6) {
              speechDetectedRef.current = true;
              silenceStart = 0;
            } else if (speechDetectedRef.current && currentVol < 6) {
              if (!silenceStart) {
                silenceStart = now;
              } else if (now - silenceStart >= 850) {
                // 850ms natural pause detected
                console.log("[VAD] Voice pause detected, submitting to VEXYL STT...");
                silenceStart = 0;
                stopMediaRecording();
                return;
              }
            }

            micAnimFrameRef.current = requestAnimationFrame(checkLevel);
          };
          checkLevel();
        }
      } catch (e) {
        console.warn("Audio meter setup notice:", e);
      }

      // Max safety recording timeout (8 seconds) to prevent infinite listening
      silenceTimerRef.current = setTimeout(() => {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
          console.log("[VAD] Max recording duration reached, submitting...");
          stopMediaRecording();
        }
      }, 8000);

      mediaRecorder.ondataavailable = (event) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        if (vadIntervalRef.current) clearInterval(vadIntervalRef.current);
        if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
        if (micAnimFrameRef.current) cancelAnimationFrame(micAnimFrameRef.current);
        if (audioAnalyserRef.current?.ctx) {
          try { audioAnalyserRef.current.ctx.close(); } catch (e) {}
          audioAnalyserRef.current = null;
        }
        setMicVolume(0);

        if (mediaStreamRef.current) {
          mediaStreamRef.current.getTracks().forEach((track) => track.stop());
          mediaStreamRef.current = null;
        }

        const audioBlob = new Blob(audioChunksRef.current, { type: mimeType || 'audio/webm' });
        if (audioBlob.size > 80) {
          const formData = new FormData();
          formData.append('audio', audioBlob, 'audio.webm');
          formData.append('language', selectedLanguage || 'auto');

          try {
            setLiveTranscript('Transcribing with on-premise VEXYL STT...');
            setIsLoading(true);
            const res = await fetch('/api/voice/transcribe/', {
              method: 'POST',
              body: formData,
            });
            const data = await res.json();
            setIsLoading(false);
            if (data && data.text && data.text.trim()) {
              const detectedLanguage = data.language || selectedLanguage || 'en';
              setCurrentDetectedLang(detectedLanguage);
              setInputQuery(data.text);
              setLiveTranscript('');
              handleSendMessage(data.text.trim(), detectedLanguage);
            } else {
              setLiveTranscript('No speech detected. Please speak closer to microphone.');
              setIsLoading(false);
              setTimeout(() => setLiveTranscript(''), 3000);
            }
          } catch (err) {
            console.error('STT transcription error:', err);
            setLiveTranscript('Local STT error. Please try again.');
            setIsLoading(false);
            setTimeout(() => setLiveTranscript(''), 3000);
          }
        } else {
          setLiveTranscript('Recording too short. Please speak your question.');
          setTimeout(() => setLiveTranscript(''), 2500);
        }
      };

      mediaRecorder.start(200);
    } catch (err) {
      console.error('Microphone start error:', err);
      setIsListening(false);
      const errMsg = err?.name === 'NotAllowedError' 
        ? 'Microphone permission was denied. Click the Tune/Lock icon next to URL -> Allow Microphone -> Reload.' 
        : `Microphone issue (${err?.name || 'Error'}): ${err?.message || 'Unable to access audio device'}`;
      setLiveTranscript(errMsg);
    }
  };

  const stopMediaRecording = () => {
    if (vadIntervalRef.current) clearInterval(vadIntervalRef.current);
    if (silenceTimerRef.current) clearTimeout(silenceTimerRef.current);
    if (micAnimFrameRef.current) cancelAnimationFrame(micAnimFrameRef.current);

    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try {
        mediaRecorderRef.current.requestData();
        mediaRecorderRef.current.stop();
      } catch (e) {}
    }
    setIsListening(false);
  };

  // Fluid Voice Toggle & Barge-In
  const toggleListening = () => {
    try {
      unlockAudioContext();
    } catch (e) {}

    const isBotSpeaking = isPlayingQueueRef.current || (currentAudioRef.current && !currentAudioRef.current.paused) || speakingIndex !== null;
    if (isBotSpeaking) {
      stopVoice();
    }

    if (isListening) {
      stopMediaRecording();
    } else {
      stopVoice();
      startMediaRecording();
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
  const queueSentenceForTTS = (sentenceText, msgIndex, targetLang) => {
    const cleanText = sentenceText
      .replace(/[*_#`~]/g, '')
      .replace(/⚠️|💡|📌|▶️|✅|🛡️|🏢|👥|📋|📜/g, '')
      .replace(/\[(.*?)\]\(.*?\)/g, '$1')
      .replace(/https?:\/\/\S+/g, '')
      .trim();

    // Ignore tiny fragments (e.g. single numbers or symbols) to prevent fragmented audio gaps
    if (!cleanText || cleanText.length < 8) return;

    const targetIdx = msgIndex !== undefined && msgIndex !== null ? msgIndex : getLatestBotMessageIndex();
    const langParam = targetLang || 'auto';
    const audioUrl = `/api/voice/synthesize/?text=${encodeURIComponent(cleanText)}&lang=${encodeURIComponent(langParam)}`;
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
  const speakText = (text, index, targetLang) => {
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
    const langParam = targetLang || (messages[targetIdx]?.language) || 'auto';

    // High-Speed Backend Voice (/api/voice/synthesize/)
    const audioUrl = `/api/voice/synthesize/?text=${encodeURIComponent(cleanText)}&lang=${encodeURIComponent(langParam)}`;
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

  // Zero-Latency Streaming + Dynamic Multi-Language Message Handler
  const handleSendMessage = async (queryToSend, forcedLang) => {
    const query = (queryToSend || inputQuery).trim();
    if (!query) return;
    if (!queryToSend && isLoading) return;

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
      language: forcedLang || 'auto',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      isStreaming: true
    };

    // Clean up any unfinished/empty in-flight bot messages before appending
    setMessages(prev => [
      ...prev.filter(m => !(m.sender === 'bot' && !m.text && m.isStreaming)),
      userMsg,
      initialBotMsg
    ]);
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
          language: forcedLang || 'auto'
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
      let msgLang = forcedLang || 'auto';

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
                if (data.language) {
                  msgLang = data.language;
                  setCurrentDetectedLang(data.language);
                }
                setMessages(prev => prev.map(m => m.id === botMsgId ? {
                  ...m,
                  sources: data.sources || [],
                  access_blocked: data.access_blocked || false,
                  language: data.language || m.language
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
                  queueSentenceForTTS(data.text, currentIdx >= 0 ? currentIdx : 1, msgLang);
                }
              } else if (data.type === 'done') {
                setMessages(prev => prev.map(m => m.id === botMsgId ? {
                  ...m,
                  isStreaming: false
                } : m));
                // Fallback ONLY if no sentence audio was queued at all during streaming
                if (autoSpeak && !hasQueuedAudioRef.current && accumulatedText) {
                  const currentIdx = getLatestBotMessageIndex();
                  speakText(accumulatedText, currentIdx >= 0 ? currentIdx : 1, msgLang);
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
        text: m.text || '⚠️ Unable to connect to backend server. Please verify Django server is running.',
        isStreaming: false
      } : m));
    } finally {
      setIsLoading(false);
    }
  };

  const sampleVoicePrompts = [
    { text: 'What are the emergency shutdown steps for Blast Furnace?', langTag: 'EN', color: 'text-cyan-400' },
    { text: 'ब्लास्ट फर्नेस आपातकालीन सुरक्षा नियम क्या हैं?', langTag: 'HI', color: 'text-amber-400' },
    { text: 'रोलिंग मिल गिअरबॉक्स ऑइल आणि हायड्रोलिक दाब SOP सांगा', langTag: 'MR', color: 'text-emerald-400' },
    { text: 'What is the standard hydraulic pressure for Rolling Mill?', langTag: 'EN', color: 'text-cyan-400' },
    { text: 'संयंत्र में अनिवार्य पीपीई किट नियम क्या हैं?', langTag: 'HI', color: 'text-amber-400' },
    { text: 'कारखान्यातील अनिवार्य पीपीई किट नियम काय आहेत?', langTag: 'MR', color: 'text-emerald-400' },
    { text: 'Q1 वित्तीय एवं बिक्री लक्ष्य क्या है?', langTag: 'HI', color: 'text-indigo-400' }
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
            <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-slate-800/80 border border-slate-700/70 text-xs font-semibold">
              <span className="relative flex h-2.5 w-2.5">
                <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${isListening ? 'bg-rose-400' : speakingIndex !== null ? 'bg-cyan-400' : 'bg-emerald-400'} opacity-75`}></span>
                <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${isListening ? 'bg-rose-500' : speakingIndex !== null ? 'bg-cyan-500' : 'bg-emerald-500'}`}></span>
              </span>
              <span className="text-slate-300 font-mono">
                {isListening 
                  ? 'Microphone Active: Listening in English / Hindi / Marathi...' 
                  : speakingIndex !== null 
                  ? 'AI Speaking Response...'
                  : isLoading
                  ? 'RAG Vector Index Search & Dynamic Language Analysis...'
                  : 'Dynamic Voice AI (English • हिंदी • मराठी) — Tap & Speak'}
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

          {/* Dynamic Audio Equalizer Bars & Live Mic Level */}
          <div className="flex items-center justify-center gap-1.5 h-8">
            {[1, 2, 3, 4, 5, 6].map((barIdx) => {
              const baseHeight = isListening ? Math.max(6, Math.min(32, micVolume * (0.3 + barIdx * 0.12))) : 6;
              return (
                <span
                  key={barIdx}
                  style={isListening ? { height: `${baseHeight}px` } : {}}
                  className={`w-1.5 rounded-full transition-all duration-75 ${
                    isListening
                      ? 'bg-rose-400'
                      : speakingIndex !== null
                      ? 'bg-cyan-400 wave-bar-1'
                      : 'h-1.5 bg-slate-700'
                  }`}
                ></span>
              );
            })}
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
                  if (idx >= 0) speakText(messages[idx].text, idx, messages[idx]?.language);
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
              <span>Play Voice</span>
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
              <span>Pause</span>
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
              <span>Resume</span>
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
              <span>Stop</span>
            </button>
          </div>

          {/* Live Speech Recognition & STT Status Transcript Box */}
          {(isListening || liveTranscript) && (
            <div className={`w-full border rounded-2xl p-4 text-center transition-all ${
              isListening
                ? 'bg-rose-950/40 border-rose-500/50 animate-pulse'
                : 'bg-indigo-950/40 border-indigo-500/50'
            }`}>
              <div className={`text-[11px] font-bold uppercase tracking-wider mb-1 flex items-center justify-center gap-1.5 ${
                isListening ? 'text-rose-400' : 'text-cyan-400'
              }`}>
                <Mic className={`w-3.5 h-3.5 ${isListening ? 'animate-ping' : 'animate-spin'}`} />
                <span>
                  {isListening
                    ? 'Microphone Active (Speak in English, Hindi, or Marathi)'
                    : 'Transcribing Audio with Indic Voice Engine...'}
                </span>
              </div>
              <p className="text-sm font-semibold text-slate-100 italic">
                {liveTranscript || 'Listening... Speak now...'}
              </p>
            </div>
          )}

          {/* Quick Voice Chips */}
          <div className="w-full space-y-2">
            <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider flex items-center justify-center gap-1.5">
              <Headphones className="w-3.5 h-3.5 text-cyan-400" />
              <span>Suggested Multilingual Voice Prompts (Tap to Ask):</span>
            </div>

            <div className="flex flex-wrap justify-center gap-2">
              {sampleVoicePrompts.map((prompt, pIdx) => (
                <button
                  key={pIdx}
                  onClick={() => handleSendMessage(prompt.text)}
                  disabled={isLoading}
                  className="px-3 py-1.5 rounded-xl bg-slate-800/80 hover:bg-slate-800 border border-slate-700/80 hover:border-cyan-500/40 text-xs text-slate-300 hover:text-cyan-200 font-medium transition-all shadow-sm flex items-center gap-2 group text-left"
                >
                  <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded bg-slate-900 border border-slate-700 ${prompt.color}`}>
                    {prompt.langTag}
                  </span>
                  <span className="truncate max-w-xs">{prompt.text}</span>
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
                placeholder="Type in English, Hindi, or Marathi (e.g. blast furnace safety, रोलिंग मिल SOP...)"
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
              Multilingual Conversation Transcript & Audio History
            </h3>
          </div>

          <button 
            onClick={() => {
              stopVoice();
              setMessages([getInitialWelcomeMessage()]);
            }}
            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-400 hover:text-slate-200 transition-all border border-slate-700/60"
            title="Clear Conversation"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* Message Cards Feed */}
        <div ref={messagesContainerRef} className="p-5 max-h-[500px] overflow-y-auto space-y-4">
          {messages.filter(m => (m.text && m.text.trim().length > 0) || m.isStreaming).map((msg, idx) => {
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
                      <span>SECURITY RESTRICTION: ACCESS DENIED (RBAC Guardrail)</span>
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
                        <span>RAG Vector Index Search & Dynamic Multilingual Analysis in progress...</span>
                      </div>
                    )}
                  </div>

                  {/* Verified Sources */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-3.5 pt-3 border-t border-slate-700/60">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-[10px] text-slate-400 font-bold uppercase tracking-wider flex items-center gap-1">
                          <FileText className="w-3.5 h-3.5 text-cyan-400" />
                          <span>Verified Plant Sources:</span>
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
                    {isVoicePaused ? 'Voice Audio Paused' : 'Playing Voice Audio...'}
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
                  <span>Resume</span>
                </button>
              ) : (
                <button
                  onClick={pauseVoice}
                  className="px-3 py-1.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs flex items-center gap-1.5 shadow-md shadow-amber-600/30 transition-all"
                  title="Pause Audio"
                >
                  <Pause className="w-3.5 h-3.5 fill-current" />
                  <span>Pause</span>
                </button>
              )}

              <button
                onClick={stopVoice}
                className="px-3 py-1.5 rounded-lg bg-rose-600/90 hover:bg-rose-600 text-white font-bold text-xs flex items-center gap-1.5 shadow-md shadow-rose-600/30 transition-all"
                title="Stop Audio"
              >
                <Square className="w-3 h-3 fill-current" />
                <span>Stop</span>
              </button>
            </div>
          </div>
        )}

      </div>

    </div>
  );
}
