import React from 'react';
import { ListChecks } from 'lucide-react';

interface Spec {
  label: string;
  value: string;
  group?: string;
}

interface TechSpecsTableProps {
  specs: Spec[];
}

export function TechSpecsTable({ specs }: TechSpecsTableProps) {
  const groups = specs.reduce<{ title: string; specs: Spec[] }[]>((items, spec) => {
    const title = spec.group?.trim() || 'Thông số khác';
    const existing = items.find((item) => item.title === title);
    if (existing) existing.specs.push(spec);
    else items.push({ title, specs: [spec] });
    return items;
  }, []);

  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm">
      <div className="flex items-center gap-2 border-b border-gray-100 bg-gray-50 px-4 py-3">
        <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-red-50 text-primary">
          <ListChecks className="h-4 w-4" />
        </span>
        <h3 className="text-base font-bold text-gray-900">Thông số kỹ thuật</h3>
      </div>

      <div className="divide-y divide-gray-100">
        {groups.map((group) => (
          <div key={group.title}>
            <div className="bg-red-50/60 px-4 py-2">
              <span className="text-xs font-bold uppercase text-primary">{group.title}</span>
            </div>
            <div className="divide-y divide-gray-100">
              {group.specs.map((spec, index) => (
                <div
                  key={`${group.title}-${index}`}
                  className={`grid grid-cols-[38%_1fr] gap-3 px-4 py-3 text-sm ${index % 2 === 0 ? 'bg-white' : 'bg-gray-50/70'}`}
                >
                  <span className="font-medium text-gray-500">{spec.label}</span>
                  <span className="font-semibold leading-relaxed text-gray-800">{spec.value}</span>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
