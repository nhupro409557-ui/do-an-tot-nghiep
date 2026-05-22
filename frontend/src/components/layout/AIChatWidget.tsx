import React, { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { X, Send, Sparkles, ShoppingCart, Minus } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useCart } from '../../context/CartContext';
import robotAvatar from '../../assets/chatbot-robot.png';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8001/api/v1';

type Message = {
  id: string;
  sender: 'ai' | 'user';
  text: React.ReactNode;
  products?: any[];
};

const productSpecs: Record<string, any> = {
  'iPhone 15 Pro Max': {
    screen: '6.7 inch, Super Retina XDR OLED',
    cpu: 'Apple A17 Pro',
    ram: '8 GB',
    camera: 'Chinh 48 MP va phu 12 MP',
    price: '29.990.000d',
  },
  'S24 Ultra': {
    screen: '6.8 inch, Dynamic AMOLED 2X',
    cpu: 'Snapdragon 8 Gen 3 for Galaxy',
    ram: '12 GB',
    camera: 'Chinh 200 MP va phu 50 MP, 12 MP, 10 MP',
    price: '28.990.000d',
  },
};

export const AIChatWidget = () => {
  const { items } = useCart();
  const { user, userData } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [inputText, setInputText] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [conversationId] = useState(() => crypto.randomUUID());
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      sender: 'ai',
      text: 'Chào bạn! 👋 Mình là trợ lý AI của Echophone. Mình có thể tư vấn sản phẩm, chính sách, đơn hàng và điểm tích lũy cho bạn.',
    },
  ]);

  const currentContext = {
    viewing: items[0]?.name || 'Danh mục sản phẩm',
    cartItems: items.length,
  };

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen, isTyping]);

  const quickActions = [
    { label: '🛡️ Chính sách bảo hành', text: 'Chính sách bảo hành' },
    { label: '💻 Tư vấn laptop', text: 'Tư vấn laptop cho sinh viên IT' },
    { label: '📦 Tra đơn hàng', text: 'Đơn hàng của tôi ở đâu?' },
  ];

  const fallbackResponse = (userText: string) => {
    const textLower = userText.toLowerCase();

    if (textLower.includes('bao hanh') || textLower.includes('bảo hành')) {
      return 'San pham duoc bao hanh chinh hang 12 thang. Cac email xac nhan don hang va bao mat luon duoc gui de dam bao quyen loi cua ban.';
    }

    if (textLower.includes('giao hang') || textLower.includes('giao hàng')) {
      return 'Don hang tu 1.000.000d duoc ho tro giao hang. Don noi thanh co the xu ly nhanh tuy khu vuc.';
    }

    if (textLower.includes('so sanh') || textLower.includes('so sánh') || textLower.includes('s24')) {
      const prod1 = productSpecs['iPhone 15 Pro Max'];
      const prod2 = productSpecs['S24 Ultra'];
      return (
        <div className="text-sm">
          <p className="mb-2">
            Bang so sanh nhanh giua <strong>iPhone 15 Pro Max</strong> va <strong>S24 Ultra</strong>:
          </p>
          <div className="overflow-x-auto rounded-lg border border-gray-200">
            <table className="min-w-full text-xs text-left">
              <thead className="bg-gray-100">
                <tr>
                  <th className="px-2 py-1 border-b border-r">Thong so</th>
                  <th className="px-2 py-1 border-b border-r text-red-600">iPhone 15 Pro Max</th>
                  <th className="px-2 py-1 border-b text-red-500">S24 Ultra</th>
                </tr>
              </thead>
              <tbody className="bg-white">
                <tr><td className="px-2 py-1 border-b border-r font-medium bg-gray-50">Man hinh</td><td className="px-2 py-1 border-b border-r">{prod1.screen}</td><td className="px-2 py-1 border-b">{prod2.screen}</td></tr>
                <tr><td className="px-2 py-1 border-b border-r font-medium bg-gray-50">Chipset</td><td className="px-2 py-1 border-b border-r">{prod1.cpu}</td><td className="px-2 py-1 border-b">{prod2.cpu}</td></tr>
                <tr><td className="px-2 py-1 border-b border-r font-medium bg-gray-50">RAM</td><td className="px-2 py-1 border-b border-r">{prod1.ram}</td><td className="px-2 py-1 border-b">{prod2.ram}</td></tr>
                <tr><td className="px-2 py-1 border-b border-r font-medium bg-gray-50">Camera</td><td className="px-2 py-1 border-b border-r">{prod1.camera}</td><td className="px-2 py-1 border-b">{prod2.camera}</td></tr>
                <tr><td className="px-2 py-1 border-b border-r font-medium bg-gray-50">Gia</td><td className="px-2 py-1 border-b border-r font-bold text-red-600">{prod1.price}</td><td className="px-2 py-1 border-b font-bold text-red-500">{prod2.price}</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      );
    }

    return 'Minh chi ho tro tu van mua sam dien thoai, laptop, phu kien, don hang va chinh sach cua cua hang.';
  };

  const dynamicContext = () => ({
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
    const response = await fetch(`${API_BASE_URL}/ai-assistant/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(user?.uid ? { 'X-User-Id': user.uid } : {}),
      },
      body: JSON.stringify({
        conversation_id: conversationId,
        message: text,
        dynamic_context: dynamicContext(),
        model_provider: 'GEMINI',
        model_name: 'gemini-flash-latest',
      }),
    });

    if (!response.ok) {
      throw new Error('AI backend unavailable');
    }

    return await response.json() as { answer: string; recommended_products?: any[] };
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
        text: data.answer,
        products: data.recommended_products || [],
      }]);
    } catch {
      setMessages((prev) => [...prev, { id: (Date.now() + 1).toString(), sender: 'ai', text: fallbackResponse(text) }]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="fixed bottom-24 lg:bottom-6 right-4 md:right-6 z-[60]">
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 20, scale: 0.92 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.92 }}
            transition={{ type: 'spring', damping: 25, stiffness: 350 }}
            className="absolute bottom-20 right-0 w-[calc(100vw-2rem)] md:w-[400px] bg-white rounded-3xl shadow-2xl overflow-hidden flex flex-col h-[540px]"
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
                      <h3 className="font-bold text-white text-sm tracking-wide">Echo Assistant</h3>
                      <p className="text-[11px] text-red-100 flex items-center gap-1">
                        <Sparkles className="w-3 h-3" />
                        Trợ lý AI thông minh
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center self-center gap-1">
                    <button onClick={() => setIsOpen(false)} className="w-8 h-8 rounded-full inline-flex items-center justify-center text-white/70 hover:text-white hover:bg-white/10 transition-colors">
                      <Minus className="w-4 h-4" />
                    </button>
                    <button onClick={() => setIsOpen(false)} className="w-8 h-8 rounded-full inline-flex items-center justify-center text-white/70 hover:text-white hover:bg-white/10 transition-colors">
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
                      <div className="leading-relaxed">{msg.text}</div>
                      {msg.products && msg.products.length > 0 && (
                        <div className="mt-3 space-y-2">
                          {msg.products.map((product) => (
                            <a
                              key={product.id || product.slug || product.name}
                              href={`/products/${product.slug || product.id}`}
                              className="flex gap-2 rounded-xl border border-gray-100 bg-gray-50 p-2.5 text-left hover:bg-red-50 hover:border-red-100 transition-colors"
                            >
                              {product.imageUrl && (
                                <img src={product.imageUrl} alt={product.name} className="h-12 w-12 shrink-0 rounded-lg object-contain bg-white" />
                              )}
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
                      <span className="w-2 h-2 bg-red-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
                      <span className="w-2 h-2 bg-red-300 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
                      <span className="w-2 h-2 bg-red-200 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
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
                  <button
                    key={action.text}
                    onClick={() => handleSendMessage(action.text)}
                    className="text-xs font-semibold bg-white border border-red-100 text-red-700 px-3.5 py-2 rounded-full hover:bg-red-50 hover:border-red-200 transition-all shadow-sm"
                  >
                    {action.label}
                  </button>
                ))}
              </div>
            )}

            {/* Input */}
            <div className="px-3 pt-3 pb-1.5 bg-white border-t border-gray-100 flex items-center gap-2 shrink-0">
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSendMessage(inputText)}
                placeholder="Hỏi bất cứ điều gì..."
                className="flex-1 bg-gray-50 rounded-full px-4 py-2.5 outline-none text-sm border border-gray-200 focus:border-red-300 focus:ring-2 focus:ring-red-100 transition-all placeholder:text-gray-500"
              />
              <button
                onClick={() => handleSendMessage(inputText)}
                className="bg-gradient-to-r from-red-600 to-red-500 text-white w-10 h-10 rounded-full shrink-0 inline-flex items-center justify-center hover:from-red-700 hover:to-red-600 transition-all shadow-md shadow-red-200 disabled:opacity-40 disabled:shadow-none"
                disabled={!inputText.trim()}
              >
                <Send className="w-4 h-4" />
              </button>
            </div>

            {/* Powered by */}
            <div className="pb-2.5 pt-1 bg-white text-center shrink-0">
              <span className="text-[10px] text-gray-400">Powered by Echophone AI ✨</span>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Floating Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="absolute bottom-0 right-0 group z-50"
      >
        <div className="relative">
          {/* Pulse ring */}
          {!isOpen && (
            <div className="absolute inset-0 rounded-full bg-red-500/30 animate-ping"></div>
          )}
          {/* Main button */}
          <div className={`relative w-16 h-16 rounded-full shadow-xl inline-flex items-center justify-center transition-all duration-300 ${
            isOpen
              ? 'bg-gradient-to-br from-red-600 to-red-500 scale-90'
              : 'bg-gradient-to-br from-red-600 to-rose-500 hover:scale-110 hover:shadow-2xl hover:shadow-red-300/40'
          }`}>
            {isOpen ? (
              <X className="w-6 h-6 text-white" />
            ) : (
              <img src={robotAvatar} alt="Chat" className="w-12 h-12 rounded-full object-cover ring-1 ring-white/20" />
            )}
          </div>
          {/* Unread badge (when closed) */}
          {!isOpen && (
            <div className="absolute -top-1 -right-1 w-5 h-5 bg-emerald-500 rounded-full border-2 border-white flex items-center justify-center">
              <span className="text-[9px] font-bold text-white">1</span>
            </div>
          )}
        </div>
      </button>
    </div>
  );
};
