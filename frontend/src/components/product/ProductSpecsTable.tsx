import React, { useState, useEffect, useRef } from 'react';
import { ListChecks, ChevronDown, X } from 'lucide-react';
import { type Spec, groupSpecs } from './ProductDetailUtils';

interface ProductSpecsTableProps {
  specs: Spec[];
}

export function ProductSpecsTable({ specs }: ProductSpecsTableProps) {
  const [showAllSpecs, setShowAllSpecs] = useState(false);
  const [activeGroup, setActiveGroup] = useState('all');

  const previewSpecs = specs.slice(0, 6);
  if (!previewSpecs.length) return null;

  return (
    <>
      <section className="overflow-hidden rounded-2xl bg-white border border-gray-200">
        <div className="flex items-center gap-2 border-b border-gray-100 px-4 py-3">
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-red-50 text-primary">
            <ListChecks className="h-4 w-4" />
          </span>
          <h2 className="text-base font-bold text-gray-900">Thông số kỹ thuật</h2>
        </div>
        <div className="divide-y divide-gray-100">
          {previewSpecs.map((spec, index) => (
            <div
              key={`${spec.group || 'spec'}-${spec.label}-${index}`}
              className={`grid grid-cols-[42%_1fr] gap-3 px-4 py-3 text-sm ${index % 2 === 0 ? 'bg-white' : 'bg-gray-50/40'}`}
            >
              <span className="font-medium text-gray-500">{spec.label}</span>
              <span className="line-clamp-2 font-semibold leading-relaxed text-gray-800">{spec.value}</span>
            </div>
          ))}
        </div>
        <div className="border-t border-gray-100 p-3">
          <button
            onClick={() => setShowAllSpecs(true)}
            className="flex w-full items-center justify-center gap-1.5 rounded-lg border border-primary bg-white py-2.5 text-sm font-bold text-primary hover:bg-red-50 cursor-pointer"
          >
            Xem tất cả thông số
            <ChevronDown className="h-4 w-4" />
          </button>
        </div>
      </section>

      {showAllSpecs && (
        <SpecsModal
          specs={specs}
          activeGroup={activeGroup}
          onSelectGroup={setActiveGroup}
          onClose={() => setShowAllSpecs(false)}
        />
      )}
    </>
  );
}

export function SpecsModal({
  specs,
  activeGroup,
  onSelectGroup,
  onClose,
}: {
  specs: Spec[];
  activeGroup: string;
  onSelectGroup: (group: string) => void;
  onClose: () => void;
}) {
  const groups = groupSpecs(specs);
  const hasSpecs = specs.length > 0;
  const contentRef = useRef<HTMLDivElement | null>(null);
  const groupRefs = useRef<Record<string, HTMLElement | null>>({});

  const scrollToGroup = (group: string) => {
    onSelectGroup(group);
    const container = contentRef.current;
    if (!container) return;
    if (group === 'all') {
      container.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }
    const target = groupRefs.current[group];
    if (!target) return;
    const containerRect = container.getBoundingClientRect();
    const targetRect = target.getBoundingClientRect();
    const nextTop = container.scrollTop + targetRect.top - containerRect.top - 24;
    container.scrollTo({ top: Math.max(0, nextTop), behavior: 'smooth' });
  };

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', onKeyDown);
    return () => {
      document.body.style.overflow = '';
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [onClose]);

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-black/45 px-3 py-5">
      <div className="flex max-h-[92vh] w-full max-w-[900px] flex-col overflow-hidden rounded-2xl bg-white shadow-2xl">
        <div className="shrink-0 flex items-center justify-between border-b border-gray-200 px-5 py-4">
          <h2 className="text-xl font-bold text-gray-900">Thông số kỹ thuật</h2>
          <button
            onClick={onClose}
            className="flex h-9 w-9 items-center justify-center rounded-full bg-gray-100 text-gray-700 hover:bg-gray-200 cursor-pointer"
            aria-label="Đóng thông số kỹ thuật"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {hasSpecs && (
          <div className="shrink-0 border-b border-gray-200 px-5">
            <div className="flex max-w-full gap-5 overflow-x-auto overflow-y-hidden pb-0.5 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
              <button
                onClick={() => scrollToGroup('all')}
                className={`shrink-0 border-b-2 py-3 text-sm font-bold cursor-pointer ${activeGroup === 'all' ? 'border-primary text-primary' : 'border-transparent text-gray-500'}`}
              >
                Tất cả
              </button>
              {groups.map((group) => (
                <button
                  key={group.title}
                  onClick={() => scrollToGroup(group.title)}
                  className={`shrink-0 border-b-2 py-3 text-sm font-bold cursor-pointer ${activeGroup === group.title ? 'border-primary text-primary' : 'border-transparent text-gray-500'}`}
                >
                  {group.title}
                </button>
              ))}
            </div>
          </div>
        )}

        <div
          ref={contentRef}
          className="flex-1 overflow-y-auto px-5 py-6 space-y-6"
        >
          {groups.map((group) => (
            <section
              key={group.title}
              ref={(el) => {
                groupRefs.current[group.title] = el;
              }}
              className="space-y-3"
            >
              <h3 className="text-sm font-bold uppercase text-primary tracking-wider">{group.title}</h3>
              <div className="overflow-hidden rounded-xl border border-gray-100 bg-white">
                {group.specs.map((spec, index) => (
                  <div
                    key={`${spec.label}-${index}`}
                    className={`grid grid-cols-[40%_1fr] gap-3 px-4 py-3.5 text-sm ${index % 2 === 0 ? 'bg-white' : 'bg-gray-50/30'}`}
                  >
                    <span className="font-medium text-gray-500">{spec.label}</span>
                    <span className="font-semibold leading-relaxed text-gray-800 whitespace-pre-line">{spec.value}</span>
                  </div>
                ))}
              </div>
            </section>
          ))}
        </div>
      </div>
    </div>
  );
}
