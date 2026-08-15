import React, { useEffect, useMemo, useState } from 'react';
import { AdminBadge, AdminPanel, AdminTable, SearchBox } from '../../admin-shell/components/AdminDashboardParts';
import { CheckCircle2, Download, Eye, FileSpreadsheet, FileText, PackageCheck, Pencil, Plus, Printer, RotateCcw, ScanLine, Trash2, XCircle } from 'lucide-react';
import { compactId, currency } from '../../admin-shell/components/AdminDashboardConfig';
import { adminInventoryApi } from '../services/adminInventoryApi';
import PurchaseOrdersPanel from './PurchaseOrdersPanel';
import ReceiptQualityModal from './ReceiptQualityModal';
import { resolveImageUrl } from '../../../services/productMedia';

type AdminInventoryReceiptsTabProps = Record<string, any>;

const receiptStatusLabel: Record<string, string> = {
  DRAFT: 'Nháp',
  PROCESSING_IMEI: 'Đang nhập IMEI/Serial',
  PENDING_APPROVAL: 'Chờ duyệt',
  PENDING_SHORTAGE_APPROVAL: 'Chờ duyệt thiếu IMEI/Serial',
  APPROVED: 'Đã duyệt',
  COMPLETED: 'Hoàn tất',
  CANCELLED: 'Đã hủy',
  REVERSED: 'Đã đảo phiếu',
};

const receiptStatusTone: Record<string, any> = {
  DRAFT: 'slate',
  PROCESSING_IMEI: 'blue',
  PENDING_APPROVAL: 'amber',
  PENDING_SHORTAGE_APPROVAL: 'amber',
  APPROVED: 'blue',
  COMPLETED: 'green',
  CANCELLED: 'red',
  REVERSED: 'amber',
};

const qualityStatusLabel: Record<string, string> = {
  PENDING: 'Chờ kiểm tra',
  PASSED: 'Đạt',
  FAILED: 'Không đạt',
};

const qualityStatusTone: Record<string, any> = {
  PENDING: 'amber',
  PASSED: 'green',
  FAILED: 'red',
};

const attachmentTypeOptions = [
  ['INVOICE', 'Hóa đơn'],
  ['DELIVERY_NOTE', 'Phiếu giao hàng'],
  ['GOODS_PHOTO', 'Ảnh hàng hóa'],
  ['OTHER', 'Khác'],
];

const receiptReasonLabel: Record<string, string> = {
  NK_MUA: 'Nhập mua từ nhà cung cấp',
  NK_TRA_NCC: 'Nhà cung cấp trả lại hàng',
  NK_KH_TRA: 'Khách hàng trả hàng',
  NK_BH: 'Nhập bảo hành',
  NK_DIEUCHINH: 'Điều chỉnh tăng tồn kho',
  NK_CHUYEN: 'Nhập từ kho khác',
  NK_SANXUAT: 'Nhập thành phẩm',
  NK_KHOI_TAO: 'Nhập kho khởi tạo',
  NK_KHAC: 'Nhập khác',
};

function formatReceiptReason(code: string | null | undefined) {
  const normalized = String(code || 'NK_MUA').toUpperCase();
  const safeCode = receiptReasonLabel[normalized] ? normalized : 'NK_MUA';
  return `${safeCode} - ${receiptReasonLabel[safeCode]}`;
}

function formatAuditActor(value: string | null | undefined, label?: string | null) {
  if (label) return label;
  return value ? compactId(value) : '-';
}

function escapeHtml(value: unknown) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function formatReceiptDate(value: string | null | undefined) {
  const date = value ? new Date(value) : new Date();
  if (Number.isNaN(date.getTime())) return '-';
  return `Ngày ${String(date.getDate()).padStart(2, '0')} tháng ${String(date.getMonth() + 1).padStart(2, '0')} năm ${date.getFullYear()}`;
}

function formatReceiptNumber(value: number) {
  return Number(value || 0).toLocaleString('vi-VN');
}

function receiptVariantDescription(line: any) {
  return [line?.variantColor, line?.variantConfiguration].map((item) => String(item || '').trim()).filter(Boolean).join(' - ');
}

function amountInVietnamese(value: number) {
  const units = ['', 'nghìn', 'triệu', 'tỷ'];
  const digits = ['không', 'một', 'hai', 'ba', 'bốn', 'năm', 'sáu', 'bảy', 'tám', 'chín'];
  const readTriple = (num: number, full = false) => {
    const hundred = Math.floor(num / 100);
    const ten = Math.floor((num % 100) / 10);
    const one = num % 10;
    const parts: string[] = [];
    if (hundred > 0 || full) parts.push(`${digits[hundred]} trăm`);
    if (ten > 1) {
      parts.push(`${digits[ten]} mươi`);
      if (one === 1) parts.push('mốt');
      else if (one === 5) parts.push('lăm');
      else if (one > 0) parts.push(digits[one]);
    } else if (ten === 1) {
      parts.push('mười');
      if (one === 5) parts.push('lăm');
      else if (one > 0) parts.push(digits[one]);
    } else if (one > 0) {
      if (hundred > 0 || full) parts.push('lẻ');
      parts.push(digits[one]);
    }
    return parts.join(' ');
  };
  const rounded = Math.round(Number(value || 0));
  if (rounded <= 0) return 'Không đồng.';
  const groups: number[] = [];
  let current = rounded;
  while (current > 0) {
    groups.push(current % 1000);
    current = Math.floor(current / 1000);
  }
  const words = groups
    .map((group, index) => {
      if (group === 0) return '';
      const full = index < groups.length - 1 && group < 100;
      return `${readTriple(group, full)} ${units[index]}`.trim();
    })
    .filter(Boolean)
    .reverse()
    .join(' ');
  return `${words.charAt(0).toUpperCase()}${words.slice(1)} đồng.`;
}

function buildReceiptDocumentHtml(receipt: any, lineSummaries: any[], isOfficialReceipt: boolean) {
  const totalCost = Number(receipt?.totalCost || lineSummaries.reduce((sum, item) => sum + item.unitCost * item.received, 0));
  const receiptDate = formatReceiptDate(receipt?.postedAt || receipt?.createdAt);
  const status = receipt?.status || 'COMPLETED';
  const rows = lineSummaries.map((summary, index) => `
    <tr>
      <td class="center">${index + 1}</td>
      <td>
        <div>${escapeHtml(summary.line.productName || '-')}</div>
        ${receiptVariantDescription(summary.line) ? `<div class="muted">${escapeHtml(receiptVariantDescription(summary.line))}</div>` : ''}
      </td>
      <td>${escapeHtml(summary.line.variantSku || summary.line.sku || compactId(summary.line.productId))}</td>
      <td class="center">${escapeHtml(summary.line.unitName || 'Cái')}</td>
      <td class="right">${formatReceiptNumber(summary.planned)}</td>
      <td class="right">${formatReceiptNumber(summary.received)}</td>
      <td class="right">${formatReceiptNumber(summary.unitCost)}</td>
      <td class="right">${formatReceiptNumber(summary.unitCost * summary.received)}</td>
    </tr>
  `).join('');
  const totalPlanned = lineSummaries.reduce((sum, item) => sum + item.planned, 0);
  const totalReceived = lineSummaries.reduce((sum, item) => sum + item.received, 0);
  return `<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Phiếu nhập kho ${escapeHtml(receipt?.referenceCode || '')}</title>
  <style>
    @page { size: A4 portrait; margin: 12mm; }
    * { box-sizing: border-box; }
    body { margin: 0; color: #111; background: #fff; font-family: "Times New Roman", Times, serif; font-size: 13px; line-height: 1.35; }
    .page { width: 100%; padding: 4px 2px; }
    .header { display: grid; grid-template-columns: 1fr; gap: 16px; }
    .company { font-weight: 700; text-transform: uppercase; }
    .form-code { text-align: center; }
    .title { margin-top: 14px; text-align: center; }
    .title-main { font-size: 22px; font-weight: 700; }
    .receipt-date { margin-top: 2px; font-style: italic; font-weight: 700; }
    .info { margin-top: 14px; }
    .info-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
    table { width: 100%; border-collapse: collapse; margin-top: 8px; page-break-inside: auto; }
    tr { page-break-inside: avoid; page-break-after: auto; }
    th, td { border: 1px solid #111; padding: 4px 5px; vertical-align: top; }
    th { text-align: center; font-weight: 700; }
    .center { text-align: center; }
    .right { text-align: right; }
    .bold { font-weight: 700; }
    .muted { font-size: 12px; }
    .amount-text { margin-top: 10px; }
    .signature-date { margin-top: 12px; text-align: right; font-style: italic; }
    .signatures { margin-top: 8px; display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; text-align: center; }
    .signature-name { margin-top: 52px; }
    .signature-name.short { margin-top: 36px; }
  </style>
</head>
<body>
  <div class="page">
    <div class="header">
      <div>
        <div class="company">ELECTROMART VIỆT NAM</div>
        <div>Hệ thống bán lẻ điện thoại, laptop và phụ kiện công nghệ</div>
        <div>Địa chỉ: ..............................................................</div>
        <div>Điện thoại: ...........................................................</div>
      </div>
    </div>
    <div class="title">
      <div class="title-main">PHIẾU NHẬP KHO</div>
      <div class="receipt-date">${escapeHtml(receiptDate)}</div>
      <div>Số: ${escapeHtml(receipt?.referenceCode || '-')}</div>
      ${!isOfficialReceipt ? `<div style="margin-top:4px;font-weight:700;">Phiếu nhập tạm - ${escapeHtml(receiptStatusLabel[status] || status)}</div>` : ''}
    </div>
    <div class="info">
      <div>- Người giao hàng / Nhà cung cấp: <b>${escapeHtml(receipt?.supplierName || '-')}</b></div>
      <div>- Theo chứng từ / Lý do nhập: ${escapeHtml(formatReceiptReason(receipt?.receiptReasonCode))}</div>
      <div class="info-grid">
        <div>- Nhập tại kho: <b>${escapeHtml(receipt?.targetLocationName || 'Kho chính')}</b></div>
        <div>Địa điểm: ........................................................</div>
      </div>
      <div>- Ghi chú: ${escapeHtml(receipt?.note || '-')}</div>
    </div>
    <table>
      <thead>
        <tr>
          <th style="width:46px">STT</th>
          <th>Tên, nhãn hiệu, quy cách phẩm chất sản phẩm, hàng hóa</th>
          <th style="width:92px">Mã số</th>
          <th style="width:58px">Đơn vị tính</th>
          <th style="width:72px">Theo chứng từ</th>
          <th style="width:72px">Thực nhập</th>
          <th style="width:92px">Đơn giá</th>
          <th style="width:104px">Thành tiền</th>
        </tr>
      </thead>
      <tbody>
        ${rows || '<tr><td colspan="8" class="center">Phiếu chưa có dòng sản phẩm.</td></tr>'}
        <tr>
          <td></td>
          <td class="center bold">Cộng</td>
          <td></td>
          <td></td>
          <td class="right bold">${formatReceiptNumber(totalPlanned)}</td>
          <td class="right bold">${formatReceiptNumber(totalReceived)}</td>
          <td></td>
          <td class="right bold">${formatReceiptNumber(totalCost)}</td>
        </tr>
      </tbody>
    </table>
    <div class="amount-text">- Tổng số tiền (Viết bằng chữ): <b><i>${escapeHtml(amountInVietnamese(totalCost))}</i></b></div>
    <div>- Số chứng từ gốc kèm theo: ..............................................................</div>
    <div class="signature-date">${escapeHtml(receiptDate)}</div>
    <div class="signatures">
      <div><b>Người lập phiếu</b><br><i>(Ký, họ tên)</i><div class="signature-name">${escapeHtml(formatAuditActor(receipt?.createdBy, receipt?.createdByName))}</div></div>
      <div><b>Người giao hàng</b><br><i>(Ký, họ tên)</i><div class="signature-name">${escapeHtml(receipt?.supplierName || '')}</div></div>
      <div><b>Thủ kho</b><br><i>(Ký, họ tên)</i><div class="signature-name">${escapeHtml(formatAuditActor(receipt?.postedBy, receipt?.postedByName))}</div></div>
      <div><b>Kế toán trưởng</b><br><i>(Hoặc bộ phận có nhu cầu nhập)</i><br><i>(Ký, họ tên)</i><div class="signature-name short">${escapeHtml(formatAuditActor(receipt?.approvedBy, receipt?.approvedByName))}</div></div>
    </div>
  </div>
</body>
</html>`;
}

function safeReceiptFileName(receipt: any, extension: 'doc' | 'html') {
  const code = String(receipt?.referenceCode || 'phieu-nhap-kho')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .replace(/Đ/g, 'D')
    .replace(/[^a-zA-Z0-9_-]+/g, '-')
    .replace(/^-+|-+$/g, '') || 'phieu-nhap-kho';
  return `${code}.${extension}`;
}

function printReceiptDocument(receipt: any, lineSummaries: any[], isOfficialReceipt: boolean) {
  const popup = window.open('', '_blank', 'width=980,height=720');
  if (!popup) {
    window.alert('Trình duyệt đang chặn cửa sổ in. Vui lòng cho phép popup để xuất PDF.');
    return;
  }
  popup.document.open();
  popup.document.write(buildReceiptDocumentHtml(receipt, lineSummaries, isOfficialReceipt));
  popup.document.close();
  popup.focus();
  popup.setTimeout(() => popup.print(), 300);
}

function exportReceiptWord(receipt: any, lineSummaries: any[], isOfficialReceipt: boolean) {
  const html = buildReceiptDocumentHtml(receipt, lineSummaries, isOfficialReceipt);
  const blob = new Blob(['\ufeff', html], { type: 'application/msword;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = safeReceiptFileName(receipt, 'doc');
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

async function downloadReceiptDocument(receipt: any, format: 'pdf' | 'docx') {
  const referenceCode = String(receipt?.referenceCode || '').trim();
  if (!referenceCode) return;
  const blob = await adminInventoryApi.adminExportReceiptDocument(referenceCode, format);
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = safeReceiptFileName(receipt, format === 'pdf' ? 'html' : 'html').replace(/\.html$/, `.${format}`);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function PrintableReceipt({ receipt, lineSummaries, isOfficialReceipt }: { receipt: any; lineSummaries: any[]; isOfficialReceipt: boolean }) {
  const totalCost = Number(receipt?.totalCost || lineSummaries.reduce((sum, item) => sum + item.unitCost * item.received, 0));
  const receiptDate = formatReceiptDate(receipt?.postedAt || receipt?.createdAt);
  const status = receipt?.status || 'COMPLETED';
  return (
    <section className="receipt-print">
      <style>{`
        .receipt-print { display: none; }
        @media print {
          @page { size: A4 portrait; margin: 12mm; }
          body { background: #fff !important; }
          body * { visibility: hidden !important; }
          .receipt-print, .receipt-print * { visibility: visible !important; }
          .receipt-print { display: block !important; position: absolute; inset: 0; color: #111; font-family: "Times New Roman", Times, serif; font-size: 13px; line-height: 1.35; }
          .receipt-screen { display: none !important; }
          .receipt-print table { width: 100%; border-collapse: collapse; }
          .receipt-print th, .receipt-print td { border: 1px solid #111; padding: 4px 5px; vertical-align: top; }
          .receipt-print th { text-align: center; font-weight: 700; }
          .receipt-print .no-border td { border: 0; }
        }
      `}</style>
      <div style={{ padding: '4px 2px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: 16 }}>
          <div>
            <div style={{ fontWeight: 700, textTransform: 'uppercase' }}>ELECTROMART VIỆT NAM</div>
            <div>Hệ thống bán lẻ điện thoại, laptop và phụ kiện công nghệ</div>
            <div>Địa chỉ: ..............................................................</div>
            <div>Điện thoại: ...........................................................</div>
          </div>
        </div>

        <div style={{ marginTop: 14, textAlign: 'center' }}>
          <div style={{ fontSize: 22, fontWeight: 700 }}>PHIẾU NHẬP KHO</div>
          <div style={{ marginTop: 2, fontStyle: 'italic', fontWeight: 700 }}>{receiptDate}</div>
          <div>Số: {receipt?.referenceCode || '-'}</div>
          {!isOfficialReceipt && <div style={{ marginTop: 4, fontWeight: 700 }}>Phiếu nhập tạm - {receiptStatusLabel[status] || status}</div>}
        </div>

        <div style={{ marginTop: 14 }}>
          <div>- Người giao hàng / Nhà cung cấp: <b>{receipt?.supplierName || '-'}</b></div>
          <div>- Theo chứng từ / Lý do nhập: {formatReceiptReason(receipt?.receiptReasonCode)}</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>- Nhập tại kho: <b>{receipt?.targetLocationName || 'Kho chính'}</b></div>
            <div>Địa điểm: ........................................................</div>
          </div>
          <div>- Ghi chú: {receipt?.note || '-'}</div>
        </div>

        <table style={{ marginTop: 8 }}>
          <thead>
            <tr>
              <th style={{ width: 46 }}>STT</th>
              <th>Tên, nhãn hiệu, quy cách phẩm chất sản phẩm, hàng hóa</th>
              <th style={{ width: 92 }}>Mã số</th>
              <th style={{ width: 58 }}>Đơn vị tính</th>
              <th style={{ width: 72 }}>Theo chứng từ</th>
              <th style={{ width: 72 }}>Thực nhập</th>
              <th style={{ width: 92 }}>Đơn giá</th>
              <th style={{ width: 104 }}>Thành tiền</th>
            </tr>
          </thead>
          <tbody>
            {lineSummaries.map((summary, index) => (
              <tr key={summary.line.id || `${summary.line.productId}-${summary.line.variantId || index}`}>
                <td style={{ textAlign: 'center' }}>{index + 1}</td>
                <td>
                  <div>{summary.line.productName || '-'}</div>
                  {receiptVariantDescription(summary.line) && <div style={{ fontSize: 12 }}>{receiptVariantDescription(summary.line)}</div>}
                </td>
                <td>{summary.line.variantSku || summary.line.sku || compactId(summary.line.productId)}</td>
                <td style={{ textAlign: 'center' }}>{summary.line.unitName || 'Cái'}</td>
                <td style={{ textAlign: 'right' }}>{formatReceiptNumber(summary.planned)}</td>
                <td style={{ textAlign: 'right' }}>{formatReceiptNumber(summary.received)}</td>
                <td style={{ textAlign: 'right' }}>{formatReceiptNumber(summary.unitCost)}</td>
                <td style={{ textAlign: 'right' }}>{formatReceiptNumber(summary.unitCost * summary.received)}</td>
              </tr>
            ))}
            <tr>
              <td />
              <td style={{ textAlign: 'center', fontWeight: 700 }}>Cộng</td>
              <td />
              <td />
              <td style={{ textAlign: 'right', fontWeight: 700 }}>{formatReceiptNumber(lineSummaries.reduce((sum, item) => sum + item.planned, 0))}</td>
              <td style={{ textAlign: 'right', fontWeight: 700 }}>{formatReceiptNumber(lineSummaries.reduce((sum, item) => sum + item.received, 0))}</td>
              <td />
              <td style={{ textAlign: 'right', fontWeight: 700 }}>{formatReceiptNumber(totalCost)}</td>
            </tr>
          </tbody>
        </table>

        <div style={{ marginTop: 10 }}>- Tổng số tiền (Viết bằng chữ): <b><i>{amountInVietnamese(totalCost)}</i></b></div>
        <div>- Số chứng từ gốc kèm theo: ..............................................................</div>

        <div style={{ marginTop: 12, textAlign: 'right', fontStyle: 'italic' }}>{receiptDate}</div>
        <div style={{ marginTop: 8, display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 8, textAlign: 'center' }}>
          <div><b>Người lập phiếu</b><br /><i>(Ký, họ tên)</i><div style={{ marginTop: 52 }}>{formatAuditActor(receipt?.createdBy, receipt?.createdByName)}</div></div>
          <div><b>Người giao hàng</b><br /><i>(Ký, họ tên)</i><div style={{ marginTop: 52 }}>{receipt?.supplierName || ''}</div></div>
          <div><b>Thủ kho</b><br /><i>(Ký, họ tên)</i><div style={{ marginTop: 52 }}>{formatAuditActor(receipt?.postedBy, receipt?.postedByName)}</div></div>
          <div><b>Kế toán trưởng</b><br /><i>(Hoặc bộ phận có nhu cầu nhập)</i><br /><i>(Ký, họ tên)</i><div style={{ marginTop: 36 }}>{formatAuditActor(receipt?.approvedBy, receipt?.approvedByName)}</div></div>
        </div>
      </div>
    </section>
  );
}

function ReceiptDetailModal({
  receipt,
  onClose,
  uploadFiles,
  onAttachmentsUpdated,
  isSuperAdmin,
}: {
  receipt: any;
  onClose: () => void;
  uploadFiles?: (files: FileList | null | File[], folder?: string) => Promise<string[]>;
  onAttachmentsUpdated?: (patch: any) => void | Promise<void>;
  isSuperAdmin?: boolean;
}) {
  const lines = receipt?.lines || [];
  const status = receipt?.status || 'COMPLETED';
  const [activeTab, setActiveTab] = useState<'info' | 'identifiers'>('info');
  const [selectedLineId, setSelectedLineId] = useState<string | null>(null);
  const [attachmentDrafts, setAttachmentDrafts] = useState<any[]>(() => {
    const pending = Array.isArray(receipt?.pendingAttachments) ? receipt.pendingAttachments : [];
    return pending.length > 0 ? pending : Array.isArray(receipt?.attachments) ? receipt.attachments : [];
  });
  const [isEditingAttachments, setIsEditingAttachments] = useState(false);
  const [isSavingAttachments, setIsSavingAttachments] = useState(false);
  const [isUploadingAttachment, setIsUploadingAttachment] = useState(false);

  useEffect(() => {
    const pending = Array.isArray(receipt?.pendingAttachments) ? receipt.pendingAttachments : [];
    setAttachmentDrafts(pending.length > 0 ? pending : Array.isArray(receipt?.attachments) ? receipt.attachments : []);
    setIsEditingAttachments(false);
  }, [receipt]);

  function normalizeIdentifierList(value: any): string[] {
    if (Array.isArray(value)) return value.map((item) => String(item).trim()).filter(Boolean);
    if (typeof value === 'string' && value.trim()) {
      try {
        const parsed = JSON.parse(value);
        if (Array.isArray(parsed)) return parsed.map((item) => String(item).trim()).filter(Boolean);
      } catch {
        return value.split(/[\s,;]+/).map((item) => item.trim()).filter(Boolean);
      }
    }
    return [];
  }

  function buildIdentifierStatus(label: 'IMEI' | 'Serial', count: number, planned: number) {
    if (planned <= 0) return label + ': không yêu cầu';
    if (count >= planned) return 'Đủ ' + label;
    return 'Thiếu ' + (planned - count) + ' ' + label;
  }

  const lineSummaries = lines.map((line: any) => {
    const planned = Number(line.plannedQuantity || line.quantity || 0);
    const imeis = normalizeIdentifierList(line.imeis);
    const secondaryImeis = normalizeIdentifierList(line.secondaryImeis);
    const serialNumbers = normalizeIdentifierList(line.serialNumbers);
    const tracksImei = Boolean(line.tracksImei);
    const tracksSerialNumber = Boolean(line.tracksSerialNumber);
    const tracksIdentifier = tracksImei || tracksSerialNumber;
    const identifierCounts = [];
    if (tracksImei) identifierCounts.push(imeis.length);
    if (tracksSerialNumber) identifierCounts.push(serialNumbers.length);
    const received = tracksIdentifier ? Math.min(...identifierCounts) : Number(line.receivedQuantity ?? line.quantity ?? 0);
    const missing = Math.max(planned - received, 0);
    const unitCost = Number(line.unitCost || 0);
    const identifierStatus = [
      tracksImei ? buildIdentifierStatus('IMEI', imeis.length, planned) : null,
      tracksSerialNumber ? buildIdentifierStatus('Serial', serialNumbers.length, planned) : null,
    ].filter(Boolean).join(' / ') || 'Không quản lý mã định danh';
    return { line, planned, received, missing, unitCost, imeis, secondaryImeis, serialNumbers, tracksImei, tracksSerialNumber, tracksIdentifier, identifierStatus };
  });
  const needsIdentifier = lineSummaries.some((item: any) => item.tracksIdentifier);
  const hasMissingIdentifier = lineSummaries.some((item: any) => item.tracksIdentifier && item.missing > 0);
  const isOfficialReceipt = status === 'COMPLETED' && (!needsIdentifier || !hasMissingIdentifier);
  const identifierRows = lineSummaries.flatMap(({ line, imeis, secondaryImeis, serialNumbers }: any) => [
    ...imeis.map((value: string) => ({ line, lineId: String(line.id || `${line.productId}-${line.variantId || 'product'}`), type: 'IMEI', value })),
    ...secondaryImeis.map((value: string) => ({ line, lineId: String(line.id || `${line.productId}-${line.variantId || 'product'}`), type: 'IMEI2', value })),
    ...serialNumbers.map((value: string) => ({ line, lineId: String(line.id || `${line.productId}-${line.variantId || 'product'}`), type: 'Serial', value })),
  ]);
  const selectedLine = selectedLineId
    ? lineSummaries.find((item: any) => String(item.line.id || `${item.line.productId}-${item.line.variantId || 'product'}`) === selectedLineId)
    : null;
  const visibleIdentifierRows = selectedLineId
    ? identifierRows.filter((item: any) => item.lineId === selectedLineId)
    : identifierRows;
  const pendingAttachments = Array.isArray(receipt?.pendingAttachments) ? receipt.pendingAttachments : [];
  const hasPendingAttachments = pendingAttachments.length > 0;

  function openIdentifierTab(summary: any) {
    setSelectedLineId(String(summary.line.id || `${summary.line.productId}-${summary.line.variantId || 'product'}`));
    setActiveTab('identifiers');
  }

  function updateAttachmentDraft(index: number, patch: any) {
    setAttachmentDrafts((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, ...patch } : item));
  }

  function addAttachmentDraft() {
    setAttachmentDrafts((current) => [...current, { type: 'INVOICE', name: '', url: '', note: '' }]);
    setIsEditingAttachments(true);
  }

  function removeAttachmentDraft(index: number) {
    setAttachmentDrafts((current) => current.filter((_, itemIndex) => itemIndex !== index));
    setIsEditingAttachments(true);
  }

  async function handleAttachmentUpload(files: FileList | null) {
    if (!files || files.length === 0 || typeof uploadFiles !== 'function') return;
    setIsUploadingAttachment(true);
    try {
      const urls = await uploadFiles(files, 'inventory');
      if (urls.length > 0) {
        setAttachmentDrafts((current) => [
          ...current,
          ...urls.map((url: string, index: number) => ({
            type: files[index]?.type?.startsWith('image/') ? 'GOODS_PHOTO' : 'OTHER',
            name: files[index]?.name || 'Chứng từ nhập hàng',
            url,
            note: '',
          })),
        ]);
        setIsEditingAttachments(true);
      }
    } finally {
      setIsUploadingAttachment(false);
    }
  }

  async function saveAttachmentDrafts() {
    const attachments = attachmentDrafts
      .filter((item: any) => String(item.name || '').trim() || String(item.url || '').trim())
      .map((item: any) => ({
        type: item.type || 'OTHER',
        name: String(item.name || '').trim(),
        url: String(item.url || '').trim(),
        note: String(item.note || '').trim() || null,
      }));
    if (attachments.some((item: any) => !item.name || !item.url)) {
      window.alert('Mỗi chứng từ cần có tên và đường dẫn file.');
      return;
    }
    setIsSavingAttachments(true);
    try {
      const result = await adminInventoryApi.adminUpdateReceiptAttachments(receipt.referenceCode, { attachments });
      setAttachmentDrafts(result.pendingAttachments || attachments);
      setIsEditingAttachments(false);
      await onAttachmentsUpdated?.({
        attachments: result.attachments || receipt.attachments || [],
        pendingAttachments: result.pendingAttachments || attachments,
        attachmentApprovalStatus: result.attachmentApprovalStatus || 'PENDING',
        attachmentApprovalNote: result.attachmentApprovalNote || null,
      });
    } finally {
      setIsSavingAttachments(false);
    }
  }

  async function decideAttachmentDrafts(approve: boolean) {
    const note = approve ? null : window.prompt('Nhập lý do từ chối chứng từ:')?.trim() || null;
    if (!approve && !note) return;
    setIsSavingAttachments(true);
    try {
      const result = await adminInventoryApi.adminDecideReceiptAttachments(receipt.referenceCode, { approve, note });
      setAttachmentDrafts(result.attachments || []);
      setIsEditingAttachments(false);
      await onAttachmentsUpdated?.({
        attachments: result.attachments || [],
        pendingAttachments: result.pendingAttachments || [],
        attachmentApprovalStatus: result.attachmentApprovalStatus,
        attachmentApprovalNote: result.attachmentApprovalNote || null,
      });
    } finally {
      setIsSavingAttachments(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/55 px-4 py-6 backdrop-blur-sm">
      <PrintableReceipt receipt={receipt} lineSummaries={lineSummaries} isOfficialReceipt={isOfficialReceipt} />
      <div className="w-full max-w-6xl overflow-hidden rounded-lg bg-white shadow-2xl">
        <div className="receipt-screen sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-slate-200 bg-white px-5 py-4">
          <div>
            <h3 className="text-lg font-bold text-slate-950">Xem phiếu nhập kho</h3>
            <p className="mt-1 font-mono text-sm font-bold text-slate-600">{receipt?.referenceCode || '-'}</p>
          </div>
          <div className="flex items-center gap-2">
            <button type="button" onClick={() => void downloadReceiptDocument(receipt, 'pdf')} className="inline-flex h-9 items-center gap-2 rounded-md border border-slate-200 px-3 text-sm font-bold text-slate-700 transition hover:bg-slate-50">
              <Printer className="h-4 w-4" /> Xuất PDF
            </button>
            <button type="button" onClick={() => void downloadReceiptDocument(receipt, 'docx')} className="inline-flex h-9 items-center gap-2 rounded-md border border-slate-200 px-3 text-sm font-bold text-slate-700 transition hover:bg-slate-50">
              <FileText className="h-4 w-4" /> Xuất Word
            </button>
            <button type="button" onClick={onClose} title="Đóng" className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:bg-slate-50 hover:text-slate-950">
              <XCircle className="h-4 w-4" />
            </button>
          </div>
        </div>

        <div className="receipt-screen border-b border-slate-200 px-5 pt-4">
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setActiveTab('info')}
              className={`h-9 rounded-md px-3 text-sm font-bold transition ${activeTab === 'info' ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}`}
            >
              Thông tin phiếu nhập
            </button>
            <button
              type="button"
              onClick={() => {
                setSelectedLineId(null);
                setActiveTab('identifiers');
              }}
              disabled={!needsIdentifier}
              className={`h-9 rounded-md px-3 text-sm font-bold transition disabled:cursor-not-allowed disabled:opacity-50 ${activeTab === 'identifiers' ? 'bg-slate-900 text-white' : 'bg-slate-100 text-slate-700 hover:bg-slate-200'}`}
            >
              Danh sách IMEI / Serial
            </button>
          </div>
        </div>

        <div className="receipt-screen max-h-[calc(100vh-190px)] overflow-y-auto p-5">
          {!isOfficialReceipt && needsIdentifier && (
            <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-800">
              Phiếu nhập chưa hoàn tất do chưa bổ sung đủ IMEI/Serial.
            </div>
          )}

          {activeTab === 'info' && (
          <>
          <section>
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <h4 className="text-sm font-bold uppercase text-slate-700">Thông tin phiếu nhập</h4>
              <AdminBadge tone={isOfficialReceipt ? 'green' : 'amber'}>{isOfficialReceipt ? 'Phiếu nhập hoàn chỉnh' : 'Phiếu nhập tạm'}</AdminBadge>
            </div>
            <div className="grid gap-3 md:grid-cols-4">
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3"><div className="text-xs font-bold uppercase text-slate-500">Trạng thái</div><div className="mt-2"><AdminBadge tone={receiptStatusTone[status] || 'slate'}>{receiptStatusLabel[status] || status}</AdminBadge></div></div>
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3"><div className="text-xs font-bold uppercase text-slate-500">Lý do nhập</div><div className="mt-1 text-sm font-semibold text-slate-800">{formatReceiptReason(receipt?.receiptReasonCode)}</div></div>
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3"><div className="text-xs font-bold uppercase text-slate-500">Nhà cung cấp</div><div className="mt-1 text-sm font-semibold text-slate-800">{receipt?.supplierName || '-'}</div></div>
              <div className="rounded-md border border-slate-200 bg-slate-50 p-3"><div className="text-xs font-bold uppercase text-slate-500">Ngày nhập</div><div className="mt-1 text-sm font-semibold text-slate-800">{receipt?.createdAt ? new Date(receipt.createdAt).toLocaleString('vi-VN') : '-'}</div></div>
              <div className="rounded-md border border-slate-200 bg-white p-3"><div className="text-xs font-bold uppercase text-slate-500">Tổng số dòng</div><div className="mt-1 text-lg font-bold text-slate-900">{receipt?.lineCount || lines.length || 0}</div></div>
              <div className="rounded-md border border-slate-200 bg-white p-3"><div className="text-xs font-bold uppercase text-slate-500">Tổng số lượng</div><div className="mt-1 text-lg font-bold text-emerald-700">{receipt?.totalQuantity || 0}</div></div>
              <div className="rounded-md border border-slate-200 bg-white p-3"><div className="text-xs font-bold uppercase text-slate-500">Tổng tiền</div><div className="mt-1 text-lg font-bold text-slate-900">{currency.format(Number(receipt?.totalCost || 0))}</div></div>
              <div className="rounded-md border border-slate-200 bg-white p-3"><div className="text-xs font-bold uppercase text-slate-500">Ghi chú</div><div className="mt-1 text-sm font-semibold text-slate-800">{receipt?.note || '-'}</div></div>
              <div className="rounded-md border border-slate-200 bg-white p-3"><div className="text-xs font-bold uppercase text-slate-500">Người tạo</div><div className="mt-1 text-sm font-semibold text-slate-800">{formatAuditActor(receipt?.createdBy, receipt?.createdByName)}</div></div>
              <div className="rounded-md border border-slate-200 bg-white p-3"><div className="text-xs font-bold uppercase text-slate-500">Người duyệt</div><div className="mt-1 text-sm font-semibold text-slate-800">{formatAuditActor(receipt?.approvedBy, receipt?.approvedByName)}</div></div>
              <div className="rounded-md border border-slate-200 bg-white p-3"><div className="text-xs font-bold uppercase text-slate-500">Người hoàn tất</div><div className="mt-1 text-sm font-semibold text-slate-800">{formatAuditActor(receipt?.postedBy, receipt?.postedByName)}</div></div>
              <div className="rounded-md border border-slate-200 bg-white p-3"><div className="text-xs font-bold uppercase text-slate-500">Người đảo phiếu</div><div className="mt-1 text-sm font-semibold text-slate-800">{formatAuditActor(receipt?.reversedBy, receipt?.reversedByName)}</div></div>
              <div className="rounded-md border border-slate-200 bg-white p-3"><div className="text-xs font-bold uppercase text-slate-500">Kiểm tra chất lượng</div><div className="mt-2"><AdminBadge tone={qualityStatusTone[receipt?.qualityStatus || 'PENDING'] || 'slate'}>{qualityStatusLabel[receipt?.qualityStatus || 'PENDING'] || receipt?.qualityStatus || 'Chờ kiểm tra'}</AdminBadge></div></div>
              <div className="rounded-md border border-slate-200 bg-white p-3"><div className="text-xs font-bold uppercase text-slate-500">Ghi chú QC</div><div className="mt-1 text-sm font-semibold text-slate-800">{receipt?.qualityNote || '-'}</div></div>
              <div className="rounded-md border border-slate-200 bg-white p-3"><div className="text-xs font-bold uppercase text-slate-500">Cách ly</div><div className="mt-1 text-sm font-semibold text-slate-800">{receipt?.quarantine ? (receipt?.quarantineLocation || 'Có') : 'Không'}</div></div>
            </div>
          </section>

          <section className="mt-5 grid gap-3 lg:grid-cols-2">
            <div className="rounded-md border border-slate-200 bg-white p-3">
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <span className="text-sm font-bold uppercase text-slate-700">Bổ sung chứng từ</span>
                <button type="button" onClick={() => setIsEditingAttachments((value) => !value)} className="inline-flex h-8 items-center gap-1 rounded-md border border-indigo-200 bg-indigo-50 px-2.5 text-xs font-bold text-indigo-700 transition hover:bg-indigo-100">
                  <Plus className="h-3.5 w-3.5" /> {isEditingAttachments ? 'Ẩn form' : 'Bổ sung'}
                </button>
              </div>
              {isEditingAttachments && (
                <div className="mb-4 space-y-2 rounded-md border border-indigo-100 bg-indigo-50/40 p-2">
                  <div className="flex flex-wrap gap-2">
                    <label className="inline-flex h-8 cursor-pointer items-center gap-1 rounded-md border border-indigo-200 bg-white px-2.5 text-xs font-bold text-indigo-700">
                      {isUploadingAttachment ? 'Đang tải...' : 'Tải file'}
                      <input
                        type="file"
                        multiple
                        accept="image/*,.pdf,.doc,.docx,.xls,.xlsx"
                        disabled={isUploadingAttachment}
                        onChange={(event) => {
                          void handleAttachmentUpload(event.target.files);
                          event.currentTarget.value = '';
                        }}
                        className="hidden"
                      />
                    </label>
                    <button type="button" onClick={addAttachmentDraft} className="inline-flex h-8 items-center gap-1 rounded-md border border-slate-200 bg-white px-2.5 text-xs font-bold text-slate-700">
                      <Plus className="h-3.5 w-3.5" /> Thêm link
                    </button>
                  </div>
                  {attachmentDrafts.length === 0 && <div className="rounded-md bg-white px-3 py-2 text-xs font-semibold text-slate-500">Chưa có chứng từ.</div>}
                  {attachmentDrafts.map((item: any, index: number) => (
                    <div key={index} className="grid gap-2 rounded-md border border-slate-100 bg-white p-2 md:grid-cols-[140px_1fr_1fr_36px]">
                      <select value={item.type || 'OTHER'} onChange={(event) => updateAttachmentDraft(index, { type: event.target.value })} className="h-10 rounded-md border border-slate-200 bg-white px-2 text-sm font-semibold text-slate-700 outline-none">
                        {attachmentTypeOptions.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                      </select>
                      <input value={item.name || ''} placeholder="Tên chứng từ" onChange={(event) => updateAttachmentDraft(index, { name: event.target.value })} className="h-10 rounded-md border border-slate-200 bg-white px-2 text-sm font-semibold text-slate-700 outline-none" />
                      <input value={item.url || ''} placeholder="https://... hoặc /uploads/..." onChange={(event) => updateAttachmentDraft(index, { url: event.target.value })} className="h-10 rounded-md border border-slate-200 bg-white px-2 text-sm font-semibold text-slate-700 outline-none" />
                      <button type="button" onClick={() => removeAttachmentDraft(index)} title="Xóa chứng từ" className="inline-flex h-10 w-9 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-500 hover:bg-red-50 hover:text-red-700">
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  ))}
                  <div className="flex flex-wrap justify-end gap-2 pt-1">
                    <button type="button" onClick={() => { setAttachmentDrafts(Array.isArray(receipt?.attachments) ? receipt.attachments : []); setIsEditingAttachments(false); }} className="h-8 rounded-md border border-slate-200 bg-white px-3 text-xs font-bold text-slate-600 hover:bg-slate-50">
                      Hủy
                    </button>
                    <button type="button" disabled={isSavingAttachments || isUploadingAttachment} onClick={() => void saveAttachmentDrafts()} className="h-8 rounded-md border border-emerald-200 bg-emerald-50 px-3 text-xs font-bold text-emerald-700 hover:bg-emerald-100 disabled:cursor-not-allowed disabled:opacity-60">
                      {isSavingAttachments ? 'Đang gửi...' : 'Gửi duyệt'}
                    </button>
                  </div>
                </div>
              )}
              {hasPendingAttachments && (
                <div className="mb-4 rounded-md border border-amber-200 bg-amber-50 p-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <div className="text-sm font-bold text-amber-900">Chứng từ đang chờ duyệt</div>
                      <div className="text-xs font-semibold text-amber-700">Danh sách này chưa được ghi vào chứng từ chính thức.</div>
                    </div>
                    {isSuperAdmin && (
                      <div className="flex flex-wrap gap-2">
                        <button type="button" disabled={isSavingAttachments} onClick={() => void decideAttachmentDrafts(true)} className="h-8 rounded-md border border-emerald-200 bg-white px-3 text-xs font-bold text-emerald-700 hover:bg-emerald-50 disabled:opacity-60">
                          Duyệt
                        </button>
                        <button type="button" disabled={isSavingAttachments} onClick={() => void decideAttachmentDrafts(false)} className="h-8 rounded-md border border-red-200 bg-white px-3 text-xs font-bold text-red-700 hover:bg-red-50 disabled:opacity-60">
                          Từ chối
                        </button>
                      </div>
                    )}
                  </div>
                  <div className="mt-2 space-y-2">
                    {pendingAttachments.map((item: any, index: number) => (
                      <a key={`${item.url || index}`} href={resolveImageUrl(item.url)} target="_blank" rel="noreferrer" className="block rounded-md border border-amber-100 bg-white px-3 py-2 text-sm font-semibold text-amber-800 hover:bg-amber-50">
                        {item.name || 'Chứng từ'} <span className="text-xs text-slate-500">({item.type || 'OTHER'})</span>
                      </a>
                    ))}
                  </div>
                </div>
              )}
              <h4 className="mb-3 text-sm font-bold uppercase text-slate-700">Chứng từ đính kèm</h4>
              {Array.isArray(receipt?.attachments) && receipt.attachments.length > 0 ? (
                <div className="space-y-2">
                  {receipt.attachments.map((item: any, index: number) => (
                    <a key={`${item.url || index}`} href={resolveImageUrl(item.url)} target="_blank" rel="noreferrer" className="block rounded-md border border-slate-100 bg-slate-50 px-3 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-50">
                      {item.name || 'Chứng từ'} <span className="text-xs text-slate-500">({item.type || 'OTHER'})</span>
                    </a>
                  ))}
                </div>
              ) : (
                <div className="text-sm font-semibold text-slate-500">Chưa có chứng từ đính kèm.</div>
              )}
            </div>
            <div className="rounded-md border border-slate-200 bg-white p-3">
              <h4 className="mb-3 text-sm font-bold uppercase text-slate-700">Biên bản sai lệch</h4>
              {Array.isArray(receipt?.discrepancies) && receipt.discrepancies.length > 0 ? (
                <div className="space-y-2">
                  {receipt.discrepancies.map((item: any, index: number) => (
                    <div key={index} className="rounded-md border border-amber-100 bg-amber-50 px-3 py-2 text-sm">
                      <div className="font-bold text-amber-900">{item.type || 'OTHER'}{item.quantity != null ? ` · SL ${item.quantity}` : ''}</div>
                      <div className="mt-1 font-semibold text-slate-800">{item.description}</div>
                      {item.action && <div className="mt-1 text-xs font-semibold text-slate-600">Xử lý: {item.action}</div>}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-sm font-semibold text-slate-500">Chưa ghi nhận sai lệch.</div>
              )}
            </div>
          </section>

          <section className="mt-5">
            <h4 className="mb-3 text-sm font-bold uppercase text-slate-700">Chi tiết nhập kho / IMEI / Serial</h4>
            <div className="overflow-x-auto rounded-md border border-slate-200">
              <table className="min-w-full divide-y divide-slate-200 bg-white text-left text-sm">
                <thead className="bg-slate-50 text-xs font-bold uppercase text-slate-500"><tr><th className="px-4 py-3">Sản phẩm</th><th className="px-4 py-3">SKU / Biến thể</th><th className="px-4 py-3">Vị trí</th><th className="px-4 py-3 text-right">SL nhập</th><th className="px-4 py-3 text-right">SL đã nhập IMEI</th><th className="px-4 py-3 text-right">SL đã nhập Serial</th><th className="px-4 py-3 text-right">Giá nhập</th><th className="px-4 py-3 text-right">Thành tiền</th><th className="px-4 py-3">Trạng thái</th></tr></thead>
                <tbody className="divide-y divide-slate-200">
                  {lineSummaries.length === 0 ? <tr><td className="px-4 py-6 text-center text-sm font-semibold text-slate-500" colSpan={9}>Phiếu chưa có dòng sản phẩm.</td></tr> : lineSummaries.map((summary: any) => (
                    <tr key={summary.line.id || String(summary.line.productId) + '-' + String(summary.line.variantId || 'product')}>
                      <td className="px-4 py-3 font-semibold text-slate-900">{summary.line.productName || '-'}</td>
                      <td className="px-4 py-3 text-slate-600">{summary.line.variantSku || summary.line.sku || '-'}</td>
                      <td className="px-4 py-3 text-slate-600">{summary.line.storageLocationName || summary.line.storageLocationCode || '-'}</td>
                      <td className="px-4 py-3 text-right font-semibold text-slate-800">{summary.planned}</td>
                      <td className="px-4 py-3 text-right font-semibold text-indigo-700">{summary.tracksImei ? summary.imeis.length : '-'}</td>
                      <td className="px-4 py-3 text-right font-semibold text-cyan-700">{summary.tracksSerialNumber ? summary.serialNumbers.length : '-'}</td>
                      <td className="px-4 py-3 text-right text-slate-700">{currency.format(summary.unitCost)}</td>
                      <td className="px-4 py-3 text-right font-semibold text-slate-900">{currency.format(summary.unitCost * summary.received)}</td>
                      <td className="px-4 py-3">
                        {summary.tracksIdentifier ? (
                          <button type="button" onClick={() => openIdentifierTab(summary)} className="inline-flex items-center rounded-md border border-slate-200 bg-white px-2.5 py-1 text-xs font-bold text-slate-700 transition hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700">
                            {summary.identifierStatus}
                          </button>
                        ) : (
                          <AdminBadge tone="slate">{summary.identifierStatus}</AdminBadge>
                        )}
                        {summary.tracksIdentifier && summary.missing > 0 && (
                          <div className="mt-1 text-xs font-bold text-amber-700">
                            Thiếu {summary.missing} mã{summary.line.shortageReason ? ` - Lý do: ${summary.line.shortageReason}` : ''}
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          </>
          )}

          {activeTab === 'identifiers' && needsIdentifier && (
            <section>
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <div>
                  <h4 className="text-sm font-bold uppercase text-slate-700">Danh sách IMEI / Serial</h4>
                  {selectedLine ? (
                    <p className="mt-1 text-xs font-semibold text-slate-500">
                      {selectedLine.line.productName || '-'} {selectedLine.line.variantSku ? `- ${selectedLine.line.variantSku}` : ''}
                    </p>
                  ) : (
                    <p className="mt-1 text-xs font-semibold text-slate-500">Toàn bộ mã định danh trong phiếu nhập.</p>
                  )}
                </div>
                {selectedLineId && (
                  <button type="button" onClick={() => setSelectedLineId(null)} className="h-8 rounded-md border border-slate-200 px-3 text-xs font-bold text-slate-700 transition hover:bg-slate-50">
                    Xem tất cả
                  </button>
                )}
              </div>
              <div className="overflow-x-auto rounded-md border border-slate-200">
                <table className="min-w-full divide-y divide-slate-200 bg-white text-left text-sm">
                  <thead className="bg-slate-50 text-xs font-bold uppercase text-slate-500">
                    <tr>
                      <th className="px-4 py-3 text-right">STT</th>
                      <th className="px-4 py-3">Sản phẩm</th>
                      <th className="px-4 py-3">SKU / Biến thể</th>
                      <th className="px-4 py-3">Loại mã</th>
                      <th className="px-4 py-3">Mã định danh</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200">
                    {visibleIdentifierRows.length === 0 ? (
                      <tr>
                        <td className="px-4 py-6 text-center text-sm font-semibold text-amber-700" colSpan={5}>Chưa có danh sách IMEI/Serial trong dữ liệu phiếu.</td>
                      </tr>
                    ) : (
                      visibleIdentifierRows.map((item: any, index: number) => (
                        <tr key={item.type + '-' + item.value + '-' + index}>
                          <td className="px-4 py-3 text-right font-semibold text-slate-700">{index + 1}</td>
                          <td className="px-4 py-3 font-semibold text-slate-900">{item.line.productName || '-'}</td>
                          <td className="px-4 py-3 text-slate-600">{item.line.variantSku || item.line.sku || '-'}</td>
                          <td className="px-4 py-3 font-semibold text-slate-700">{item.type}</td>
                          <td className="px-4 py-3 font-mono text-xs font-bold text-slate-900">{item.value}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          )}

          <div className="mt-5 flex flex-wrap justify-end gap-2">
            <button type="button" onClick={() => void downloadReceiptDocument(receipt, 'pdf')} className="inline-flex h-10 items-center gap-2 rounded-md border border-slate-200 px-4 text-sm font-bold text-slate-700 transition hover:bg-slate-50"><Download className="h-4 w-4" /> Xuất PDF</button>
            <button type="button" onClick={() => void downloadReceiptDocument(receipt, 'docx')} className="inline-flex h-10 items-center gap-2 rounded-md border border-slate-200 px-4 text-sm font-bold text-slate-700 transition hover:bg-slate-50"><FileText className="h-4 w-4" /> Xuất Word</button>
            <button type="button" onClick={onClose} className="inline-flex h-10 items-center justify-center rounded-md border border-slate-200 px-4 text-sm font-bold text-slate-700 transition hover:bg-slate-50">Đóng</button>
          </div>
        </div>
      </div>
    </div>
  );
}

function splitImeis(value: string) {
  return value
    .split(/[\s,;]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function ImeiReceiptModal({ receipt, onClose, onSubmit }: { receipt: any; onClose: () => void; onSubmit: (referenceCode: string, lines: { lineId: string; imeis: string[]; secondaryImeis?: string[]; serialNumbers: string[]; acceptShortage?: boolean; shortageReason?: string | null }[], shortageReason: string) => Promise<any> }) {
  const trackedLines = useMemo(() => (receipt?.lines || []).filter((line: any) => line.tracksImei || line.tracksSerialNumber), [receipt]);
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [secondaryImeiInputs, setSecondaryImeiInputs] = useState<Record<string, string>>({});
  const [serialInputs, setSerialInputs] = useState<Record<string, string>>({});
  const [confirmedShortages, setConfirmedShortages] = useState<Record<string, boolean>>({});
  const [shortageReasons, setShortageReasons] = useState<Record<string, string>>({});
  const [scanInputs, setScanInputs] = useState<Record<string, string>>({});
  const [scanTargets, setScanTargets] = useState<Record<string, 'imei' | 'imei2' | 'serial'>>({});
  const [scanMessage, setScanMessage] = useState<Record<string, string>>({});
  const [submitError, setSubmitError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    const next: Record<string, string> = {};
    for (const line of trackedLines) next[line.id] = '';
    setInputs(next);
    setSecondaryImeiInputs(next);
    setSerialInputs(next);
    setScanInputs(next);
    setScanTargets(Object.fromEntries(trackedLines.map((line: any) => [line.id, line.tracksImei ? 'imei' : 'serial'])));
    setScanMessage({});
    setConfirmedShortages({});
    setShortageReasons(next);
    setSubmitError('');
    setIsSubmitting(false);
  }, [trackedLines]);

  const lineStats = trackedLines.map((line: any) => {
    const imeis = splitImeis(inputs[line.id] || '');
    const secondaryImeis = splitImeis(secondaryImeiInputs[line.id] || '');
    const serialNumbers = splitImeis(serialInputs[line.id] || '');
    const planned = Number(line.plannedQuantity || line.quantity || 0);
    const counts = [];
    if (line.tracksImei) counts.push(imeis.length);
    if (line.tracksSerialNumber) counts.push(serialNumbers.length);
    const received = counts.length ? Math.min(...counts) : planned;
    const missing = Math.max(planned - received, 0);
    return { line, planned, received, missing, imeis, secondaryImeis, serialNumbers, percent: planned > 0 ? Math.min(100, Math.round((received / planned) * 100)) : 0 };
  });
  const hasOverage = lineStats.some((item) => item.imeis.length > item.planned || item.secondaryImeis.length > item.planned || item.serialNumbers.length > item.planned);
  const hasMismatchedSecondaryImeis = lineStats.some((item) => item.secondaryImeis.length > 0 && item.secondaryImeis.length !== item.imeis.length);
  const duplicateImeis = lineStats
    .flatMap((item) => [...item.imeis, ...item.secondaryImeis])
    .filter((value, index, values) => values.indexOf(value) !== index);
  const duplicateSerials = lineStats
    .flatMap((item) => item.serialNumbers.map((value: string) => `${item.line.productId}:${value}`))
    .filter((value, index, values) => values.indexOf(value) !== index);

  async function handleFile(lineId: string, file: File | null, target: 'imei' | 'imei2' | 'serial') {
    if (!file) return;
    setSubmitError('');
    try {
      const XLSX = await import('xlsx');
      const buffer = await file.arrayBuffer();
      const workbook = XLSX.read(buffer, { type: 'array' });
      const firstSheetName = workbook.SheetNames[0];
      const firstSheet = firstSheetName ? workbook.Sheets[firstSheetName] : null;
      if (!firstSheet) throw new Error('File không có trang dữ liệu.');
      const rows = XLSX.utils.sheet_to_json<any[]>(firstSheet, { header: 1, raw: false });
      const values = rows.flat().map((cell) => String(cell || '').trim()).filter(Boolean).join('\n');
      if (!values) throw new Error('File không chứa mã định danh.');
      if (target === 'serial') setSerialInputs((current) => ({ ...current, [lineId]: values }));
      else if (target === 'imei2') setSecondaryImeiInputs((current) => ({ ...current, [lineId]: values }));
      else setInputs((current) => ({ ...current, [lineId]: values }));
    } catch {
      const targetLabel = target === 'serial' ? 'serial number' : target.toUpperCase();
      setSubmitError(`Không thể đọc danh sách ${targetLabel} từ file. Hãy chọn file Excel, CSV hoặc TXT có ít nhất một mã.`);
    }
  }

  function handleFileInput(event: React.ChangeEvent<HTMLInputElement>, lineId: string, target: 'imei' | 'imei2' | 'serial') {
    const file = event.currentTarget.files?.[0] || null;
    event.currentTarget.value = '';
    void handleFile(lineId, file, target);
  }

  function appendScannedCode(line: any) {
    const lineId = line.id;
    const target = scanTargets[lineId] || (line.tracksImei ? 'imei' : 'serial');
    const rawValue = String(scanInputs[lineId] || '').trim();
    if (!rawValue) return;
    if ((target === 'imei' || target === 'imei2') && !line.tracksImei) {
      setScanMessage((current) => ({ ...current, [lineId]: 'Dòng này không quản lý IMEI.' }));
      return;
    }
    if (target === 'serial' && !line.tracksSerialNumber) {
      setScanMessage((current) => ({ ...current, [lineId]: 'Dòng này không quản lý serial number.' }));
      return;
    }
    const normalizedValue = target === 'serial' ? rawValue.toUpperCase() : rawValue;
    const currentValues = target === 'serial'
      ? splitImeis(serialInputs[lineId] || '')
      : target === 'imei2'
        ? splitImeis(secondaryImeiInputs[lineId] || '')
        : splitImeis(inputs[lineId] || '');
    if (currentValues.includes(normalizedValue)) {
      setScanInputs((current) => ({ ...current, [lineId]: '' }));
      setScanMessage((current) => ({ ...current, [lineId]: `Mã ${normalizedValue} đã có trong danh sách.` }));
      return;
    }
    const planned = Number(line.plannedQuantity || line.quantity || 0);
    if (currentValues.length >= planned) {
      setScanMessage((current) => ({ ...current, [lineId]: `Dòng này đã đủ ${planned} mã, không thể quét thêm.` }));
      return;
    }
    const nextValue = [...currentValues, normalizedValue].join('\n');
    if (target === 'serial') {
      setSerialInputs((current) => ({ ...current, [lineId]: nextValue }));
    } else if (target === 'imei2') {
      setSecondaryImeiInputs((current) => ({ ...current, [lineId]: nextValue }));
    } else {
      setInputs((current) => ({ ...current, [lineId]: nextValue }));
    }
    setScanInputs((current) => ({ ...current, [lineId]: '' }));
    setScanMessage((current) => ({ ...current, [lineId]: `Đã thêm ${normalizedValue}.` }));
  }

  async function handleSubmit() {
    setSubmitError('');
    if (hasOverage) {
      window.alert('Có dòng nhập vượt quá số lượng dự kiến. Vui lòng kiểm tra lại danh sách IMEI/serial number.');
      return;
    }
    if (hasMismatchedSecondaryImeis) {
      window.alert('Nếu nhập IMEI2 thì số dòng IMEI2 phải bằng số dòng IMEI1 để ghép đúng từng máy.');
      return;
    }
    if (duplicateImeis.length > 0 || duplicateSerials.length > 0) {
      window.alert('Danh sách đang có mã IMEI/serial bị trùng. Vui lòng kiểm tra lại trước khi xác nhận.');
      return;
    }
    const unconfirmedShortageLine = lineStats.find((item) => item.missing > 0 && !confirmedShortages[item.line.id]);
    if (unconfirmedShortageLine) {
      window.alert(`Dòng ${unconfirmedShortageLine.line.productName}${unconfirmedShortageLine.line.variantSku ? ` - ${unconfirmedShortageLine.line.variantSku}` : ''} còn thiếu mã định danh. Vui lòng nhập đủ mã hoặc chọn xác nhận nhập thiếu.`);
      return;
    }
    const missingReasonLine = lineStats.find((item) => item.missing > 0 && confirmedShortages[item.line.id] && !shortageReasons[item.line.id]?.trim());
    if (missingReasonLine) {
      window.alert(`Dòng ${missingReasonLine.line.productName}${missingReasonLine.line.variantSku ? ` - ${missingReasonLine.line.variantSku}` : ''} thiếu mã định danh phải nhập lý do thiếu.`);
      return;
    }
    setIsSubmitting(true);
    try {
      await onSubmit(
        receipt.referenceCode,
        lineStats.map((item) => ({
          lineId: item.line.id,
          imeis: item.imeis,
          secondaryImeis: item.secondaryImeis,
          serialNumbers: item.serialNumbers,
          acceptShortage: item.missing > 0 && Boolean(confirmedShortages[item.line.id]),
          shortageReason: item.missing > 0 && confirmedShortages[item.line.id] ? shortageReasons[item.line.id].trim() : null,
        })),
        '',
      );
    } catch (error) {
      setSubmitError(error instanceof Error ? error.message : 'Không thể xác nhận danh sách mã định danh.');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/55 px-4 py-6 backdrop-blur-sm">
      <div className="w-full max-w-5xl overflow-hidden rounded-lg bg-white shadow-2xl">
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 px-5 py-4">
          <div>
            <h3 className="text-lg font-bold text-slate-950">Bổ sung IMEI/serial number</h3>
            <p className="mt-1 text-sm text-slate-500">Phiếu {receipt.referenceCode}. Số lượng phiếu đã khóa, chỉ cập nhật danh sách mã định danh thực nhận.</p>
            <p className="mt-1 text-xs font-semibold text-indigo-700">Với IMEI, dòng đầu tiên sẽ được dùng làm IMEI chính nếu sản phẩm hoặc biến thể chưa có IMEI chính; các dòng còn lại là IMEI bổ sung.</p>
          </div>
          <button type="button" onClick={onClose} className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:bg-slate-50 hover:text-slate-950">
            <XCircle className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4 p-5">
          {trackedLines.length === 0 ? (
            <div className="rounded-md border border-slate-200 bg-slate-50 p-4 text-sm font-semibold text-slate-600">Phiếu này không có dòng cần quản lý IMEI hoặc serial number.</div>
          ) : (
            lineStats.map(({ line, planned, received, missing, percent }) => (
              <div key={line.id} className="rounded-lg border border-slate-200 bg-white p-4">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-bold text-slate-900">{line.productName} {line.variantSku ? `- ${line.variantSku}` : ''}</div>
                    <div className="mt-1 text-xs font-semibold text-slate-500">Đang nhập mã định danh cho sản phẩm này: {received}/{planned}</div>
                  </div>
                  <div className={`rounded-md px-3 py-1 text-xs font-bold ${missing > 0 ? 'bg-amber-50 text-amber-700' : 'bg-emerald-50 text-emerald-700'}`}>
                    {missing > 0 ? `Thiếu ${missing}` : 'Đủ mã'}
                  </div>
                </div>
                <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
                  <div className={`h-full ${received > planned ? 'bg-red-500' : received === planned ? 'bg-emerald-500' : 'bg-amber-500'}`} style={{ width: `${Math.min(100, percent)}%` }} />
                </div>
                <div className="mt-3 rounded-md border border-indigo-100 bg-indigo-50/70 p-3">
                  <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <div className="text-xs font-bold uppercase text-indigo-700">Quét mã liên tục</div>
                      <div className="text-xs font-semibold text-slate-500">Máy quét nhập mã rồi Enter sẽ tự thêm vào danh sách.</div>
                    </div>
                    {line.tracksImei && line.tracksSerialNumber && (
                      <div className="inline-flex rounded-lg border border-indigo-200 bg-white p-1">
                        <button
                          type="button"
                          onClick={() => setScanTargets((current) => ({ ...current, [line.id]: 'imei' }))}
                          className={`rounded-md px-3 py-1.5 text-xs font-bold ${scanTargets[line.id] !== 'serial' ? 'bg-indigo-600 text-white' : 'text-indigo-700 hover:bg-indigo-50'}`}
                        >
                          IMEI
                        </button>
                        <button
                          type="button"
                          onClick={() => setScanTargets((current) => ({ ...current, [line.id]: 'imei2' }))}
                          className={`rounded-md px-3 py-1.5 text-xs font-bold ${scanTargets[line.id] === 'imei2' ? 'bg-indigo-600 text-white' : 'text-indigo-700 hover:bg-indigo-50'}`}
                        >
                          IMEI2
                        </button>
                        <button
                          type="button"
                          onClick={() => setScanTargets((current) => ({ ...current, [line.id]: 'serial' }))}
                          className={`rounded-md px-3 py-1.5 text-xs font-bold ${scanTargets[line.id] === 'serial' ? 'bg-indigo-600 text-white' : 'text-indigo-700 hover:bg-indigo-50'}`}
                        >
                          Serial
                        </button>
                      </div>
                    )}
                  </div>
                  <div className="flex flex-col gap-2 sm:flex-row">
                    <input
                      value={scanInputs[line.id] || ''}
                      onChange={(event) => setScanInputs((current) => ({ ...current, [line.id]: event.target.value }))}
                      onKeyDown={(event) => {
                        if (event.key === 'Enter') {
                          event.preventDefault();
                          appendScannedCode(line);
                        }
                      }}
                      placeholder={`Quét ${line.tracksImei && scanTargets[line.id] !== 'serial' ? 'IMEI' : 'serial number'} rồi nhấn Enter`}
                      className="h-10 flex-1 rounded-lg border border-indigo-200 bg-white px-3 font-mono text-sm font-semibold text-slate-800 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                    />
                    <button
                      type="button"
                      onClick={() => appendScannedCode(line)}
                      className="h-10 rounded-lg bg-indigo-600 px-4 text-sm font-bold text-white hover:bg-indigo-700"
                    >
                      Thêm mã
                    </button>
                  </div>
                  {scanMessage[line.id] && <div className="mt-2 text-xs font-semibold text-indigo-700">{scanMessage[line.id]}</div>}
                </div>
                {line.tracksImei && (
                  <div className="mt-3">
                    <label className="inline-flex h-9 cursor-pointer items-center gap-2 rounded-md border border-slate-200 bg-white px-3 text-xs font-bold text-slate-700 transition hover:bg-slate-50">
                      <FileSpreadsheet className="h-4 w-4" /> Nhập IMEI1 từ tệp
                      <input type="file" accept=".xlsx,.xls,.csv,.txt" className="hidden" onChange={(event) => handleFileInput(event, line.id, 'imei')} />
                    </label>
                    <textarea className="mt-2 min-h-28 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-amber-500" placeholder="Dán danh sách IMEI1, mỗi máy một dòng" value={inputs[line.id] || ''} onChange={(event) => setInputs((current) => ({ ...current, [line.id]: event.target.value }))} />
                    <label className="mt-3 inline-flex h-9 cursor-pointer items-center gap-2 rounded-md border border-slate-200 bg-white px-3 text-xs font-bold text-slate-700 transition hover:bg-slate-50">
                      <FileSpreadsheet className="h-4 w-4" /> Nhập IMEI2 từ tệp (tùy chọn)
                      <input type="file" accept=".xlsx,.xls,.csv,.txt" className="hidden" onChange={(event) => handleFileInput(event, line.id, 'imei2')} />
                    </label>
                    <textarea className="mt-2 min-h-24 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-indigo-500" placeholder="Dán danh sách IMEI2 nếu có, cùng thứ tự với IMEI1" value={secondaryImeiInputs[line.id] || ''} onChange={(event) => setSecondaryImeiInputs((current) => ({ ...current, [line.id]: event.target.value }))} />
                  </div>
                )}
                {line.tracksSerialNumber && (
                  <div className="mt-3">
                    <label className="inline-flex h-9 cursor-pointer items-center gap-2 rounded-md border border-slate-200 bg-white px-3 text-xs font-bold text-slate-700 transition hover:bg-slate-50">
                      <FileSpreadsheet className="h-4 w-4" /> Nhập số sê-ri từ tệp
                      <input type="file" accept=".xlsx,.xls,.csv,.txt" className="hidden" onChange={(event) => handleFileInput(event, line.id, 'serial')} />
                    </label>
                    <textarea className="mt-2 min-h-28 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm outline-none focus:border-cyan-500" placeholder="Dán danh sách serial number" value={serialInputs[line.id] || ''} onChange={(event) => setSerialInputs((current) => ({ ...current, [line.id]: event.target.value }))} />
                  </div>
                )}
                {missing > 0 && (
                  <div className="mt-3 rounded-md border border-amber-200 bg-amber-50 p-3">
                    <label className="flex items-start gap-2 text-xs font-bold text-amber-800">
                      <input
                        type="checkbox"
                        className="mt-0.5 h-4 w-4 rounded border-amber-300 text-amber-600 focus:ring-amber-500"
                        checked={Boolean(confirmedShortages[line.id])}
                        onChange={(event) => setConfirmedShortages((current) => ({ ...current, [line.id]: event.target.checked }))}
                      />
                      <span>Xác nhận nhập thiếu {missing} mã định danh cho sản phẩm này</span>
                    </label>
                    {confirmedShortages[line.id] && (
                      <label className="mt-3 block">
                        <span className="mb-1.5 block text-xs font-bold text-amber-700">Lý do thiếu</span>
                        <textarea
                          className="min-h-20 w-full rounded-md border border-amber-200 bg-white px-3 py-2 text-sm outline-none focus:border-amber-500"
                          placeholder="Nhập lý do thiếu cho riêng sản phẩm này"
                          value={shortageReasons[line.id] || ''}
                          onChange={(event) => setShortageReasons((current) => ({ ...current, [line.id]: event.target.value }))}
                        />
                      </label>
                    )}
                  </div>
                )}
              </div>
            ))
          )}

          {submitError && (
            <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">
              {submitError}
            </div>
          )}

          <div className="flex flex-wrap justify-end gap-2">
            <button type="button" onClick={onClose} className="h-10 rounded-md border border-slate-200 px-4 text-sm font-bold text-slate-700">Đóng</button>
            <button type="button" onClick={handleSubmit} disabled={trackedLines.length === 0 || isSubmitting} className="h-10 rounded-md bg-amber-600 px-4 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-50">
              Xác nhận danh sách mã định danh
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AdminInventoryReceiptsTab(props: AdminInventoryReceiptsTabProps) {
  const {
    inventoryReceipts,
    receiptPage,
    receiptTotal,
    receiptTotalPages,
    inventoryReceiptReport,
    imeiReceipt,
    setImeiReceipt,
    openReceiptDialog,
    openReceiptEditDialog,
    updateReceiptStatus,
    submitReceiptQuality,
    reverseReceipt,
    deleteDraftReceipt,
    openReceiptImeiDialog,
    submitReceiptImeis,
    query,
    setQuery,
    receiptStatusFilter,
    setReceiptStatusFilter,
    receiptDateFrom,
    setReceiptDateFrom,
    receiptDateTo,
    setReceiptDateTo,
    applyReceiptDateFilter,
    clearReceiptDateFilter,
    loadInventoryReceipts,
    isSuperAdmin,
    inventoryLocations,
    setTab,
    uploadFiles,
    products,
    suppliers,
  } = props;
  const [viewReceipt, setViewReceipt] = useState<any | null>(null);
  const [qualityReceipt, setQualityReceipt] = useState<any | null>(null);
  const visibleReceipts = inventoryReceipts || [];
  const latestMonthlyReport = inventoryReceiptReport?.monthly?.[0] || {};
  const latestDailyReport = inventoryReceiptReport?.daily?.[0] || {};
  const supplierStats = Array.isArray(inventoryReceiptReport?.suppliers) ? inventoryReceiptReport.suppliers.slice(0, 5) : [];
  const statusOptions = [
    ['', 'Tất cả trạng thái'],
    ['DRAFT', receiptStatusLabel.DRAFT],
    ['PROCESSING_IMEI', receiptStatusLabel.PROCESSING_IMEI],
    ['PENDING_APPROVAL', receiptStatusLabel.PENDING_APPROVAL],
    ['PENDING_SHORTAGE_APPROVAL', receiptStatusLabel.PENDING_SHORTAGE_APPROVAL],
    ['APPROVED', receiptStatusLabel.APPROVED],
    ['COMPLETED', receiptStatusLabel.COMPLETED],
    ['CANCELLED', receiptStatusLabel.CANCELLED],
    ['REVERSED', receiptStatusLabel.REVERSED],
  ];

  return (
    <>
      <PurchaseOrdersPanel products={products || []} suppliers={suppliers || []} isSuperAdmin={isSuperAdmin} />
      <AdminPanel
        title="Quản lý nhập kho"
        action={
          <button type="button" onClick={() => openReceiptDialog()} className="inline-flex h-10 items-center gap-2 rounded-xl bg-amber-600 px-4 text-sm font-bold text-white shadow-sm transition hover:bg-amber-700">
            <Plus className="h-4 w-4" /> Tạo phiếu nhập
          </button>
        }
      >
        <div className="mb-4 rounded-lg border border-emerald-200 bg-emerald-50/60 p-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <div className="text-sm font-bold text-emerald-900">Kệ hàng trong kho</div>
              <div className="text-xs font-semibold text-emerald-700">Kệ được dùng khi lập từng dòng phiếu nhập và theo dõi tồn kho theo vị trí.</div>
            </div>
            <button
              type="button"
              onClick={() => typeof setTab === 'function' && setTab('inventory')}
              className="h-9 rounded-md border border-emerald-200 bg-white px-3 text-xs font-bold text-emerald-700 hover:bg-emerald-50"
            >
              Quản lý kệ hàng
            </button>
          </div>
          <div className="mt-3 flex flex-wrap gap-2">
            {(inventoryLocations || []).filter((location: any) => String(location.status || 'ACTIVE') === 'ACTIVE').slice(0, 8).map((location: any) => (
              <span key={location.id} className="rounded-full border border-emerald-200 bg-white px-3 py-1 text-xs font-bold text-emerald-800">
                {location.code} - {location.name}
              </span>
            ))}
            {(!inventoryLocations || inventoryLocations.length === 0) && (
              <span className="rounded-full border border-amber-200 bg-amber-50 px-3 py-1 text-xs font-bold text-amber-800">
                Chưa tải được danh mục kệ. Hãy chạy migration mới và tải lại trang.
              </span>
            )}
          </div>
        </div>

        <div className="mb-4 grid gap-3 xl:grid-cols-[360px_1fr]">
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
            <div className="rounded-lg border border-slate-200 bg-white p-3">
              <div className="text-xs font-bold uppercase text-slate-500">Nhập kho tháng {latestMonthlyReport.period || '-'}</div>
              <div className="mt-2 text-2xl font-black text-slate-900">{latestMonthlyReport.receiptCount || 0}</div>
              <div className="mt-1 text-xs font-semibold text-slate-500">
                {Number(latestMonthlyReport.totalQuantity || 0).toLocaleString('vi-VN')} sản phẩm · {currency.format(Number(latestMonthlyReport.totalCost || 0))}
              </div>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-3">
              <div className="text-xs font-bold uppercase text-slate-500">Nhập kho ngày {latestDailyReport.period || '-'}</div>
              <div className="mt-2 text-2xl font-black text-slate-900">{latestDailyReport.receiptCount || 0}</div>
              <div className="mt-1 text-xs font-semibold text-slate-500">
                {Number(latestDailyReport.discrepancyCount || 0).toLocaleString('vi-VN')} phiếu có sai lệch
              </div>
            </div>
          </div>
          <div className="rounded-lg border border-slate-200 bg-white p-3">
            <div className="mb-2 text-sm font-bold text-slate-900">Thống kê nhà cung cấp</div>
            <div className="overflow-x-auto">
              <table className="min-w-full text-left text-xs">
                <thead className="text-slate-500">
                  <tr>
                    <th className="py-2 pr-3">Nhà cung cấp</th>
                    <th className="py-2 pr-3">Số lần nhập</th>
                    <th className="py-2 pr-3">Sai lệch</th>
                    <th className="py-2 pr-3">Không đạt QC</th>
                    <th className="py-2 pr-3">Tỷ lệ lỗi</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {supplierStats.length === 0 ? (
                    <tr><td colSpan={5} className="py-3 text-sm font-semibold text-slate-500">Chưa có dữ liệu nhà cung cấp.</td></tr>
                  ) : supplierStats.map((item: any) => (
                    <tr key={item.supplierName}>
                      <td className="py-2 pr-3 font-bold text-slate-800">{item.supplierName}</td>
                      <td className="py-2 pr-3 font-semibold text-slate-700">{item.receiptCount || 0}</td>
                      <td className="py-2 pr-3 font-semibold text-amber-700">{item.discrepancyCount || 0}</td>
                      <td className="py-2 pr-3 font-semibold text-red-700">{item.failedQualityCount || 0}</td>
                      <td className="py-2 pr-3 font-semibold text-slate-700">{Number(item.failureRate || 0).toFixed(2)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <div className="mb-5 flex flex-wrap items-center gap-2 rounded-2xl border border-slate-200/60 bg-slate-50/70 p-3.5 shadow-[inset_0_1px_2px_rgba(0,0,0,0.02)]">
          <SearchBox value={query} onChange={setQuery} placeholder="Tìm mã phiếu, nhà cung cấp hoặc sản phẩm trong phiếu" />
          <label className="flex h-10 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-xs font-bold text-slate-500">
            Từ
            <input type="date" value={receiptDateFrom || ''} onChange={(event) => setReceiptDateFrom(event.target.value)} className="min-w-32 bg-transparent text-sm font-semibold text-slate-700 outline-none" />
          </label>
          <label className="flex h-10 items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 text-xs font-bold text-slate-500">
            Đến
            <input type="date" value={receiptDateTo || ''} onChange={(event) => setReceiptDateTo(event.target.value)} className="min-w-32 bg-transparent text-sm font-semibold text-slate-700 outline-none" />
          </label>
          <button type="button" onClick={() => void applyReceiptDateFilter()} className="h-10 rounded-xl border border-indigo-200 bg-indigo-50 px-3 text-sm font-bold text-indigo-700 transition hover:bg-indigo-100">Lọc ngày</button>
          {(receiptDateFrom || receiptDateTo) && (
            <button type="button" onClick={() => void clearReceiptDateFilter()} className="h-10 rounded-xl border border-slate-200 bg-white px-3 text-sm font-bold text-slate-600 transition hover:bg-slate-50">Xóa ngày</button>
          )}
          <select
            aria-label="Lọc trạng thái phiếu nhập"
            value={receiptStatusFilter || ''}
            onChange={(event) => {
              const nextStatus = event.target.value;
              setReceiptStatusFilter(nextStatus);
              void loadInventoryReceipts(query, 1, nextStatus);
            }}
            className="h-10 rounded-xl border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
          >
            {statusOptions.map(([value, label]) => (
              <option key={value || 'all'} value={value}>{label}</option>
            ))}
          </select>
        </div>

        <AdminTable headers={['Mã phiếu', 'Trạng thái', 'QC', 'Lý do nhập', 'Nhà cung cấp', 'Ngày tạo', 'Số dòng', 'Tổng SL', 'Giá trị nhập', 'Thao tác']}>
          {visibleReceipts.map((receipt: any) => {
            const status = receipt.status || 'COMPLETED';
            const requiresImei = (receipt.lines || []).some((line: any) => line.tracksImei || line.tracksSerialNumber);
            const canManageReceipt = Boolean(isSuperAdmin);
            const canEditReceipt = ['DRAFT', 'PROCESSING_IMEI'].includes(status)
              || (canManageReceipt && ['PENDING_APPROVAL', 'PENDING_SHORTAGE_APPROVAL', 'APPROVED'].includes(status));
            const hasPendingAttachments = Array.isArray(receipt.pendingAttachments) && receipt.pendingAttachments.length > 0;
            return (
              <tr key={receipt.referenceCode}>
                <td className="px-4 py-3 font-mono text-xs font-bold text-slate-800">{receipt.referenceCode || '-'}</td>
                <td className="px-4 py-3">
                  <AdminBadge tone={receiptStatusTone[status] || 'slate'}>{receiptStatusLabel[status] || status}</AdminBadge>
                  {hasPendingAttachments && <div className="mt-1"><AdminBadge tone="amber">Chờ duyệt chứng từ</AdminBadge></div>}
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-col gap-1">
                    <AdminBadge tone={qualityStatusTone[receipt.qualityStatus || 'PENDING'] || 'slate'}>{qualityStatusLabel[receipt.qualityStatus || 'PENDING'] || receipt.qualityStatus || 'Chờ kiểm tra'}</AdminBadge>
                    {receipt.quarantine && <span className="text-xs font-bold text-red-700">Cách ly</span>}
                  </div>
                </td>
                <td className="px-4 py-3 text-xs font-semibold text-slate-700">{formatReceiptReason(receipt.receiptReasonCode)}</td>
                <td className="px-4 py-3 text-sm font-semibold text-slate-800">{receipt.supplierName || '-'}</td>
                <td className="px-4 py-3 text-sm text-slate-600">{receipt.createdAt ? new Date(receipt.createdAt).toLocaleString('vi-VN') : '-'}</td>
                <td className="px-4 py-3 text-sm font-semibold text-slate-800">{receipt.lineCount || 0}</td>
                <td className="px-4 py-3 text-sm font-semibold text-emerald-700">{receipt.totalQuantity || 0}</td>
                <td className="px-4 py-3 text-sm font-semibold text-slate-800">{currency.format(Number(receipt.totalCost || 0))}</td>
                <td className="px-4 py-3">
                  <div className="flex min-w-40 flex-col items-start gap-2">
                    <div className="flex flex-wrap gap-1.5">
                      <button type="button" onClick={() => setViewReceipt(receipt)} title="Xem phiếu" className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-700 transition hover:bg-slate-50">
                        <Eye className="h-4 w-4" />
                      </button>
                      {canEditReceipt && (
                        <button type="button" onClick={() => openReceiptEditDialog(receipt)} title="Sửa phiếu" className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 bg-white text-slate-700 transition hover:bg-slate-50">
                          <Pencil className="h-4 w-4" />
                        </button>
                      )}
                      {status === 'DRAFT' && (
                        <button type="button" onClick={() => deleteDraftReceipt(receipt)} title="Xóa phiếu nháp" className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-red-200 bg-red-50 text-red-700 transition hover:bg-red-100">
                          <Trash2 className="h-4 w-4" />
                        </button>
                      )}
                      {canManageReceipt && ['PROCESSING_IMEI', 'PENDING_APPROVAL', 'PENDING_SHORTAGE_APPROVAL', 'APPROVED'].includes(status) && (
                        <button type="button" onClick={() => updateReceiptStatus(receipt, 'CANCELLED')} title="Hủy phiếu" className="inline-flex h-8 w-8 items-center justify-center rounded-md border border-red-200 bg-red-50 text-red-700 transition hover:bg-red-100">
                          <XCircle className="h-4 w-4" />
                        </button>
                      )}
                    </div>
                    {status === 'DRAFT' && requiresImei && (
                      <button type="button" onClick={() => updateReceiptStatus(receipt, 'PROCESSING_IMEI')} className="inline-flex h-8 items-center gap-1 rounded-md border border-indigo-200 bg-indigo-50 px-2.5 text-xs font-bold text-indigo-700 transition hover:bg-indigo-100">
                        <ScanLine className="h-3.5 w-3.5" /> Xử lý mã
                      </button>
                    )}
                    {canManageReceipt && status === 'DRAFT' && !requiresImei && (
                      <button type="button" onClick={() => updateReceiptStatus(receipt, 'APPROVED')} className="inline-flex h-8 items-center gap-1 rounded-md border border-blue-200 bg-blue-50 px-2.5 text-xs font-bold text-blue-700 transition hover:bg-blue-100">
                        <CheckCircle2 className="h-3.5 w-3.5" /> Duyệt
                      </button>
                    )}
                    {status === 'PROCESSING_IMEI' && (
                      <button type="button" onClick={() => openReceiptImeiDialog(receipt)} className="inline-flex h-8 items-center gap-1 rounded-md border border-amber-200 bg-amber-50 px-2.5 text-xs font-bold text-amber-700 transition hover:bg-amber-100">
                        <ScanLine className="h-3.5 w-3.5" /> Nhập mã
                      </button>
                    )}
                    {canManageReceipt && status === 'PENDING_APPROVAL' && (
                      <button type="button" onClick={() => updateReceiptStatus(receipt, 'APPROVED')} className="inline-flex h-8 items-center gap-1 rounded-md border border-blue-200 bg-blue-50 px-2.5 text-xs font-bold text-blue-700 transition hover:bg-blue-100">
                        <CheckCircle2 className="h-3.5 w-3.5" /> Duyệt
                      </button>
                    )}
                    {!['COMPLETED', 'CANCELLED', 'REVERSED'].includes(status) && (
                      <div className="flex flex-wrap gap-1.5">
                        <button type="button" onClick={() => setQualityReceipt(receipt)} className="inline-flex h-8 items-center gap-1 rounded-md border border-indigo-200 bg-indigo-50 px-2.5 text-xs font-bold text-indigo-700 transition hover:bg-indigo-100">
                          Kiểm tra QC
                        </button>
                      </div>
                    )}
                    {canManageReceipt && status === 'PENDING_SHORTAGE_APPROVAL' && (
                      <button type="button" onClick={() => updateReceiptStatus(receipt, 'APPROVED')} className="inline-flex h-8 items-center gap-1 rounded-md border border-blue-200 bg-blue-50 px-2.5 text-xs font-bold text-blue-700 transition hover:bg-blue-100">
                        <CheckCircle2 className="h-3.5 w-3.5" /> Duyệt thiếu
                      </button>
                    )}
                    {canManageReceipt && status === 'APPROVED' && (
                      <button type="button" onClick={() => updateReceiptStatus(receipt, 'COMPLETED')} className="inline-flex h-8 items-center gap-1 rounded-md border border-emerald-200 bg-emerald-50 px-2.5 text-xs font-bold text-emerald-700 transition hover:bg-emerald-100">
                        <PackageCheck className="h-3.5 w-3.5" /> Hoàn tất
                      </button>
                    )}
                    {canManageReceipt && status === 'COMPLETED' && (
                      <button type="button" onClick={() => reverseReceipt(receipt)} className="inline-flex h-8 items-center gap-1 rounded-md border border-amber-200 bg-amber-50 px-2.5 text-xs font-bold text-amber-700 transition hover:bg-amber-100">
                        <RotateCcw className="h-3.5 w-3.5" /> Đảo phiếu
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            );
          })}
        </AdminTable>
        <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-4">
          <div className="text-sm font-semibold text-slate-600">
            {receiptTotal > 0
              ? `Hiển thị ${(receiptPage - 1) * 50 + 1}-${Math.min(receiptPage * 50, receiptTotal)} trong ${receiptTotal} phiếu`
              : 'Không có phiếu nhập phù hợp'}
          </div>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={receiptPage <= 1}
              onClick={() => void loadInventoryReceipts(query, receiptPage - 1)}
              className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Trang trước
            </button>
            <span className="min-w-24 text-center text-sm font-bold text-slate-700">
              Trang {receiptPage} / {receiptTotalPages}
            </span>
            <button
              type="button"
              disabled={receiptPage >= receiptTotalPages}
              onClick={() => void loadInventoryReceipts(query, receiptPage + 1)}
              className="h-9 rounded-lg border border-slate-200 bg-white px-3 text-sm font-bold text-slate-700 hover:bg-slate-50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Trang sau
            </button>
          </div>
        </div>
      </AdminPanel>

      {imeiReceipt && (
        <ImeiReceiptModal
          receipt={imeiReceipt}
          onClose={() => setImeiReceipt(null)}
          onSubmit={submitReceiptImeis}
        />
      )}
      {qualityReceipt && (
        <ReceiptQualityModal
          receipt={qualityReceipt}
          locations={inventoryLocations || []}
          onClose={() => setQualityReceipt(null)}
          onSubmit={async (referenceCode: string, payload: any) => {
            await submitReceiptQuality(referenceCode, payload);
            setQualityReceipt(null);
          }}
          uploadFiles={uploadFiles}
        />
      )}
      {viewReceipt && (
        <ReceiptDetailModal
          receipt={viewReceipt}
          onClose={() => setViewReceipt(null)}
          uploadFiles={uploadFiles}
          isSuperAdmin={Boolean(isSuperAdmin)}
          onAttachmentsUpdated={async (patch) => {
            setViewReceipt((current: any) => current ? { ...current, ...patch } : current);
            await loadInventoryReceipts();
          }}
        />
      )}
    </>
  );
}
