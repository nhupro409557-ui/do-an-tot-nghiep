import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Clock3, Search, Sparkles, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useCatalog } from '../../hooks/useCatalog';
import { analyzeProductSearch, getSearchIntentBadges } from '../../utils/smartProductSearch';

const SEARCH_HISTORY_KEY = 'echophone_search_history';
const MAX_SEARCH_HISTORY = 5;
const SEARCH_SUGGESTIONS = ['điện thoại dưới 10 triệu', 'laptop gaming', 'tai nghe bluetooth'];

const readSearchHistory = () => {
  try {
    const value = window.localStorage.getItem(SEARCH_HISTORY_KEY);
    const parsed = value ? JSON.parse(value) : [];
    return Array.isArray(parsed)
      ? parsed.filter((item) => typeof item === 'string').slice(0, MAX_SEARCH_HISTORY)
      : [];
  } catch {
    return [];
  }
};

const saveSearchHistory = (items: string[]) => {
  window.localStorage.setItem(SEARCH_HISTORY_KEY, JSON.stringify(items.slice(0, MAX_SEARCH_HISTORY)));
};

export function SearchBar() {
  const navigate = useNavigate();
  const { categories } = useCatalog();
  const mobileInputRef = useRef<HTMLInputElement>(null);
  const [term, setTerm] = useState('');
  const [isMobileOpen, setIsMobileOpen] = useState(false);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  const [history, setHistory] = useState<string[]>(() => readSearchHistory());

  const intentBadges = useMemo(() => {
    const keyword = term.trim();
    if (!keyword) return [];
    return getSearchIntentBadges(analyzeProductSearch(keyword, [], categories), categories);
  }, [categories, term]);

  useEffect(() => {
    if (!isMobileOpen) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.setTimeout(() => mobileInputRef.current?.focus(), 40);

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setIsMobileOpen(false);
        setIsHistoryOpen(false);
      }
    };

    window.addEventListener('keydown', handleKeyDown);

    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [isMobileOpen]);

  const rememberSearch = (keyword: string) => {
    const nextHistory = [
      keyword,
      ...history.filter((item) => item.toLowerCase() !== keyword.toLowerCase()),
    ].slice(0, MAX_SEARCH_HISTORY);
    setHistory(nextHistory);
    saveSearchHistory(nextHistory);
  };

  const runSearch = (value: string) => {
    const keyword = value.trim();
    if (!keyword) return;

    rememberSearch(keyword);
    navigate(`/search?q=${encodeURIComponent(keyword)}`);
    setIsMobileOpen(false);
    setIsHistoryOpen(false);
  };

  const submitSearch = (event: React.FormEvent) => {
    event.preventDefault();
    runSearch(term);
  };

  const handleSearchKeyDown = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      runSearch(term);
    }
  };

  const selectHistory = (keyword: string) => {
    setTerm(keyword);
    runSearch(keyword);
  };

  const selectSuggestion = (keyword: string) => {
    setTerm(keyword);
    runSearch(keyword);
  };

  const removeHistoryItem = (keyword: string) => {
    const nextHistory = history.filter((item) => item !== keyword);
    setHistory(nextHistory);
    saveSearchHistory(nextHistory);
  };

  const clearHistory = () => {
    setHistory([]);
    saveSearchHistory([]);
  };

  const shouldShowAssist = isHistoryOpen && (history.length > 0 || intentBadges.length > 0);

  const renderAssistPanel = (className: string) => (
    <div className={className}>
      {intentBadges.length > 0 && (
        <div className="border-b border-slate-100 px-3 py-3">
          <div className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-500">Hệ thống hiểu là</div>
          <div className="flex flex-wrap gap-2">
            {intentBadges.map((badge) => (
              <span key={`${badge.label}-${badge.value}`} className="inline-flex max-w-full items-center gap-1 rounded-full border border-red-100 bg-red-50 px-2.5 py-1 text-xs font-semibold text-primary">
                <span className="shrink-0 text-slate-500">{badge.label}:</span>
                <span className="truncate">{badge.value}</span>
              </span>
            ))}
          </div>
        </div>
      )}

      {history.length > 0 && (
        <>
          <div className="flex items-center justify-between gap-2 border-b border-slate-100 px-3 py-2">
            <span className="truncate text-xs font-bold uppercase tracking-wide text-slate-500">Tìm kiếm gần đây</span>
            <button
              type="button"
              onMouseDown={(event) => event.preventDefault()}
              onClick={clearHistory}
              className="shrink-0 text-xs font-semibold text-primary hover:underline"
            >
              Xóa tất cả
            </button>
          </div>
          <div className="py-1">
            {history.map((item) => (
              <div key={item} className="group flex items-center gap-2 px-2">
                <button
                  type="button"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => selectHistory(item)}
                  className="flex min-w-0 flex-1 items-center gap-2 rounded-md px-2 py-2 text-left text-sm hover:bg-slate-50"
                >
                  <Clock3 className="h-4 w-4 shrink-0 text-slate-400" />
                  <span className="truncate">{item}</span>
                </button>
                <button
                  type="button"
                  onMouseDown={(event) => event.preventDefault()}
                  onClick={() => removeHistoryItem(item)}
                  aria-label={`Xóa ${item}`}
                  className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-slate-400 opacity-100 hover:bg-slate-100 hover:text-slate-700 md:opacity-0 md:group-hover:opacity-100"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  );

  return (
    <>
      <form onSubmit={submitSearch} className="relative hidden min-w-0 flex-1 md:block">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-500" />
        <input
          aria-label="Tìm kiếm sản phẩm"
          value={term}
          onChange={(event) => setTerm(event.target.value)}
          onFocus={() => setIsHistoryOpen(true)}
          onClick={() => setIsHistoryOpen(true)}
          onBlur={() => setIsHistoryOpen(false)}
          onKeyDown={handleSearchKeyDown}
          type="search"
          enterKeyHint="search"
          spellCheck={false}
          placeholder="Tìm kiếm điện thoại, laptop, phụ kiện"
          style={{ color: '#000' }}
          className="h-11 w-full rounded-xl border-0 bg-white pl-10 pr-4 text-sm shadow-sm outline-none ring-1 ring-white/20 transition placeholder:text-slate-500 focus:ring-2 focus:ring-yellow-300"
        />
        {shouldShowAssist && renderAssistPanel('absolute left-0 right-0 top-full z-50 mt-2 max-h-[60vh] overflow-hidden overflow-y-auto rounded-xl border border-slate-200 bg-white text-slate-900 shadow-2xl')}
      </form>

      <button
        type="button"
        onClick={() => {
          setIsMobileOpen(true);
          setIsHistoryOpen(true);
        }}
        className="ml-auto flex h-11 min-w-11 items-center justify-center gap-2 rounded-xl bg-white/15 px-3 ring-1 ring-white/15 transition hover:bg-white/20 md:hidden"
        aria-label="Tìm kiếm sản phẩm"
      >
        <Search className="h-5 w-5" />
        <span className="hidden whitespace-nowrap text-sm font-semibold min-[430px]:inline">Tìm kiếm</span>
      </button>

      {isMobileOpen && (
        <div className="fixed inset-0 z-[100] bg-white text-slate-900 md:hidden">
          <div className="border-b border-slate-200 bg-white px-4 pb-3 pt-4 shadow-sm">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-bold uppercase tracking-wide text-primary">Tìm nhanh</p>
                <h2 className="text-lg font-bold text-slate-950">Bạn cần sản phẩm nào?</h2>
              </div>
              <button
                type="button"
                onClick={() => {
                  setIsMobileOpen(false);
                  setIsHistoryOpen(false);
                }}
                className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-700"
                aria-label="Đóng tìm kiếm"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <div className="relative">
              <form onSubmit={submitSearch} className="flex items-center gap-2">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
                  <input
                    ref={mobileInputRef}
                    aria-label="Tìm kiếm sản phẩm trên di động"
                    value={term}
                    onChange={(event) => setTerm(event.target.value)}
                    onFocus={() => setIsHistoryOpen(true)}
                    onClick={() => setIsHistoryOpen(true)}
                    onKeyDown={handleSearchKeyDown}
                    type="search"
                    enterKeyHint="search"
                    spellCheck={false}
                    placeholder="Tìm kiếm sản phẩm"
                    style={{ color: '#000' }}
                    className="h-12 w-full rounded-xl bg-slate-100 pl-11 pr-4 text-sm outline-none ring-1 ring-slate-200 transition placeholder:text-slate-500 focus:bg-white focus:ring-2 focus:ring-primary"
                  />
                </div>
                <button type="submit" className="h-12 rounded-xl bg-primary px-4 text-sm font-bold text-white shadow-sm">
                  Tìm
                </button>
              </form>
              {shouldShowAssist && renderAssistPanel('mt-3 max-h-[42vh] overflow-hidden overflow-y-auto rounded-xl border border-slate-200 bg-white text-slate-900 shadow-sm')}
            </div>
          </div>

          <div className="space-y-5 px-4 py-5">
            <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
              <div className="mb-3 flex items-center gap-2 text-sm font-bold text-slate-800">
                <Sparkles className="h-4 w-4 text-primary" />
                Gợi ý tìm kiếm
              </div>
              <div className="flex flex-wrap gap-2">
                {SEARCH_SUGGESTIONS.map((item) => (
                  <button
                    type="button"
                    key={item}
                    onClick={() => selectSuggestion(item)}
                    className="rounded-full border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 shadow-sm"
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>

            <div className="text-sm leading-6 text-slate-500">
              Nhập nhu cầu cụ thể như khoảng giá, thương hiệu hoặc loại sản phẩm để hệ thống lọc kết quả chính xác hơn.
            </div>
          </div>
        </div>
      )}
    </>
  );
}
