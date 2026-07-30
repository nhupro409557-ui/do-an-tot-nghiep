import { useEffect, useState } from 'react';
import { BookOpenText, Edit, Save, X } from 'lucide-react';
import { useAuth } from '../../../context/AuthContext';
import { storeInfoApi, type StorePolicy } from '../../../services/storeInfoApi';
import { notifyAdmin } from '../../admin-shell/utils/adminNotice';


export function AdminStorePoliciesSection() {
  const { usePermission } = useAuth();
  const canUpdate = usePermission('store_info:update');
  const [policies, setPolicies] = useState<StorePolicy[]>([]);
  const [loading, setLoading] = useState(true);
  const [editingCode, setEditingCode] = useState<string | null>(null);
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [isActive, setIsActive] = useState(true);
  const [saving, setSaving] = useState(false);

  const loadPolicies = async () => {
    setLoading(true);
    try {
      setPolicies(await storeInfoApi.adminListStorePolicies());
    } catch (error) {
      console.error(error);
      notifyAdmin('Không thể tải danh sách chính sách cửa hàng.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadPolicies();
  }, []);

  const startEditing = (policy: StorePolicy) => {
    setEditingCode(policy.code);
    setTitle(policy.title);
    setContent(policy.content);
    setIsActive(policy.is_active);
  };

  const cancelEditing = () => {
    setEditingCode(null);
    setTitle('');
    setContent('');
  };

  const savePolicy = async () => {
    if (!editingCode || !title.trim() || !content.trim()) {
      notifyAdmin('Tên và nội dung chính sách không được để trống.');
      return;
    }
    setSaving(true);
    try {
      const updated = await storeInfoApi.adminUpdateStorePolicy(editingCode, {
        title: title.trim(),
        content: content.trim(),
        is_active: isActive,
      });
      setPolicies((current) => current.map((item) => (item.code === updated.code ? updated : item)));
      cancelEditing();
      notifyAdmin('Đã cập nhật chính sách cửa hàng.');
    } catch (error) {
      console.error(error);
      notifyAdmin('Không thể cập nhật chính sách cửa hàng.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <section className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex items-center gap-3 border-b border-slate-100 bg-slate-50/50 px-6 py-4">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-sky-50 text-sky-700">
          <BookOpenText className="h-5 w-5" />
        </div>
        <div>
          <h3 className="font-bold text-slate-900">Chính sách dùng cho chatbot</h3>
          <p className="text-xs text-slate-500">Chatbot đọc trực tiếp nội dung đang hoạt động và phiên bản mới nhất tại đây.</p>
        </div>
      </div>

      {loading ? (
        <p className="px-6 py-8 text-sm font-semibold text-slate-500">Đang tải chính sách...</p>
      ) : (
        <div className="divide-y divide-slate-100">
          {policies.map((policy) => {
            const editing = editingCode === policy.code;
            return (
              <article key={policy.code} className="space-y-3 px-6 py-5">
                {editing ? (
                  <>
                    <div className="grid gap-3 md:grid-cols-[1fr_auto]">
                      <input
                        value={title}
                        maxLength={150}
                        onChange={(event) => setTitle(event.target.value)}
                        className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-bold outline-none focus:border-[#d70018]"
                      />
                      <label className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                        <input
                          type="checkbox"
                          checked={isActive}
                          onChange={(event) => setIsActive(event.target.checked)}
                        />
                        Đang áp dụng
                      </label>
                    </div>
                    <textarea
                      value={content}
                      maxLength={5000}
                      rows={4}
                      onChange={(event) => setContent(event.target.value)}
                      className="w-full resize-y rounded-lg border border-slate-300 px-3 py-2 text-sm leading-6 outline-none focus:border-[#d70018]"
                    />
                    <div className="flex justify-end gap-2">
                      <button type="button" onClick={cancelEditing} className="inline-flex items-center gap-1 rounded-lg border border-slate-300 px-3 py-2 text-sm font-bold text-slate-700">
                        <X className="h-4 w-4" /> Hủy
                      </button>
                      <button type="button" disabled={saving} onClick={() => void savePolicy()} className="inline-flex items-center gap-1 rounded-lg bg-[#d70018] px-3 py-2 text-sm font-bold text-white disabled:opacity-50">
                        <Save className="h-4 w-4" /> {saving ? 'Đang lưu...' : 'Lưu'}
                      </button>
                    </div>
                  </>
                ) : (
                  <div className="flex items-start justify-between gap-4">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <h4 className="font-bold text-slate-900">{policy.title}</h4>
                        <span className={`rounded-full px-2 py-0.5 text-[11px] font-bold ${policy.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
                          {policy.is_active ? 'Đang áp dụng' : 'Tạm ẩn'}
                        </span>
                        <span className="text-[11px] text-slate-400">Phiên bản {policy.version}</span>
                      </div>
                      <p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-600">{policy.content}</p>
                    </div>
                    {canUpdate && (
                      <button type="button" onClick={() => startEditing(policy)} className="inline-flex shrink-0 items-center gap-1 rounded-lg border border-slate-300 px-3 py-2 text-sm font-bold text-slate-700 hover:text-[#d70018]">
                        <Edit className="h-4 w-4" /> Sửa
                      </button>
                    )}
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}
    </section>
  );
}
