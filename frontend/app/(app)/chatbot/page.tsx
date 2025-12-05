'use client';
import { useState, useRef, useEffect, useCallback, memo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from "remark-gfm";
import { Send, Bot, Loader2, Clock, Mic, MicOff, Volume2 } from 'lucide-react';
import { ConfirmDialog } from '@/components/ConfirmDialog';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import SpeechRecognition, { useSpeechRecognition } from 'react-speech-recognition';

interface Message {
  id: string;
  text: string;
  type: 'user' | 'assistant';
  timestamp: string;
  createdAt: number;
}

const ChatMessage = memo(({ message, onSpeakMessage }: { message: Message, onSpeakMessage: (text: string) => void }) => (
  <div className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}>
    <div className={`p-3 rounded-lg inline-block ${message.type === 'user'
      ? 'bg-[#00E676] text-black'
      : 'bg-[#1A1A1A] text-white'
      }`}>
      <div className="whitespace-pre-wrap break-words max-w-[400px] w-full prose prose-invert prose-sm">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.text}</ReactMarkdown>
      </div>
      <div className="flex justify-between items-center mt-1">
        <p className="text-xs opacity-50">{message.timestamp}</p>
        {message.type === 'assistant' && (
          <button
            onClick={() => onSpeakMessage(message.text)}
            className="text-xs opacity-50 hover:opacity-100"
            aria-label="Speak message"
          >
            <Volume2 size={14} />
          </button>
        )}
      </div>
    </div>
  </div>
));
ChatMessage.displayName = 'ChatMessage';

const TypingIndicator = memo(() => (
  <div className="flex items-center text-sm text-gray-400 ml-2">
    <Loader2 className="w-4 h-4 mr-2 animate-spin" />
    Assistant is typing...
  </div>
));
TypingIndicator.displayName = 'TypingIndicator';

export default function AISidebar() {
  const [messages, setMessages] = useState<Message[]>(() => {
    if (typeof window !== 'undefined') {
      const savedMessages = localStorage.getItem('chatMessages');

      if (savedMessages) {
        try {
          const parsedMessages = JSON.parse(savedMessages) as Message[];
          const twelveHoursAgo = Date.now() - (12 * 60 * 60 * 1000);
          return parsedMessages.filter(msg => msg.createdAt && msg.createdAt > twelveHoursAgo);
        } catch (e) {
          console.error('Error parsing saved messages:', e);
          return getDefaultWelcomeMessage();
        }
      }
    }
    return getDefaultWelcomeMessage();
  });
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [abortController, setAbortController] = useState<AbortController | null>(null);
  const [isListening, setIsListening] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const [isConfirmOpen, setIsConfirmOpen] = useState(false);
  const synth = typeof window !== 'undefined' ? window.speechSynthesis : null;

  const {
    transcript,
    listening,
    resetTranscript,
    browserSupportsSpeechRecognition
  } = useSpeechRecognition();

  function getDefaultWelcomeMessage(): Message[] {
    return [{
      id: 'welcome-msg',
      text: 'Hello! How can I assist you today? 😊 You can type or use the microphone to speak to me.',
      type: 'assistant',
      timestamp: new Date().toLocaleTimeString(),
      createdAt: Date.now()
    }];
  }

  const filterRecentMessages = useCallback((msgs: Message[]) => {
    const twelveHoursAgo = Date.now() - (12 * 60 * 60 * 1000);
    return msgs.filter(msg => msg.createdAt && msg.createdAt > twelveHoursAgo);
  }, []);

  useEffect(() => {
    const recentMessages = filterRecentMessages(messages);

    if (recentMessages.length !== messages.length) {
      setMessages(recentMessages);
    }

    localStorage.setItem('chatMessages', JSON.stringify(recentMessages));
  }, [messages, filterRecentMessages]);

  useEffect(() => {
    const cleanupInterval = setInterval(() => {
      setMessages(prevMessages => filterRecentMessages(prevMessages));
    }, 60 * 60 * 1000);

    return () => clearInterval(cleanupInterval);
  }, [filterRecentMessages]);

  useEffect(() => {
    if (scrollAreaRef.current) {
      requestAnimationFrame(() => {
        if (scrollAreaRef.current) {
          scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
        }
      });
    }
  }, [messages]);

  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.focus();
    }
  }, []);

  useEffect(() => {
    return () => {
      if (abortController) {
        abortController.abort();
      }
      if (synth) {
        synth.cancel();
      }
    };
  }, [abortController]);

  useEffect(() => {
    if (transcript) {
      setInputMessage(transcript);
    }
  }, [transcript]);

  const speakMessage = useCallback((text: string) => {
    if (synth) {
      synth.cancel();

      const cleanText = text.replace(/\*\*|__|\*|_|`|#|>|\[.*\]\(.*\)/g, '');

      const utterance = new SpeechSynthesisUtterance(cleanText);
      utterance.rate = 1;
      utterance.pitch = 1;
      synth.speak(utterance);
    }
  }, []);

  const toggleListening = useCallback(() => {
    if (listening) {
      SpeechRecognition.stopListening();
      setIsListening(false);
      if (transcript) {
        setTimeout(() => {
          handleSendMessage(transcript);
        }, 500);
      }
    } else {
      resetTranscript();
      SpeechRecognition.startListening({ continuous: true });
      setIsListening(true);
      toast.info('Listening... Speak now', {
        position: "top-right",
        autoClose: 2000,
        hideProgressBar: false,
        closeOnClick: true,
        pauseOnHover: true,
        draggable: true,
        theme: "dark",
      });
    }
  }, [listening, transcript]);

  const handleSendMessage = useCallback(async (message = inputMessage) => {
    if (!message.trim() || isTyping) return;

    const messageId = `msg-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const currentTime = Date.now();
    const newUserMessage: Message = {
      id: messageId,
      text: message.trim(),
      type: 'user',
      timestamp: new Date(currentTime).toLocaleTimeString(),
      createdAt: currentTime
    };

    setMessages((prev) => [...prev, newUserMessage]);
    setInputMessage('');
    resetTranscript();
    setIsTyping(true);

    const controller = new AbortController();
    setAbortController(controller);

    try {
      const response = await fetch(`http://localhost:5000/chatbot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: message.trim() })
      });
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      const data = await response.json();
      const responseTime = Date.now();
      const newBotMessage: Message = {
        id: `response-${messageId}`,
        text: data.response || "I'm sorry, I couldn't process that.",
        type: 'assistant',
        timestamp: new Date(responseTime).toLocaleTimeString(),
        createdAt: responseTime
      };

      setMessages((prev) => [...prev, newBotMessage]);

      speakMessage(newBotMessage.text);
    } catch (error) {
      if (!(error instanceof DOMException && error.name === 'AbortError')) {
        console.error('Error fetching chatbot response:', error);
        const errorTime = Date.now();
        setMessages((prev) => [
          ...prev,
          {
            id: `error-${messageId}`,
            text: "Sorry, I couldn't fetch a response. Please try again later.",
            type: 'assistant',
            timestamp: new Date(errorTime).toLocaleTimeString(),
            createdAt: errorTime
          },
        ]);
      }
    } finally {
      setIsTyping(false);
      setAbortController(null);

      // Focus back on input after sending
      if (inputRef.current) {
        inputRef.current.focus();
      }
    }
  }, [inputMessage, isTyping, resetTranscript, speakMessage]);

  const handleKeyPress = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  }, [handleSendMessage]);

  const clearChat = useCallback(() => {
    setIsConfirmOpen(true);
  }, []);

  const handleConfirmClear = useCallback(() => {
    setIsConfirmOpen(false);
    setMessages(getDefaultWelcomeMessage());

    toast.success('Chat history cleared successfully!', {
      position: "top-right",
      autoClose: 3000,
      hideProgressBar: false,
      closeOnClick: true,
      pauseOnHover: true,
      draggable: true,
      theme: "dark",
    });
  }, []);

  return (
    <div className="w-full bg-[#141414] h-screen flex flex-col">
      <ToastContainer />
      <ConfirmDialog
        isOpen={isConfirmOpen}
        onClose={() => setIsConfirmOpen(false)}
        onConfirm={handleConfirmClear}
        title="Clear Chat History"
        message="Are you sure you want to clear all chat history? This action cannot be undone."
      />
      <div className="flex items-center justify-between p-4 bg-[#1A1A1A]">
        <div className="flex items-center">
          <div className="w-10 h-10 bg-[#00E676] rounded-full flex items-center justify-center">
            <Bot size={20} />
          </div>
          <div className="ml-3">
            <h2 className="text-white font-medium">AI Assistant</h2>
            <p className="text-gray-400 text-sm">
              {isTyping ? 'Typing...' : listening ? 'Listening...' : 'Online'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-xs text-gray-400 flex items-center">
            <Clock size={14} className="mr-1" />
            Saving last 12hrs of chat
          </div>
          <button
            onClick={clearChat}
            className="text-gray-400 hover:text-white text-sm px-3 py-1 rounded hover:bg-[#252525] transition-colors"
          >
            Clear Chat
          </button>
        </div>
      </div>

      <div
        ref={scrollAreaRef}
        className="flex-1 p-4 overflow-y-auto text-white scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-transparent"
      >
        <div className="space-y-4">
          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} onSpeakMessage={speakMessage} />
          ))}
          {isTyping && <TypingIndicator />}
        </div>
      </div>

      <div className="p-4 border-t border-[#2A2A2A] w-full">
        <div className="flex items-center gap-2">
          <input
            ref={inputRef}
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder={listening ? "Listening..." : "Type your message..."}
            className="w-full bg-[#1A1A1A] text-white rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-[#00E676]"
            disabled={isTyping || listening}
          />
          {browserSupportsSpeechRecognition && (
            <button
              onClick={toggleListening}
              className={`p-2 rounded-lg transition-colors flex items-center justify-center ${listening
                  ? 'bg-red-600 hover:bg-red-700 text-white'
                  : 'bg-[#1A1A1A] text-[#00E676] hover:bg-[#252525]'
                }`}
              aria-label={listening ? "Stop listening" : "Start listening"}
            >
              {listening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
            </button>
          )}
          <button
            onClick={() => handleSendMessage()}
            className="bg-[#00E676] text-black p-2 rounded-lg hover:bg-[#00ff84] transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
            disabled={(!inputMessage.trim() && !transcript) || isTyping || isListening}
            aria-label="Send message"
          >
            {isTyping ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
          </button>
        </div>
      </div>
    </div>
  );
}