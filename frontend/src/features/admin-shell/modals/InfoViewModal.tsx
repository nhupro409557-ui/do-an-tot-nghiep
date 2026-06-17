import React from 'react';
import { X } from 'lucide-react';

type InfoField = {
  label: string;
  value: React.ReactNode;
};

type InfoSection = {
  title: string;
  fields: InfoField[];
};

type InfoViewPayload = {
  title: string;
  subtitle?: string;
  sections: InfoSection[];
};

type InfoViewModalProps = {
  infoView: InfoViewPayload | null;
  setInfoView: (value: InfoViewPayload | null) => void;
};

function displayValue(value: React.ReactNode) {
  if (value === null || value === undefined || value === '') return '-';
  return value;
}

export default function InfoViewModal({ infoView, setInfoView }: InfoViewModalProps) {
  if (!infoView) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-slate-950/55 px-4 py-6 backdrop-blur-sm">
      <div className="w-full max-w-4xl overflow-hidden rounded-lg bg-white shadow-2xl">
        <div className="sticky top-0 z-10 flex items-start justify-between gap-4 border-b border-slate-200 bg-white px-5 py-4">
          <div className="min-w-0">
            <h3 className="truncate text-lg font-bold text-slate-950">{infoView.title}</h3>
            {infoView.subtitle && <p className="mt-1 text-sm font-medium text-slate-500">{infoView.subtitle}</p>}
          </div>
          <button
            type="button"
            onClick={() => setInfoView(null)}
            title="Đóng"
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-slate-200 text-slate-500 hover:bg-slate-50"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-4 p-5">
          {infoView.sections.map((section) => (
            <section key={section.title} className="rounded-lg border border-slate-200 bg-white">
              <div className="border-b border-slate-100 px-4 py-3 text-sm font-bold text-slate-900">{section.title}</div>
              <dl className="grid gap-0 md:grid-cols-2">
                {section.fields.map((field) => (
                  <div key={field.label} className="border-b border-slate-100 px-4 py-3 last:border-b-0 md:border-r md:nth-[2n]:border-r-0">
                    <dt className="text-xs font-bold uppercase text-slate-400">{field.label}</dt>
                    <dd className="mt-1 break-words text-sm font-semibold text-slate-800">{displayValue(field.value)}</dd>
                  </div>
                ))}
              </dl>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
