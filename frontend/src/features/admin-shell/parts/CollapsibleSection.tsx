import React, { useEffect, useLayoutEffect, useState } from 'react';
import { Plus, X } from 'lucide-react';

export function CollapsibleSection({
  title,
  description,
  children,
  defaultOpen = false,
  forceOpen = false,
  forceOpenKey,
  closeSignal = 0,
  open: controlledOpen,
  onOpenChange,
  onClose,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
  forceOpen?: boolean;
  forceOpenKey?: string | null;
  closeSignal?: number;
  open?: boolean;
  onOpenChange?: (open: boolean) => void;
  onClose?: () => void;
}) {
  const [open, setOpen] = useState(defaultOpen);
  const sectionOpen = controlledOpen ?? open;
  const setSectionOpen = (nextOpen: boolean) => {
    if (controlledOpen === undefined) {
      setOpen(nextOpen);
    }
    onOpenChange?.(nextOpen);
  };

  useEffect(() => {
    if (forceOpen) setSectionOpen(true);
  }, [forceOpen, forceOpenKey]);

  useLayoutEffect(() => {
    if (closeSignal > 0) setSectionOpen(false);
  }, [closeSignal]);

  const closePopup = () => {
    setSectionOpen(false);
    onClose?.();
  };

  return (
    <div className="mb-5 rounded-lg border border-slate-200 bg-slate-50 p-3">
      <div className="flex w-full flex-col gap-3 rounded-md bg-white px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <div className="text-sm font-bold text-slate-955">{title}</div>
          {description && <div className="mt-1 text-xs font-medium leading-5 text-slate-500">{description}</div>}
        </div>
        <button
          type="button"
          onClick={() => setSectionOpen(true)}
          className="inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap rounded-xl bg-red-600 px-4 py-2 text-sm font-bold text-white shadow-sm transition hover:bg-red-700"
        >
          <Plus className="h-4 w-4" /> Thêm
        </button>
      </div>
      {sectionOpen && (
        <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/55 px-4 py-6 backdrop-blur-sm">
          <div className="w-full max-w-6xl overflow-hidden rounded-lg bg-white shadow-2xl">
            <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-slate-200 bg-white px-5 py-4">
              <div>
                <h3 className="text-lg font-bold text-slate-955">{title}</h3>
                {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
              </div>
              <button
                type="button"
                onClick={closePopup}
                title="Đóng popup"
                className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-600 transition hover:bg-slate-50 hover:text-slate-950"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="max-h-[calc(100vh-150px)] overflow-y-auto p-5">{children}</div>
          </div>
        </div>
      )}
    </div>
  );
}
