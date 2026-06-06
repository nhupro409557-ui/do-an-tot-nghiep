export type AdminNoticeType = 'success' | 'error' | 'info';

export type AdminNotice = {
  id: number;
  type: AdminNoticeType;
  title?: string;
  message: string;
};

export const ADMIN_NOTICE_EVENT = 'admin-notice';

export function notifyAdmin(message: string, type: AdminNoticeType = 'success', title?: string) {
  window.dispatchEvent(new CustomEvent<Omit<AdminNotice, 'id'>>(ADMIN_NOTICE_EVENT, {
    detail: { message, type, title },
  }));
}
