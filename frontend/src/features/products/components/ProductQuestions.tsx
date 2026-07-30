import React, { useEffect, useMemo, useReducer } from 'react';
import { MessageCircle, Send, Trash2 } from 'lucide-react';
import { publicApi } from '../../../services/publicApi';
import { useAuth } from '../../../context/AuthContext';

interface ProductQuestion {
  id: string;
  userName?: string;
  content?: string;
  body?: string;
  parentId?: string | null;
  replyToUserName?: string | null;
  createdAt?: string;
  isRetracted?: boolean;
  isPending?: boolean;
  isFailed?: boolean;
}

interface QuestionThread extends ProductQuestion {
  replies: ProductQuestion[];
}

type ProductQuestionsState = {
  questions: ProductQuestion[];
  loading: boolean;
  questionText: string;
  replyTarget: ProductQuestion | null;
  submitting: boolean;
  submitError: string;
  loadError: string;
};

type ProductQuestionsAction =
  | Partial<ProductQuestionsState>
  | ((state: ProductQuestionsState) => ProductQuestionsState);

const initialProductQuestionsState: ProductQuestionsState = {
  questions: [],
  loading: true,
  questionText: '',
  replyTarget: null,
  submitting: false,
  submitError: '',
  loadError: '',
};

function mergeProductQuestionsState(state: ProductQuestionsState, action: ProductQuestionsAction): ProductQuestionsState {
  return typeof action === 'function' ? action(state) : { ...state, ...action };
}

function questionContent(question: ProductQuestion) {
  if (question.isRetracted) return 'Nội dung đã được thu hồi.';
  return question.content || question.body || '';
}

function questionDate(question: ProductQuestion) {
  if (!question.createdAt) return '';
  return new Date(question.createdAt).toLocaleDateString('vi-VN');
}

export function ProductQuestions({ productId }: { productId: string }) {
  return <ProductQuestionsContent key={productId} productId={productId} />;
}

function ProductQuestionsContent({ productId }: { productId: string }) {
  const { user } = useAuth();
  const [{ questions, loading, questionText, replyTarget, submitting, submitError, loadError }, setQuestionState] = useReducer(
    mergeProductQuestionsState,
    initialProductQuestionsState,
  );

  useEffect(() => {
    let isActive = true;
    publicApi.listProductQuestions(productId)
      .then((items) => {
        if (!isActive) return;
        setQuestionState({ questions: Array.isArray(items) ? items : [], loadError: '' });
      })
      .catch(() => {
        if (!isActive) return;
        setQuestionState({ questions: [], loadError: 'Không thể tải hỏi đáp sản phẩm. Vui lòng thử tải lại trang.' });
      })
      .finally(() => {
        if (!isActive) return;
        setQuestionState({ loading: false });
      });
    return () => {
      isActive = false;
    };
  }, [productId]);

  const questionThreads = useMemo<QuestionThread[]>(() => {
    const visibleQuestions = questions.filter((question) => String(questionContent(question)).trim() !== '');
    const roots = visibleQuestions.filter((question) => !question.parentId);
    const replies = visibleQuestions.filter((question) => question.parentId);
    return roots.map((root) => ({
      ...root,
      replies: replies.filter((reply) => reply.parentId === root.id),
    }));
  }, [questions]);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    const content = questionText.trim();
    if (!content) return;
    if (!user) {
      setQuestionState({ submitError: 'Vui lòng đăng nhập để gửi câu hỏi.' });
      return;
    }

    const parentId = replyTarget?.parentId || replyTarget?.id || null;
    const replyToUserName = replyTarget?.userName || null;
    const tempId = `local-${Date.now()}`;
    const optimisticQuestion: ProductQuestion = {
      id: tempId,
      userName: 'Bạn',
      content,
      parentId,
      replyToUserName,
      isPending: true,
    };

    setQuestionState((state) => ({
      ...state,
      questions: [...state.questions, optimisticQuestion],
      questionText: '',
      replyTarget: null,
      submitError: '',
      submitting: true,
    }));

    try {
      const created = await publicApi.createProductQuestion(productId, {
        body: content,
        parentId,
        replyToUserName,
      });
      setQuestionState((state) => ({ ...state, questions: state.questions.map((question) => question.id === tempId ? created : question) }));
    } catch (error: any) {
      setQuestionState({ submitError: error?.message || 'Không thể gửi câu hỏi. Vui lòng thử lại.' });
      setQuestionState((state) => ({
        ...state,
        questions: state.questions.map((question) =>
          question.id === tempId
            ? { ...question, isPending: false, isFailed: true }
            : question
        ),
      }));
    } finally {
      setQuestionState({ submitting: false });
    }
  }

  async function handleRetract(questionId: string) {
    if (!window.confirm('Thu hồi nội dung này?')) return;
    try {
      await publicApi.retractProductQuestion(productId, questionId);
      setQuestionState((state) => ({ ...state, questions: state.questions.map((question) => question.id === questionId ? { ...question, isRetracted: true, content: 'Nội dung đã được thu hồi.' } : question) }));
    } catch (error: any) {
      setQuestionState({ submitError: error?.message || 'Không thể thu hồi nội dung.' });
    }
  }

  const renderQuestion = (question: ProductQuestion, isReply = false) => {
    const content = questionContent(question);
    const canRetract = user && !question.isPending && !question.isRetracted && !question.id.startsWith('local-');
    return (
      <div key={question.id} className={`${isReply ? 'ml-9 border-l border-gray-100 pl-4' : ''} rounded-xl bg-white`}>
        <div className="flex items-start gap-3">
          <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-red-50 text-sm font-black text-primary">
            {(question.userName || 'K').charAt(0).toUpperCase()}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-sm font-bold text-gray-900">{question.userName || 'Khách hàng'}</span>
              {questionDate(question) && <span className="text-xs font-medium text-gray-400">{questionDate(question)}</span>}
              {question.isPending && <span className="text-xs font-semibold text-amber-600">Đang gửi</span>}
              {question.isFailed && <span className="text-xs font-semibold text-red-600">Gửi lỗi</span>}
            </div>
            <p className={`mt-1 whitespace-pre-line text-sm leading-6 ${question.isRetracted ? 'text-gray-400 italic' : 'text-gray-700'}`}>
              {question.replyToUserName && <span className="font-semibold text-primary">@{question.replyToUserName} </span>}
              {content}
            </p>
            {!question.isRetracted && (
              <div className="mt-2 flex flex-wrap gap-3 text-xs font-bold">
                <button type="button" onClick={() => setQuestionState({ replyTarget: question })} className="text-primary hover:text-red-700">
                  Trả lời
                </button>
                {canRetract && (
                  <button type="button" onClick={() => handleRetract(question.id)} className="inline-flex items-center gap-1 text-gray-400 hover:text-red-600">
                    <Trash2 className="h-3.5 w-3.5" />
                    Thu hồi
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <section id="product-questions" className="mt-8 rounded-xl border border-gray-100 bg-white p-6 shadow-sm">
      <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <MessageCircle className="h-5 w-5 text-primary" />
            <h2 className="font-display text-xl font-bold text-gray-900">Hỏi đáp sản phẩm</h2>
          </div>
          <p className="mt-1 text-sm text-gray-500">Đặt câu hỏi về sản phẩm, cửa hàng sẽ phản hồi trong thời gian sớm nhất.</p>
        </div>
        <span className="text-sm font-bold text-gray-500">
          {loading ? 'Đang tải...' : loadError ? 'Chưa xác định' : `${questions.length.toLocaleString('vi-VN')} nội dung`}
        </span>
      </div>

      {!user && (
        <div className="mb-5 rounded-lg border border-amber-100 bg-amber-50 p-4 text-sm font-semibold text-amber-800">
          Vui lòng đăng nhập để gửi câu hỏi hoặc phản hồi.
        </div>
      )}

      <form onSubmit={handleSubmit} className="mb-6 rounded-xl border border-gray-200 bg-gray-50 p-4">
        {replyTarget && (
          <div className="mb-3 flex items-center justify-between rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-sm text-red-700">
            <span>Đang trả lời {replyTarget.userName || 'khách hàng'}</span>
            <button type="button" onClick={() => setQuestionState({ replyTarget: null })} className="font-bold hover:text-red-900">Hủy</button>
          </div>
        )}
        <textarea
          aria-label="Nhập câu hỏi về sản phẩm"
          value={questionText}
          onChange={(event) => setQuestionState({ questionText: event.target.value })}
          placeholder="Nhập câu hỏi của bạn về sản phẩm này..."
          className="min-h-[96px] w-full rounded-lg border border-gray-300 p-3 text-sm outline-none focus:border-primary focus:ring-1 focus:ring-primary"
          maxLength={1000}
        />
        {submitError && <div className="mt-3 rounded-md bg-red-50 px-3 py-2 text-sm font-semibold text-red-600">{submitError}</div>}
        <div className="mt-3 flex items-center justify-between gap-3">
          <span className="text-xs font-medium text-gray-400">{questionText.length}/1000 ký tự</span>
          <button type="submit" disabled={submitting || !questionText.trim()} className="inline-flex items-center gap-2 rounded-lg bg-primary px-5 py-2 text-sm font-bold text-white transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-60">
            <Send className="h-4 w-4" />
            {submitting ? 'Đang gửi...' : replyTarget ? 'Gửi trả lời' : 'Gửi câu hỏi'}
          </button>
        </div>
      </form>

      <div className="space-y-5">
        {loading && <div className="text-sm text-gray-400">Đang tải hỏi đáp...</div>}
        {!loading && loadError && <div className="rounded-lg border border-red-100 bg-red-50 px-4 py-3 text-sm font-semibold text-red-700">{loadError}</div>}
        {!loading && !loadError && questionThreads.length === 0 && <div className="text-sm text-gray-400">Chưa có câu hỏi nào cho sản phẩm này.</div>}
        {questionThreads.map((thread) => (
          <div key={thread.id} className="space-y-3 border-b border-gray-100 pb-5 last:border-0 last:pb-0">
            {renderQuestion(thread)}
            {thread.replies.map((reply) => renderQuestion(reply, true))}
          </div>
        ))}
      </div>
    </section>
  );
}
