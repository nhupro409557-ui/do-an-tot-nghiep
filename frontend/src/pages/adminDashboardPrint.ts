type CurrencyFormatter = Pick<Intl.NumberFormat, 'format'>;

function escapeHtml(value: unknown) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function printOrderDocument(
  order: any,
  mode: 'invoice' | 'delivery',
  helpers: {
    currency: CurrencyFormatter;
    compactId: (id?: string) => string;
    statusLabel: Record<string, string>;
  },
) {
  const popup = window.open('', '_blank', 'width=900,height=700');
  if (!popup) return;
  const rows = Array.isArray(order.items) ? order.items : [];
  const title = mode === 'invoice' ? 'Hóa đơn bán hàng' : 'Phiếu giao hàng';
  const note = mode === 'invoice'
    ? `Tổng thanh toán: ${helpers.currency.format(Number(order.totalAmount || 0))}`
    : `Người nhận: ${order.recipientName || '-'} - ${order.recipientPhone || '-'}`;
  popup.document.write(`
      <html>
        <head><title>${escapeHtml(title)}</title><style>body{font-family:Arial,sans-serif;padding:24px;color:#0f172a}table{width:100%;border-collapse:collapse;margin-top:16px}th,td{border:1px solid #cbd5e1;padding:8px;text-align:left}h1{margin:0 0 8px}p{margin:4px 0}</style></head>
        <body>
          <h1>${escapeHtml(title)}</h1>
          <p>Mã đơn: ${escapeHtml(order.orderCode || helpers.compactId(order.id))}</p>
          <p>Trạng thái: ${escapeHtml(helpers.statusLabel[order.status] || order.status)}</p>
          <p>${escapeHtml(note)}</p>
          <p>Địa chỉ giao: ${escapeHtml(order.shippingAddress || '-')}</p>
          <table>
            <thead><tr><th>Sản phẩm</th><th>SL</th><th>Đơn giá</th><th>Thành tiền</th></tr></thead>
            <tbody>
              ${rows.map((item: any) => `<tr><td>${escapeHtml(item.productName || '-')}</td><td>${escapeHtml(item.quantity || 0)}</td><td>${escapeHtml(helpers.currency.format(Number(item.price || 0)))}</td><td>${escapeHtml(helpers.currency.format(Number(item.totalPrice || 0)))}</td></tr>`).join('')}
            </tbody>
          </table>
        </body>
      </html>
    `);
  popup.document.close();
  popup.focus();
  popup.print();
}
