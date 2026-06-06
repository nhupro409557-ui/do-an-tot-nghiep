import React, { useEffect, useState, useRef } from 'react';
import { ChevronDown, Search, Upload } from 'lucide-react';

export function Input({
  label,
  value,
  onChange,
  onBlur,
  type = 'text',
  required = false,
  disabled = false,
  placeholder,
  noLabel = false,
}: {
  label: string;
  value: string | number;
  onChange: (value: string) => void;
  onBlur?: () => void;
  type?: string;
  required?: boolean;
  disabled?: boolean;
  placeholder?: string;
  noLabel?: boolean;
}) {
  return (
    <label className="block w-full sm:w-auto">
      {!noLabel && <span className="mb-1.5 block text-xs font-bold text-slate-500">{label}</span>}
      <input
        disabled={disabled}
        required={required}
        type={type}
        value={value}
        placeholder={placeholder || (noLabel ? label : undefined)}
        onBlur={onBlur}
        onChange={(event) => onChange(event.target.value)}
        className="h-10 w-full rounded-xl border border-slate-200 bg-white px-3 text-sm text-slate-800 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
      />
    </label>
  );
}

export function Select({
  label,
  value,
  onChange,
  options,
  disabled = false,
  noLabel = false,
}: {
  label: string;
  value: string;
  onChange?: (value: string) => void;
  options: [string, string][];
  disabled?: boolean;
  noLabel?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const wrapperRef = useRef<HTMLDivElement | null>(null);
  const selectedLabel = options.find(([optionValue]) => optionValue === value)?.[1] || options[0]?.[1] || label;

  useEffect(() => {
    if (!open) return undefined;

    const handleClickOutside = (event: MouseEvent) => {
      if (!wrapperRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [open]);

  const handleSelect = (optionValue: string) => {
    onChange?.(optionValue);
    setOpen(false);
  };

  return (
    <div ref={wrapperRef} className="relative block w-full sm:w-auto">
      {!noLabel && <span className="mb-1.5 block text-xs font-bold text-slate-500">{label}</span>}
      <button
        type="button"
        disabled={disabled}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={noLabel ? label : undefined}
        onClick={() => setOpen((current) => !current)}
        className="flex h-10 w-full min-w-44 items-center justify-between gap-2 rounded-xl border border-slate-200 bg-white px-3 text-left text-sm text-slate-800 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"
      >
        <span className="truncate">{selectedLabel}</span>
        <ChevronDown className={`h-4 w-4 shrink-0 text-slate-400 transition ${open ? 'rotate-180' : ''}`} />
      </button>
      {open && !disabled && (
        <div className="absolute left-0 top-full z-50 mt-2 w-full min-w-56 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl">
          <div role="listbox" aria-label={label} className="max-h-72 overflow-y-auto p-1">
            {options.map(([optionValue, labelText]) => {
              const selected = optionValue === value;
              return (
                <button
                  key={optionValue || labelText}
                  type="button"
                  role="option"
                  aria-selected={selected}
                  onClick={() => handleSelect(optionValue)}
                  className={`flex w-full items-center rounded-lg px-3 py-2 text-left text-sm font-semibold transition ${
                    selected ? 'bg-red-50 text-red-700' : 'text-slate-700 hover:bg-slate-50 hover:text-slate-950'
                  }`}
                >
                  <span className="truncate">{labelText}</span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export function Checkbox({
  label,
  checked,
  onChange,
  disabled = false,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
}) {
  return (
    <label className="mt-5 flex h-10 items-center gap-2 text-sm font-semibold text-slate-700">
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(event) => onChange(event.target.checked)}
        className="h-4 w-4 accent-indigo-600 disabled:opacity-40"
      />{' '}
      {label}
    </label>
  );
}

export function FileInput({
  label,
  accept,
  multiple = false,
  onFiles,
}: {
  label: string;
  accept: string;
  multiple?: boolean;
  onFiles: (files: FileList | null) => void;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-bold text-slate-500">{label}</span>
      <span className="flex h-10 cursor-pointer items-center gap-2 rounded-xl border border-dashed border-slate-300 bg-white px-3 text-sm font-semibold text-slate-600 transition hover:border-indigo-200 hover:bg-indigo-50 hover:text-indigo-700">
        <Upload className="h-4 w-4" /> Chọn file
      </span>
      <input
        className="hidden"
        type="file"
        accept={accept}
        multiple={multiple}
        onChange={(event) => onFiles(event.target.files)}
      />
    </label>
  );
}

export function RichTextEditor({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const editorRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (editorRef.current && editorRef.current.innerHTML !== value) {
      editorRef.current.innerHTML = value || '<p></p>';
    }
  }, [value]);

  function apply(command: string, commandValue?: string) {
    editorRef.current?.focus();
    document.execCommand(command, false, commandValue);
    onChange(editorRef.current?.innerHTML || '<p></p>');
  }

  return (
    <div className="block">
      <span className="mb-1.5 block text-xs font-bold text-slate-500">{label}</span>
      <div className="overflow-hidden rounded-md border border-slate-200 bg-white">
        <div className="flex flex-wrap gap-2 border-b border-slate-200 bg-slate-50 p-2">
          <button
            type="button"
            onClick={() => apply('bold')}
            className="rounded border border-slate-200 px-2 py-1 text-xs font-bold text-slate-700"
          >
            Bold
          </button>
          <button
            type="button"
            onClick={() => apply('italic')}
            className="rounded border border-slate-200 px-2 py-1 text-xs font-bold text-slate-700"
          >
            Italic
          </button>
          <button
            type="button"
            onClick={() => apply('formatBlock', 'h2')}
            className="rounded border border-slate-200 px-2 py-1 text-xs font-bold text-slate-700"
          >
            H2
          </button>
          <button
            type="button"
            onClick={() => apply('insertUnorderedList')}
            className="rounded border border-slate-200 px-2 py-1 text-xs font-bold text-slate-700"
          >
            List
          </button>
          <button
            type="button"
            onClick={() => {
              const link = window.prompt('Nhập URL liên kết');
              if (link) apply('createLink', link);
            }}
            className="rounded border border-slate-200 px-2 py-1 text-xs font-bold text-slate-700"
          >
            Link
          </button>
        </div>
        <div
          ref={editorRef}
          contentEditable
          suppressContentEditableWarning
          onInput={() => onChange(editorRef.current?.innerHTML || '<p></p>')}
          className="prose min-h-48 max-w-none px-4 py-3 text-sm outline-none"
        />
      </div>
    </div>
  );
}

export function MultiSelectBox({
  label,
  options,
  values,
  onChange,
}: {
  label: string;
  options: { value: string; label: string }[];
  values: string[];
  onChange: (values: string[]) => void;
}) {
  return (
    <label className="block">
      <span className="mb-1.5 block text-xs font-bold text-slate-500">{label}</span>
      <select
        multiple
        value={values}
        onChange={(event) =>
          onChange(
            Array.from(event.target.selectedOptions).map((option) => option.value)
          )
        }
        className="min-h-36 w-full rounded-md border border-slate-200 bg-white px-3 py-2 text-sm text-slate-800 outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </label>
  );
}

export function SearchBox({
  value,
  onChange,
  placeholder = 'Tìm kiếm nhanh',
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="relative block w-full sm:flex-1">
      <Search className="absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="h-10 w-full rounded-xl border border-slate-200 bg-white pl-10 pr-4 text-sm text-slate-800 outline-none transition hover:border-slate-300 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100 placeholder:text-slate-400"
      />
    </label>
  );
}
