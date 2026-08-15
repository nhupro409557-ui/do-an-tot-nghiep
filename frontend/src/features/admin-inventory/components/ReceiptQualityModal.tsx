import React, { useMemo, useState } from 'react';
import { CheckCircle2, ImagePlus, Loader2, ShieldAlert, Trash2, UploadCloud, X } from 'lucide-react';
import { resolveImageUrl } from '../../../services/productMedia';

type QualityLine = {
  lineId: string;
  receivedQuantity: number;
  failedQuantity: number;
  actionType: string;
  failedLocationId: string;
  failedImeis: string[];
  failedSerialNumbers: string[];
  notes: string;
  images: QualityImage[];
};

type QualityImage = { url: string; caption: string };

function normalizeQualityImages(images: unknown): QualityImage[] {
  if (!Array.isArray(images)) return [];
  return images.map((image: any) => typeof image === 'string'
    ? { url: image, caption: '' }
    : { url: String(image?.url || ''), caption: String(image?.caption || '') })
    .filter((image) => image.url);
}

async function compressQualityImage(file: File): Promise<File> {
  if (!file.type.startsWith('image/')) return file;
  const objectUrl = URL.createObjectURL(file);
  try {
    const image = await new Promise<HTMLImageElement>((resolve, reject) => {
      const element = new Image();
      element.onload = () => resolve(element);
      element.onerror = () => reject(new Error('Không đọc được ảnh.'));
      element.src = objectUrl;
    });
    const maxDimension = 1920;
    const ratio = Math.min(1, maxDimension / Math.max(image.naturalWidth, image.naturalHeight));
    const width = Math.max(1, Math.round(image.naturalWidth * ratio));
    const height = Math.max(1, Math.round(image.naturalHeight * ratio));
    const canvas = document.createElement('canvas');
    canvas.width = width;
    canvas.height = height;
    const context = canvas.getContext('2d');
    if (!context) return file;
    context.drawImage(image, 0, 0, width, height);
    const blob = await new Promise<Blob | null>((resolve) => canvas.toBlob(resolve, 'image/webp', 0.82));
    if (!blob || blob.size >= file.size) return file;
    const baseName = file.name.replace(/\.[^.]+$/, '') || 'anh-qc';
    return new File([blob], `${baseName}.webp`, { type: 'image/webp', lastModified: Date.now() });
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}

function initialLine(line: any): QualityLine {
  const receivedQuantity = Number(line.receivedQuantity ?? line.quantity ?? 0);
  return {
    lineId: String(line.id),
    receivedQuantity,
    failedQuantity: Number(line.failedQuantity || 0),
    actionType: line.qualityActionType || 'NONE',
    failedLocationId: String(line.failedLocationId || ''),
    failedImeis: Array.isArray(line.failedImeis) ? line.failedImeis : [],
    failedSerialNumbers: Array.isArray(line.failedSerialNumbers) ? line.failedSerialNumbers : [],
    notes: '',
    images: normalizeQualityImages(line.qualityImages),
  };
}

export default function ReceiptQualityModal({ receipt, locations, onClose, onSubmit, uploadFiles }: Record<string, any>) {
  const [note, setNote] = useState(String(receipt.qualityNote || ''));
  const [lines, setLines] = useState<QualityLine[]>(() => (receipt.lines || []).map(initialLine));
  const [uploadingLineId, setUploadingLineId] = useState('');
  const [previewImage, setPreviewImage] = useState('');
  const quarantineLocations = useMemo(() => (locations || []).filter((location: any) => (
    ['QC', 'DAMAGED', 'RETURN', 'WARRANTY'].includes(String(location.purpose || '').toUpperCase())
    && String(location.status || 'ACTIVE') === 'ACTIVE'
  )), [locations]);

  function updateLine(lineId: string, patch: Partial<QualityLine>) {
    setLines((current) => current.map((line) => line.lineId === lineId ? { ...line, ...patch } : line));
  }

  function toggleIdentifier(lineId: string, field: 'failedImeis' | 'failedSerialNumbers', value: string) {
    const current = lines.find((line) => line.lineId === lineId);
    if (!current) return;
    const selected = current[field];
    updateLine(lineId, { [field]: selected.includes(value) ? selected.filter((item) => item !== value) : [...selected, value] });
  }

  async function handleQualityImages(lineId: string, files: FileList | File[]) {
    const images = Array.from(files || []).filter((file: File) => file.type.startsWith('image/'));
    if (!images.length) return window.alert('Vui lòng chọn ít nhất một file ảnh hợp lệ.');
    if (images.length > 8) return window.alert('Mỗi lần chỉ tải tối đa 8 ảnh.');
    if (images.some((file: File) => file.size > 10 * 1024 * 1024)) return window.alert('Mỗi ảnh QC không được vượt quá 10 MB.');
    if (typeof uploadFiles !== 'function') return window.alert('Chức năng tải ảnh hiện chưa sẵn sàng.');
    setUploadingLineId(lineId);
    try {
      const compressedImages = await Promise.all(images.map(compressQualityImage));
      const urls = await uploadFiles(compressedImages, 'inventory');
      const current = lines.find((line) => line.lineId === lineId);
      if (!current) return;
      const existingUrls = new Set(current.images.map((image) => image.url));
      const uploaded = (urls || []).filter((url: string) => url && !existingUrls.has(url)).map((url: string) => ({ url, caption: '' }));
      updateLine(lineId, { images: [...current.images, ...uploaded].slice(0, 12) });
    } finally {
      setUploadingLineId('');
    }
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    let totalPassed = 0;
    let totalFailed = 0;
    const payloadLines = [];
    for (const [index, draft] of lines.entries()) {
      const source = (receipt.lines || [])[index] || {};
      const failed = Number(draft.failedQuantity || 0);
      if (!Number.isInteger(failed) || failed < 0 || failed > draft.receivedQuantity) {
        return window.alert(`Dòng ${index + 1}: số lượng lỗi không hợp lệ.`);
      }
      if (failed > 0 && (!draft.failedLocationId || draft.actionType === 'NONE')) {
        return window.alert(`Dòng ${index + 1}: hàng lỗi phải có hướng xử lý và kệ cách ly.`);
      }
      if (source.tracksImei && draft.failedImeis.length !== failed) {
        return window.alert(`Dòng ${index + 1}: phải chọn đúng ${failed} IMEI lỗi.`);
      }
      if (source.tracksSerialNumber && draft.failedSerialNumbers.length !== failed) {
        return window.alert(`Dòng ${index + 1}: phải chọn đúng ${failed} serial lỗi.`);
      }
      const passed = draft.receivedQuantity - failed;
      totalPassed += passed;
      totalFailed += failed;
      payloadLines.push({
        lineId: draft.lineId,
        passedQuantity: passed,
        failedQuantity: failed,
        actionType: failed > 0 ? draft.actionType : 'NONE',
        failedLocationId: failed > 0 ? draft.failedLocationId : null,
        failedImeis: failed > 0 ? draft.failedImeis : [],
        failedSerialNumbers: failed > 0 ? draft.failedSerialNumbers : [],
        notes: draft.notes || note || null,
        images: draft.images,
      });
    }
    await onSubmit(receipt.referenceCode, {
      qualityStatus: totalFailed > 0 && totalPassed === 0 ? 'FAILED' : 'PASSED',
      qualityNote: note.trim() || null,
      quarantine: false,
      quarantineLocation: null,
      lines: payloadLines,
    });
  }

  return <div className="fixed inset-0 z-[80] flex items-center justify-center bg-slate-950/50 p-4">
    <form onSubmit={submit} className="max-h-[92vh] w-full max-w-6xl overflow-hidden rounded-2xl bg-white shadow-2xl">
      <div className="flex items-center justify-between border-b px-5 py-4">
        <div><h3 className="text-lg font-black text-slate-950">Kiểm tra chất lượng phiếu {receipt.referenceCode}</h3><p className="text-sm text-slate-500">Phân loại hàng đạt và hàng lỗi theo từng sản phẩm, IMEI và serial.</p></div>
        <button type="button" onClick={onClose} className="rounded-lg border p-2 text-slate-500"><X className="h-4 w-4" /></button>
      </div>
      <div className="max-h-[72vh] space-y-4 overflow-y-auto p-5">
        <label className="block text-sm font-bold text-slate-700">Ghi chú QC chung<textarea value={note} onChange={(event) => setNote(event.target.value)} className="mt-1 min-h-20 w-full rounded-xl border border-slate-200 p-3 text-sm font-medium outline-none focus:border-indigo-500" placeholder="Tình trạng tem, hộp, phụ kiện, ngoại quan..." /></label>
        {(receipt.lines || []).map((source: any, index: number) => {
          const draft = lines[index];
          if (!draft) return null;
          const passed = draft.receivedQuantity - draft.failedQuantity;
          return <div key={draft.lineId} className="rounded-xl border border-slate-200 p-4">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2"><div><div className="font-bold text-slate-900">{source.productName || source.productSku || `Dòng ${index + 1}`}</div><div className="text-xs font-semibold text-slate-500">Thực nhận: {draft.receivedQuantity} · Đạt: {passed} · Lỗi: {draft.failedQuantity}</div></div><div className="flex gap-2"><span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-3 py-1 text-xs font-bold text-emerald-700"><CheckCircle2 className="h-3.5 w-3.5" /> {passed} đạt</span><span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-3 py-1 text-xs font-bold text-red-700"><ShieldAlert className="h-3.5 w-3.5" /> {draft.failedQuantity} lỗi</span></div></div>
            <div className="grid gap-3 md:grid-cols-3">
              <label className="text-xs font-bold text-slate-600">Số lượng lỗi<input type="number" min="0" max={draft.receivedQuantity} value={draft.failedQuantity} onChange={(event) => { const failedQuantity = Math.max(0, Math.min(draft.receivedQuantity, Number(event.target.value || 0))); updateLine(draft.lineId, { failedQuantity, failedImeis: draft.failedImeis.slice(0, failedQuantity), failedSerialNumbers: draft.failedSerialNumbers.slice(0, failedQuantity) }); }} className="mt-1 h-10 w-full rounded-lg border px-3 text-sm" /></label>
              <label className="text-xs font-bold text-slate-600">Hướng xử lý<select value={draft.actionType} disabled={draft.failedQuantity === 0} onChange={(event) => updateLine(draft.lineId, { actionType: event.target.value })} className="mt-1 h-10 w-full rounded-lg border px-3 text-sm disabled:bg-slate-100"><option value="NONE">Không có</option><option value="QUARANTINE">Chờ xử lý tại QC</option><option value="RETURN_TO_SUPPLIER">Trả nhà cung cấp</option><option value="SCRAP">Đề xuất hủy</option></select></label>
              <label className="text-xs font-bold text-slate-600">Kệ cách ly<select value={draft.failedLocationId} disabled={draft.failedQuantity === 0} onChange={(event) => updateLine(draft.lineId, { failedLocationId: event.target.value })} className="mt-1 h-10 w-full rounded-lg border px-3 text-sm disabled:bg-slate-100"><option value="">Chọn kệ</option>{quarantineLocations.map((location: any) => <option key={location.id} value={location.id}>{location.code} - {location.name}</option>)}</select></label>
            </div>
            {source.tracksImei && <div className="mt-3"><div className="mb-1 text-xs font-bold text-slate-600">Chọn IMEI lỗi ({draft.failedImeis.length}/{draft.failedQuantity})</div><div className="flex flex-wrap gap-1.5">{(source.imeis || []).map((imei: string) => <button key={imei} type="button" disabled={draft.failedQuantity === 0 || (!draft.failedImeis.includes(imei) && draft.failedImeis.length >= draft.failedQuantity)} onClick={() => toggleIdentifier(draft.lineId, 'failedImeis', imei)} className={`rounded-md border px-2 py-1 font-mono text-xs ${draft.failedImeis.includes(imei) ? 'border-red-300 bg-red-50 text-red-700' : 'border-slate-200 bg-white text-slate-600'} disabled:opacity-40`}>{imei}</button>)}</div></div>}
            {source.tracksSerialNumber && <div className="mt-3"><div className="mb-1 text-xs font-bold text-slate-600">Chọn serial lỗi ({draft.failedSerialNumbers.length}/{draft.failedQuantity})</div><div className="flex flex-wrap gap-1.5">{(source.serialNumbers || []).map((serial: string) => <button key={serial} type="button" disabled={draft.failedQuantity === 0 || (!draft.failedSerialNumbers.includes(serial) && draft.failedSerialNumbers.length >= draft.failedQuantity)} onClick={() => toggleIdentifier(draft.lineId, 'failedSerialNumbers', serial)} className={`rounded-md border px-2 py-1 font-mono text-xs ${draft.failedSerialNumbers.includes(serial) ? 'border-red-300 bg-red-50 text-red-700' : 'border-slate-200 bg-white text-slate-600'} disabled:opacity-40`}>{serial}</button>)}</div></div>}
            <div className="mt-4 border-t border-slate-100 pt-4">
              <div className="mb-2 flex items-center justify-between gap-3"><div><div className="flex items-center gap-1.5 text-xs font-bold text-slate-700"><ImagePlus className="h-4 w-4 text-indigo-600" /> Ảnh kiểm tra dòng hàng</div><div className="text-[11px] font-medium text-slate-500">Tối đa 12 ảnh, mỗi ảnh không quá 10 MB.</div></div><span className="text-xs font-bold text-slate-500">{draft.images.length}/12 ảnh</span></div>
              <label
                onDragOver={(event) => { event.preventDefault(); event.currentTarget.classList.add('border-indigo-400', 'bg-indigo-50'); }}
                onDragLeave={(event) => { event.currentTarget.classList.remove('border-indigo-400', 'bg-indigo-50'); }}
                onDrop={(event) => { event.preventDefault(); event.currentTarget.classList.remove('border-indigo-400', 'bg-indigo-50'); void handleQualityImages(draft.lineId, event.dataTransfer.files); }}
                className="flex min-h-24 cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed border-slate-200 bg-slate-50/70 px-4 py-3 text-center transition hover:border-indigo-300 hover:bg-indigo-50/60 focus-within:border-indigo-500 focus-within:ring-2 focus-within:ring-indigo-100"
              >
                {uploadingLineId === draft.lineId ? <Loader2 className="mb-1 h-6 w-6 animate-spin text-indigo-600" /> : <UploadCloud className="mb-1 h-6 w-6 text-indigo-500" />}
                <span className="text-xs font-bold text-slate-700">{uploadingLineId === draft.lineId ? 'Đang tải ảnh...' : 'Kéo ảnh vào đây hoặc bấm để chọn'}</span>
                <span className="mt-0.5 text-[11px] font-medium text-slate-500">PNG, JPG, WEBP</span>
                <input type="file" multiple accept="image/png,image/jpeg,image/webp" disabled={uploadingLineId === draft.lineId || draft.images.length >= 12} onChange={(event) => { if (event.target.files) void handleQualityImages(draft.lineId, event.target.files); event.currentTarget.value = ''; }} className="sr-only" />
              </label>
              {draft.images.length > 0 && <div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{draft.images.map((image, imageIndex) => <div key={image.url} className="group overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm"><div className="relative aspect-[4/3] overflow-hidden bg-slate-100"><button type="button" onClick={() => setPreviewImage(resolveImageUrl(image.url))} className="h-full w-full focus:outline-none focus:ring-2 focus:ring-inset focus:ring-indigo-500"><img src={resolveImageUrl(image.url)} alt={image.caption || `Ảnh QC ${imageIndex + 1}`} className="h-full w-full object-cover transition group-hover:scale-105" /></button><button type="button" aria-label="Xóa ảnh QC" onClick={() => updateLine(draft.lineId, { images: draft.images.filter((item) => item.url !== image.url) })} className="absolute right-2 top-2 inline-flex h-8 w-8 items-center justify-center rounded-full bg-slate-950/70 text-white shadow-sm transition hover:bg-red-600"><Trash2 className="h-4 w-4" /></button></div><label className="block p-2 text-[11px] font-bold text-slate-600">Chú thích ảnh<input value={image.caption} maxLength={200} onChange={(event) => updateLine(draft.lineId, { images: draft.images.map((item) => item.url === image.url ? { ...item, caption: event.target.value } : item) })} placeholder="Ví dụ: móp góc hộp, trầy viền máy..." className="mt-1 h-9 w-full rounded-lg border border-slate-200 px-2 text-xs font-medium text-slate-700 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100" /></label></div>)}</div>}
            </div>
          </div>;
        })}
      </div>
      <div className="flex justify-end gap-2 border-t bg-slate-50 px-5 py-4"><button type="button" onClick={onClose} className="h-10 rounded-xl border bg-white px-4 text-sm font-bold text-slate-700">Hủy</button><button type="submit" className="h-10 rounded-xl bg-indigo-600 px-5 text-sm font-bold text-white">Lưu kết quả QC</button></div>
    </form>
    {previewImage && <div role="dialog" aria-modal="true" aria-label="Xem ảnh QC" className="fixed inset-0 z-[90] flex items-center justify-center bg-slate-950/85 p-6" onClick={() => setPreviewImage('')}><button type="button" aria-label="Đóng ảnh" onClick={() => setPreviewImage('')} className="absolute right-5 top-5 rounded-full bg-white/10 p-2 text-white hover:bg-white/20"><X className="h-5 w-5" /></button><img src={previewImage} alt="Ảnh QC phóng to" onClick={(event) => event.stopPropagation()} className="max-h-full max-w-full rounded-xl object-contain shadow-2xl" /></div>}
  </div>;
}
