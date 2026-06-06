import { AlertTriangle } from 'lucide-react';

type DeleteAccountSectionProps = {
  onOpenDeleteAccount: () => void;
};

export function DeleteAccountSection({ onOpenDeleteAccount }: DeleteAccountSectionProps) {
  return (
    <section className="bg-white rounded-xl shadow-sm border border-red-100 p-6">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-6 h-6 text-red-600 shrink-0" />
          <div>
            <h3 className="font-bold text-red-700">Xóa tài khoản</h3>
            <p className="text-sm text-gray-500 mt-1">Thao tác này sẽ xóa tài khoản và hồ sơ đang lưu trong bản demo.</p>
          </div>
        </div>
        <button onClick={onOpenDeleteAccount} className="px-4 py-3 rounded-lg border border-red-600 text-red-600 font-bold hover:bg-red-600 hover:text-white transition-colors">Xóa tài khoản</button>
      </div>
    </section>
  );
}
