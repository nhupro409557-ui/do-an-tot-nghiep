import { useEffect, useRef, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { AnimatePresence, LazyMotion, domAnimation, m } from 'motion/react';
import { ImageOff, X, Send, Sparkles, ShoppingCart, Minus, ThumbsDown, ThumbsUp, PhoneCall, RotateCcw } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useCart } from '../../context/CartContext';
import {
  askAIAssistant,
  createAIConversation,
  submitAIAssistantFeedback,
  type AIAssistantAnswerMode,
  type AIConversationSession,
  type AIAssistantRequest,
} from '../../services/aiAssistantApi';
import robotAvatar from '../../assets/chatbot-robot.png';

type Message = {
  id: string;
  sender: 'ai' | 'user';
  text: string;
  products?: any[];
  answerMode?: AIAssistantAnswerMode;
  responseId?: string;
  feedback?: 'helpful' | 'not_helpful';
  handover?: {
    phone?: string | null;
    email?: string | null;
    supportRequestCode?: string | null;
  } | null;
};

const initialMessages = (): Message[] => [{
  id: '1',
  sender: 'ai',
  text: 'Chào bạn! 👋 Mình là trợ lý AI của ElectroMart. Mình có thể tư vấn sản phẩm, chính sách, đơn hàng và điểm tích lũy cho bạn.',
}];

const conversationStorageKey = (userId?: string) => `electromart_ai_conversation_${userId || 'guest'}`;
const messagesStorageKey = (userId?: string) => `electromart_ai_messages_${userId || 'guest'}`;

const loadStoredMessages = (userId?: string): Message[] => {
  try {
    const stored = sessionStorage.getItem(messagesStorageKey(userId));
    const parsed = stored ? JSON.parse(stored) : null;
    return Array.isArray(parsed) && parsed.length > 0 ? parsed : initialMessages();
  } catch {
    return initialMessages();
  }
};

const loadStoredConversation = (userId?: string): AIConversationSession | null => {
  try {
    const stored = sessionStorage.getItem(conversationStorageKey(userId));
    const parsed = stored ? JSON.parse(stored) : null;
    if (
      typeof parsed?.conversation_id !== 'string'
      || typeof parsed?.conversation_token !== 'string'
      || typeof parsed?.expires_at !== 'string'
      || Date.parse(parsed.expires_at) <= Date.now() + 60_000
    ) {
      return null;
    }
    return parsed as AIConversationSession;
  } catch {
    return null;
  }
};

const quickActions = [
  { label: 'Chính sách bảo hành', text: 'Chính sách bảo hành' },
  { label: 'Tư vấn laptop', text: 'Tư vấn laptop cho sinh viên IT' },
  { label: 'Tra đơn hàng', text: 'Đơn hàng của tôi ở đâu?' },
];

const ProductThumbnail = ({ src }: { src?: string }) => {
  const [failed, setFailed] = useState(!src);

  return (
    <span className="flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-lg bg-white text-gray-400">
      {failed ? (
        <ImageOff className="h-5 w-5" aria-hidden="true" />
      ) : (
        <img
          src={src}
          alt=""
          loading="lazy"
          className="h-full w-full object-contain"
          onError={() => setFailed(true)}
        />
      )}
    </span>
  );
};

const cleanAssistantAnswer = (answer: string) => answer
  .replace(/\*\*(.*?)\*\*/g, '$1')
  .replace(/`([^`]+)`/g, '$1')
  .trim();

export const AIChatWidget = () => {
  const location = useLocation();
  const { items } = useCart();
  const { user, userData } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [conversation, setConversation] = useState<AIConversationSession | null>(() => loadStoredConversation(user?.uid));
  const [messageOwnerKey, setMessageOwnerKey] = useState(() => user?.uid || 'guest');
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [messages, setMessages] = useState<Message[]>(() => loadStoredMessages(user?.uid));

  useEffect(() => {
    setMessageOwnerKey(user?.uid || 'guest');
    const storedConversation = loadStoredConversation(user?.uid);
    setConversation(storedConversation);
    setMessages(storedConversation ? loadStoredMessages(user?.uid) : initialMessages());
  }, [user?.uid]);

  useEffect(() => {
    sessionStorage.setItem(`electromart_ai_messages_${messageOwnerKey}`, JSON.stringify(messages));
  }, [messageOwnerKey, messages]);

  const currentContext = {
    viewing: items[0]?.name || 'Danh mục sản phẩm',
    cartItems: items.length,
  };

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen, isTyping]);

  const dynamicContext = (): AIAssistantRequest['dynamic_context'] => ({
    cart_items: items.map((item) => ({
      product_id: item.productId,
      name: item.name,
      quantity: item.quantity,
      price: item.price,
    })),
    viewed_products: [],
    loyalty: userData
      ? {
          tier:
            userData.tier === 'Diamond'
              ? 'DIAMOND'
              : userData.tier === 'Gold'
                ? 'GOLD'
                : userData.tier === 'Silver'
                  ? 'SILVER'
                  : 'MEMBER',
          points_balance: userData.points || 0,
          wallet_status: 'ACTIVE',
        }
      : null,
  });

  const requestBackendAnswer = async (text: string) => {
    let activeConversation = conversation;
    if (!activeConversation || Date.parse(activeConversation.expires_at) <= Date.now() + 60_000) {
      activeConversation = await createAIConversation();
      sessionStorage.setItem(conversationStorageKey(user?.uid), JSON.stringify(activeConversation));
      setConversation(activeConversation);
    }
    const productRouteMatch = location.pathname.match(/^\/product\/([^/]+)\/?$/);
    return askAIAssistant({
      conversation_id: activeConversation.conversation_id,
      conversation_token: activeConversation.conversation_token,
      message: text,
      dynamic_context: dynamicContext(),
      page_context: productRouteMatch
        ? { product_id: decodeURIComponent(productRouteMatch[1]), cart_item_ids: [] }
        : undefined,
    });
  };

  const handleSendMessage = async (text: string) => {
    if (!text.trim()) return;

    setMessages((prev) => [...prev, { id: Date.now().toString(), sender: 'user', text }]);
    setInputText('');
    setIsTyping(true);

    try {
      const data = await requestBackendAnswer(text);
      setMessages((prev) => [...prev, {
        id: (Date.now() + 1).toString(),
        sender: 'ai',
        text: cleanAssistantAnswer(data.answer),
        products: data.recommended_products || [],
        answerMode: data.answer_mode,
        responseId: data.response_id,
        handover: data.handover ? {
          phone: data.handover.phone,
          email: data.handover.email,
          supportRequestCode: data.handover.support_request_code,
        } : null,
      }]);
    } catch {
      setMessages((prev) => [...prev, {
        id: (Date.now() + 1).toString(),
        sender: 'ai',
        text: 'Trợ lý đang tạm thời chưa kết nối được. Bạn vui lòng thử lại sau ít phút.',
      }]);
    } finally {
      setIsTyping(false);
    }
  };

  const startNewConversation = () => {
    sessionStorage.removeItem(conversationStorageKey(user?.uid));
    setConversation(null);
    setMessages(initialMessages());
    setInputText('');
  };

  const handleFeedback = async (messageId: string, responseId: string, helpful: boolean) => {
    if (!conversation) return;
    try {
      const result = await submitAIAssistantFeedback({
        response_id: responseId,
        conversation_id: conversation.conversation_id,
        conversation_token: conversation.conversation_token,
        helpful,
      });
      setMessages((current) => {
        const feedback: Message['feedback'] = helpful ? 'helpful' : 'not_helpful';
        const updated = current.map((message) => (
          message.id === messageId
          ? { ...message, feedback }
          : message
        ));
        if (!helpful && result.handover_recommended && result.handover) {
          return [...updated, {
            id: `${Date.now()}-handover`,
            sender: 'ai',
            text: result.handover.display_text || 'Bạn có muốn liên hệ bộ phận chăm sóc khách hàng không?',
            handover: {
              phone: result.handover.phone,
              email: result.handover.email,
              supportRequestCode: result.handover.support_request_code,
            },
          }];
        }
        return updated;
      });
    } catch {
      // Không làm gián đoạn cuộc trò chuyện nếu dịch vụ ghi nhận phản hồi tạm lỗi.
    }
  };

  return (
    <div className="fixed bottom-[calc(env(safe-area-inset-bottom)+7rem)] right-4 z-[60] md:bottom-24 md:right-5 lg:bottom-6 lg:right-6">
      <LazyMotion features={domAnimation}>
        <AnimatePresence>
          {isOpen && (
            <m.div
            initial={{ opacity: 0, y: 20, scale: 0.92 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.92 }}
            transition={{ type: 'spring', damping: 25, stiffness: 350 }}
            className="absolute bottom-16 right-0 flex h-[min(500px,calc(100dvh-13rem))] w-[calc(100vw-1.5rem)] flex-col overflow-hidden rounded-2xl bg-white shadow-2xl md:bottom-[4.5rem] md:h-[500px] md:w-[380px] md:rounded-3xl lg:bottom-20 lg:h-[540px] lg:w-[400px]"
            style={{ boxShadow: '0 25px 60px -15px rgba(220, 38, 38, 0.25), 0 10px 30px -10px rgba(0,0,0,0.1)' }}
          >
            {/* Header */}
            <div className="relative shrink-0 overflow-hidden">
              <div className="bg-gradient-to-r from-red-600 via-red-500 to-rose-500 px-5 py-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="relative">
                      <div className="w-10 h-10 rounded-full bg-white/20 backdrop-blur-sm p-0.5 ring-2 ring-white/30 overflow-hidden">
                        <img src={robotAvatar} alt="AI Bot" className="w-full h-full rounded-full object-cover" />
                      </div>
                      <div className="absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 bg-emerald-400 rounded-full border-2 border-red-500"></div>
                    </div>
                    <div>
                      <h3 className="font-bold text-white text-sm tracking-wide">ElectroMart Assistant</h3>
                      <p className="text-[11px] text-red-100 flex items-center gap-1">
                        <Sparkles className="w-3 h-3" />
                        Trợ lý AI thông minh
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center self-center gap-1">
                    <button type="button" onClick={startNewConversation} aria-label="Bắt đầu cuộc trò chuyện mới" title="Cuộc trò chuyện mới" className="inline-flex h-11 w-11 items-center justify-center rounded-full text-white/70 transition-colors hover:bg-white/10 hover:text-white">
                      <RotateCcw className="w-4 h-4" />
                    </button>
                    <button type="button" onClick={() => setIsOpen(false)} aria-label="Thu nhỏ cửa sổ trò chuyện" className="inline-flex h-11 w-11 items-center justify-center rounded-full text-white/70 transition-colors hover:bg-white/10 hover:text-white">
                      <Minus className="w-4 h-4" />
                    </button>
                    <button type="button" onClick={() => setIsOpen(false)} aria-label="Đóng cửa sổ trò chuyện" className="inline-flex h-11 w-11 items-center justify-center rounded-full text-white/70 transition-colors hover:bg-white/10 hover:text-white">
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
              {/* Context bar */}
              <div className="bg-gradient-to-r from-red-50 to-rose-50 px-4 py-2 text-[11px] text-gray-600 flex items-center gap-2 border-b border-red-100">
                <ShoppingCart className="w-3.5 h-3.5 text-red-500" />
                <span className="truncate">
                  Đang xem: <strong className="text-gray-900">{currentContext.viewing}</strong>
                  <span className="mx-1.5 text-gray-300">·</span>
                  Giỏ hàng: <strong className="text-red-700">{currentContext.cartItems} sản phẩm</strong>
                </span>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 p-4 overflow-y-auto bg-gradient-to-b from-slate-50 to-white text-sm flex flex-col gap-3">
              {messages.map((msg) => (
                <div key={msg.id} className={`flex gap-2 ${msg.sender === 'user' ? 'justify-end' : 'items-end justify-start'}`}>
                  {msg.sender === 'ai' && (
                    <div className="w-7 h-7 rounded-full overflow-hidden shrink-0 ring-1 ring-red-100 shadow-sm self-end mb-1">
                      <img src={robotAvatar} alt="Bot" className="w-full h-full object-cover" />
                    </div>
                  )}
                  <div className="relative">
                    {/* Chat bubble tail for bot messages */}
                    {msg.sender === 'ai' && (
                      <div className="absolute bottom-2 -left-1.5 w-3 h-3 bg-white border-b border-l border-gray-100 rotate-45"></div>
                    )}
                    {msg.sender === 'user' && (
                      <div className="absolute bottom-2 -right-1.5 w-3 h-3 bg-red-500 rotate-45"></div>
                    )}
                    <div className={`relative p-3 max-w-[78%] ${
                      msg.sender === 'user'
                        ? 'bg-gradient-to-br from-red-600 to-red-500 text-white rounded-2xl rounded-br-sm shadow-md shadow-red-100'
                        : 'bg-white text-gray-700 border border-gray-100 rounded-2xl rounded-bl-sm shadow-sm'
                    }`}>
                      <div className="whitespace-pre-wrap leading-relaxed">{msg.text}</div>
                      {msg.answerMode === 'DATABASE_FALLBACK' && (
                        <div className="mt-2 text-[10px] font-medium text-amber-700">
                          Trả lời từ dữ liệu cửa hàng do AI đang tạm bận
                        </div>
                      )}
                      {msg.products && msg.products.length > 0 && (
                        <div className="mt-3 space-y-2">
                          {msg.products.map((product) => (
                            <a
                              key={product.id || product.slug || product.name}
                              href={product.isUsed
                                ? `/used-products/${product.slug || product.id}`
                                : `/products/${product.slug || product.id}`}
                              aria-label={`Xem sản phẩm ${product.name}`}
                              className="flex gap-2 rounded-xl border border-gray-100 bg-gray-50 p-2.5 text-left hover:bg-red-50 hover:border-red-100 transition-colors"
                            >
                              <ProductThumbnail src={product.imageUrl} />
                              <span className="min-w-0 flex-1">
                                <span className="block truncate text-xs font-bold text-gray-900">{product.name}</span>
                                <span className="block text-xs text-red-600 font-semibold mt-0.5">
                                  {Number(product.salePrice || product.price || 0).toLocaleString('vi-VN')}đ
                                </span>
                              </span>
                            </a>
                          ))}
                        </div>
                      )}
                      {msg.handover?.phone && (
                        <a
                          href={`tel:${msg.handover.phone.replace(/[\s.-]/g, '')}`}
                          className="mt-3 inline-flex min-h-11 items-center gap-2 rounded-xl bg-emerald-600 px-3 py-2 text-xs font-bold text-white transition-colors hover:bg-emerald-700"
                        >
                          <PhoneCall className="h-4 w-4" />
                          Gọi CSKH: {msg.handover.phone}
                        </a>
                      )}
                      {!msg.handover?.phone && msg.handover?.email && (
                        <a
                          href={`mailto:${msg.handover.email}`}
                          className="mt-3 inline-flex min-h-11 items-center gap-2 rounded-xl bg-emerald-600 px-3 py-2 text-xs font-bold text-white transition-colors hover:bg-emerald-700"
                        >
                          Liên hệ CSKH: {msg.handover.email}
                        </a>
                      )}
                      {msg.handover?.supportRequestCode && (
                        <div className="mt-2 text-[11px] font-semibold text-emerald-700">
                          Mã hỗ trợ: {msg.handover.supportRequestCode}
                        </div>
                      )}
                      {msg.sender === 'ai' && msg.responseId && (
                        <div className="mt-2 flex items-center gap-1 border-t border-gray-100 pt-2 text-[10px] text-gray-500">
                          <span className="mr-1">Câu trả lời hữu ích?</span>
                          <button
                            type="button"
                            aria-label="Câu trả lời hữu ích"
                            disabled={Boolean(msg.feedback)}
                            onClick={() => void handleFeedback(msg.id, msg.responseId!, true)}
                            className={`rounded p-1 transition-colors ${msg.feedback === 'helpful' ? 'bg-emerald-100 text-emerald-700' : 'hover:bg-gray-100'} disabled:cursor-default`}
                          >
                            <ThumbsUp className="h-3.5 w-3.5" />
                          </button>
                          <button
                            type="button"
                            aria-label="Câu trả lời chưa hữu ích"
                            disabled={Boolean(msg.feedback)}
                            onClick={() => void handleFeedback(msg.id, msg.responseId!, false)}
                            className={`rounded p-1 transition-colors ${msg.feedback === 'not_helpful' ? 'bg-rose-100 text-rose-700' : 'hover:bg-gray-100'} disabled:cursor-default`}
                          >
                            <ThumbsDown className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              {isTyping && (
                <div className="flex items-end gap-2 justify-start">
                  <div className="w-7 h-7 rounded-full overflow-hidden shrink-0 ring-1 ring-red-100 shadow-sm self-end mb-1">
                    <img src={robotAvatar} alt="Bot" className="w-full h-full object-cover" />
                  </div>
                  <div className="relative">
                    <div className="absolute bottom-2 -left-1.5 w-3 h-3 bg-white border-b border-l border-gray-100 rotate-45"></div>
                    <div className="relative bg-white px-4 py-3 rounded-2xl rounded-bl-sm border border-gray-100 shadow-sm flex items-center gap-1.5">
                      <span className="typing-dot w-2 h-2 bg-red-400 rounded-full" style={{ animationDelay: '0ms' }}></span>
                      <span className="typing-dot w-2 h-2 bg-red-300 rounded-full" style={{ animationDelay: '150ms' }}></span>
                      <span className="typing-dot w-2 h-2 bg-red-200 rounded-full" style={{ animationDelay: '300ms' }}></span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Quick Actions */}
            {messages.length === 1 && (
              <div className="px-3 py-2.5 bg-gradient-to-r from-slate-50 to-white flex flex-wrap gap-2 border-t border-gray-100 shrink-0">
                {quickActions.map((action) => (
                  <button type="button"
                    key={action.text}
                    onClick={() => handleSendMessage(action.text)}
                    className="min-h-11 rounded-full border border-red-100 bg-white px-3.5 py-2 text-xs font-semibold text-red-700 shadow-sm transition-all hover:border-red-200 hover:bg-red-50"
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            )}

            {/* Input */}
            <div className="px-3 pt-3 pb-1.5 bg-white border-t border-gray-100 flex items-center gap-2 shrink-0">
              <input
                aria-label="Nhập tin nhắn cho trợ lý AI"
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSendMessage(inputText)}
                placeholder="Hỏi bất cứ điều gì..."
                className="flex-1 bg-gray-50 rounded-full px-4 py-2.5 outline-none text-sm border border-gray-200 focus:border-red-300 focus:ring-2 focus:ring-red-100 transition-all placeholder:text-gray-500"
              />
              <button type="button"
                onClick={() => handleSendMessage(inputText)}
                aria-label="Gửi tin nhắn"
                className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-gradient-to-r from-red-600 to-red-500 text-white shadow-md shadow-red-200 transition-all hover:from-red-700 hover:to-red-600 disabled:opacity-40 disabled:shadow-none"
                disabled={!inputText.trim()}
              >
                <Send className="w-4 h-4" />
              </button>
            </div>

            {/* Powered by */}
            <div className="pb-2.5 pt-1 bg-white text-center shrink-0">
              <span className="text-[10px] text-gray-400">Được hỗ trợ bởi ElectroMart AI</span>
            </div>
            </m.div>
          )}
        </AnimatePresence>
      </LazyMotion>

      {/* Floating Button */}
      <button type="button"
        onClick={() => setIsOpen(!isOpen)}
        aria-label={isOpen ? 'Đóng trợ lý AI' : 'Mở trợ lý AI'}
        aria-expanded={isOpen}
        className="absolute bottom-0 right-0 group z-50"
      >
        <div className="relative">
          {/* Pulse ring */}
          {!isOpen && (
            <div className="absolute inset-0 rounded-full bg-red-500/30 animate-ping"></div>
          )}
          {/* Main button */}
          <div className={`relative inline-flex h-11 w-11 items-center justify-center rounded-full shadow-xl transition-all duration-300 md:h-14 md:w-14 lg:h-16 lg:w-16 ${
            isOpen
              ? 'bg-gradient-to-br from-red-600 to-red-500 scale-90'
              : 'bg-gradient-to-br from-red-600 to-rose-500 hover:scale-110 hover:shadow-2xl hover:shadow-red-300/40'
          }`}>
            {isOpen ? (
              <X className="w-6 h-6 text-white" />
            ) : (
              <img src={robotAvatar} alt="" className="h-8 w-8 rounded-full object-cover ring-1 ring-white/20 md:h-10 md:w-10 lg:h-12 lg:w-12" />
            )}
          </div>
          {/* Unread badge (when closed) */}
          {!isOpen && (
            <div className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full border-2 border-white bg-emerald-500 md:-right-1 md:-top-1 md:h-5 md:w-5">
              <span className="text-[8px] font-bold text-white md:text-[9px]">1</span>
            </div>
          )}
        </div>
      </button>
    </div>
  );
};
