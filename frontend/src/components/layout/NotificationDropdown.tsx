import React, { useState, useRef, useEffect } from 'react';
import { Bell, Package, Gift, ShieldAlert } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { apiDb } from '../../services/apiDb';
import { useAuth } from '../../context/AuthContext';

interface Notification {
  id: string;
  type: string;
  title: string;
  message: string;
  date: string;
  read: boolean;
}

export function NotificationDropdown() {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const { user } = useAuth();
  const [notifications, setNotifications] = useState<Notification[]>([]);

  useEffect(() => {
    const fetchNotifications = async () => {
      if (!user) {
        setNotifications([]);
        return;
      }

      try {
        const notifs = await apiDb.listNotifications();
        notifs.sort((a: any, b: any) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());
        setNotifications(notifs.map((data: any) => {
          return {
            id: data.id,
            type: data.type || 'order',
            title: data.title || '',
            message: data.message || '',
            date: new Date(data.createdAt).toLocaleString('vi-VN'),
            read: Boolean(data.read),
          };
        }));
      } catch (err) {
        console.error(err);
        setNotifications([]);
      }
    };

    fetchNotifications();
  }, [user]);

  const unreadCount = notifications.filter(n => !n.read).length;

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getIcon = (type: string) => {
    switch (type) {
      case 'order': return <Package className="w-4 h-4 text-primary" />;
      case 'loyalty': return <Gift className="w-4 h-4 text-yellow-500" />;
      case 'security': return <ShieldAlert className="w-4 h-4 text-red-500" />;
      default: return <Bell className="w-4 h-4 text-gray-500" />;
    }
  };

  const markAllRead = async () => {
    if (!user) return;
    try {
      await apiDb.markNotificationsRead();
      setNotifications(notifications.map(n => ({ ...n, read: true })));
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="flex flex-col items-center p-1 hover:text-white/85 relative transition-colors"
      >
        <Bell className="w-6 h-6" />
        <span className="mt-1 hidden lg:block text-xs">Thông báo</span>
        {unreadCount > 0 && <span className="absolute -top-1 -right-1 bg-yellow-400 text-black text-[10px] font-bold rounded-full h-4 w-4 flex items-center justify-center">{unreadCount}</span>}
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.95 }}
            transition={{ duration: 0.2 }}
            className="absolute md:top-[60px] top-[40px] md:-right-2 right-0 md:w-80 w-[280px] bg-white rounded-xl shadow-xl border border-gray-100 z-50 text-slate-800"
          >
            <div className="p-3 border-b border-gray-100 flex justify-between items-center bg-gray-50 rounded-t-xl">
              <h3 className="font-bold text-sm">Thông báo hệ thống</h3>
              {unreadCount > 0 && (
                <button onClick={markAllRead} className="text-[10px] text-blue-600 hover:underline">Đã đọc tất cả</button>
              )}
            </div>

            <div className="max-h-[300px] overflow-y-auto">
              {notifications.length > 0 ? notifications.map(notif => (
                <div key={notif.id} className={`p-3 border-b border-gray-50 flex gap-3 hover:bg-gray-50 transition-colors ${!notif.read ? 'bg-blue-50/30' : ''}`}>
                  <div className="mt-1 bg-white p-2 border border-gray-100 rounded-full h-8 w-8 flex items-center justify-center shrink-0">
                    {getIcon(notif.type)}
                  </div>
                  <div>
                    <h4 className="text-xs font-bold leading-tight mb-1">{notif.title}</h4>
                    <p className="text-[11px] text-gray-500 leading-snug mb-1">{notif.message}</p>
                    <p className="text-[9px] text-gray-400 font-mono">{notif.date}</p>
                  </div>
                  {!notif.read && <div className="w-2 h-2 bg-primary rounded-full mt-2 shrink-0"></div>}
                </div>
              )) : (
                <div className="p-8 text-center text-gray-400 text-xs">
                  Chưa có thông báo nào.
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
