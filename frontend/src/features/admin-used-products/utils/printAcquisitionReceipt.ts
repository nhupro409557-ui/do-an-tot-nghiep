import type { UsedProductIntake } from '../types';

const paymentLabels: Record<string, string> = {
  CASH: 'Tiền mặt',
  BANK_TRANSFER: 'Chuyển khoản',
  TRADE_IN_CREDIT: 'Bù trừ đơn đổi máy',
};

function escapeHtml(value: unknown) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#039;');
}

function formatDate(value?: string | null) {
  return value ? new Intl.DateTimeFormat('vi-VN', { dateStyle: 'short', timeStyle: 'short' }).format(new Date(value)) : '-';
}

export function printAcquisitionReceipt(intake: UsedProductIntake) {
  const popup = window.open('', '_blank', 'width=900,height=760');
  if (!popup) throw new Error('Trình duyệt đang chặn cửa sổ in phiếu thu mua.');
  const amount = new Intl.NumberFormat('vi-VN', { style: 'currency', currency: 'VND', maximumFractionDigits: 0 })
    .format(Number(intake.proposedAcquisitionPrice || 0));
  popup.document.write(`<!doctype html>
  <html lang="vi"><head><meta charset="utf-8"><title>Phiếu thu mua ${escapeHtml(intake.requestCode)}</title>
  <style>
    body{font-family:Arial,sans-serif;color:#0f172a;margin:36px;line-height:1.5}h1{text-align:center;font-size:22px;margin:0}.sub{text-align:center;color:#475569;margin:6px 0 28px}.grid{display:grid;grid-template-columns:1fr 1fr;gap:10px 28px}.row{border-bottom:1px dotted #94a3b8;padding:7px 0}.wide{grid-column:1/-1}.confirm{margin-top:22px;padding:12px;border:1px solid #94a3b8;border-radius:6px}.signatures{display:grid;grid-template-columns:1fr 1fr;text-align:center;margin-top:48px;gap:80px}.space{height:80px}.note{font-size:12px;color:#64748b;margin-top:30px}@media print{body{margin:18mm}.no-print{display:none}}
  </style></head><body>
  <h1>PHIẾU XÁC NHẬN THU MUA THIẾT BỊ CŨ</h1>
  <div class="sub">Mã hồ sơ: <strong>${escapeHtml(intake.requestCode)}</strong> · Thời điểm: ${escapeHtml(formatDate(intake.acquisitionPaidAt || intake.acceptedAt))}</div>
  <div class="grid">
    <div class="row"><strong>Người bán:</strong> ${escapeHtml(intake.sellerName || '-')}</div>
    <div class="row"><strong>Số điện thoại:</strong> ${escapeHtml(intake.sellerPhone || '-')}</div>
    <div class="row"><strong>Giấy tờ định danh:</strong> ${escapeHtml(intake.sellerIdentityNumber || '-')}</div>
    <div class="row"><strong>IMEI:</strong> ${escapeHtml(intake.imei)}</div>
    <div class="row wide"><strong>Địa chỉ:</strong> ${escapeHtml(intake.sellerAddress || '-')}</div>
    <div class="row wide"><strong>Thiết bị:</strong> ${escapeHtml(intake.productName)} ${escapeHtml([intake.colorName, intake.storage, intake.ram].filter(Boolean).join(' / '))}</div>
    <div class="row"><strong>Giá thu mua:</strong> ${escapeHtml(amount)}</div>
    <div class="row"><strong>Phương thức:</strong> ${escapeHtml(paymentLabels[intake.acquisitionPaymentMethod || ''] || intake.acquisitionPaymentMethod || '-')}</div>
    <div class="row wide"><strong>Mã tham chiếu:</strong> ${escapeHtml(intake.acquisitionPaymentReference || '-')}</div>
  </div>
  <div class="confirm">Người bán xác nhận thiết bị thuộc quyền sở hữu hợp pháp, không có tranh chấp, đã thoát tài khoản và đồng ý chuyển giao thiết bị theo mức giá nêu trên.</div>
  <div class="signatures"><div><strong>NGƯỜI BÁN</strong><div class="space"></div><div>${escapeHtml(intake.sellerName || '')}</div></div><div><strong>ĐẠI DIỆN CỬA HÀNG</strong><div class="space"></div><div>____________________</div></div></div>
  <div class="note">Phiếu phục vụ quản lý nội bộ và minh họa quy trình trong phạm vi đồ án; không thay thế hóa đơn hoặc chứng từ kế toán theo quy định chuyên ngành.</div>
  <script>window.onload=()=>{window.print();}</script></body></html>`);
  popup.document.close();
}
