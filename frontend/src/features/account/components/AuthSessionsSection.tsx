import { LogOut, ShieldCheck } from 'lucide-react';
import type { AuthSession } from '../types/accountDashboardTypes';

type AuthSessionsSectionProps = {
  authSessions: AuthSession[];
  onRevokeSession: (sessionId: string, isCurrent: boolean) => void;
};

export function AuthSessionsSection({ authSessions, onRevokeSession }: AuthSessionsSectionProps) {
  return (
    <section className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
      <div className="flex items-center gap-3 mb-5">
        <ShieldCheck className="w-6 h-6 text-[#d70018]" />
        <h3 className="font-bold text-gray-800">Phiên đăng nhập</h3>
      </div>
      {authSessions.length === 0 ? (
        <p className="text-sm text-gray-500">Chưa có dữ liệu phiên đăng nhập.</p>
      ) : (
        <div className="space-y-3">
          {authSessions.map(session => (
            <div key={session.id} className="flex flex-col gap-3 rounded-lg border border-slate-100 p-4 md:flex-row md:items-center md:justify-between">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <p className="truncate text-sm font-bold text-gray-800">{session.userAgent || 'Thiết bị không xác định'}</p>
                  {session.current && <span className="rounded bg-green-50 px-2 py-0.5 text-xs font-bold text-green-700">Hiện tại</span>}
                </div>
                <p className="mt-1 text-xs text-gray-500">IP: {session.ipAddress || 'unknown'} · Tạo lúc: {new Date(session.createdAt).toLocaleString('vi-VN')}</p>
              </div>
              <button
                type="button"
                onClick={() => onRevokeSession(session.id, session.current)}
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-red-200 px-3 py-2 text-sm font-bold text-red-600 hover:bg-red-50"
              >
                <LogOut className="w-4 h-4" /> Đăng xuất phiên này
              </button>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
