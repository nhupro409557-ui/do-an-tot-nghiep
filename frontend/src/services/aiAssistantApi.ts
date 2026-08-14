import { request } from './apiClient';

export type AIAssistantAnswerMode =
  | 'GEMINI'
  | 'GROUNDED_GENERATION'
  | 'DETERMINISTIC'
  | 'DATABASE_FALLBACK'
  | 'POLICY_REFUSAL';

export type AIAssistantResponse = {
  response_id: string;
  version?: '1' | '2';
  answer: string;
  intent?: string | null;
  confidence?: number;
  needs_clarification?: boolean;
  clarification_question?: string | null;
  recommended_products?: any[];
  cards?: Array<{ type: 'product' | 'used_product'; id: string; reason?: string | null }>;
  source_details?: Array<{ type: string; id: string; updated_at?: string | null }>;
  verification_passed?: boolean | null;
  answer_mode: AIAssistantAnswerMode;
  provider_used: 'GEMINI' | 'GROQ' | 'SYSTEM';
  model_name?: string | null;
  fallback_reason?: string | null;
  handover_recommended?: boolean;
  handover?: {
    recommended: boolean;
    reason: string;
    phone?: string | null;
    email?: string | null;
    display_text?: string | null;
    can_create_ticket?: boolean;
    support_request_code?: string | null;
  } | null;
};

export type AIAssistantRequest = {
  conversation_id: string;
  conversation_token: string;
  message: string;
  dynamic_context: {
    cart_items: Array<{
      product_id: string;
      name: string;
      quantity: number;
      price: number;
    }>;
    viewed_products: any[];
    loyalty: {
      tier: 'MEMBER' | 'SILVER' | 'GOLD' | 'DIAMOND';
      points_balance: number;
      wallet_status: 'ACTIVE' | 'CLOSED';
    } | null;
  };
  page_context?: {
    product_id?: string | null;
    cart_item_ids?: string[];
  };
  client_capabilities?: string[];
};

export function askAIAssistant(payload: AIAssistantRequest) {
  return request<AIAssistantResponse>('/ai-assistant/chat', {
    method: 'POST',
    body: JSON.stringify({
      ...payload,
      client_capabilities: payload.client_capabilities || ['response_v2', 'feedback'],
      model_provider: 'GEMINI',
      model_name: 'gemini-3.5-flash',
    }),
  });
}

export type AIConversationSession = {
  conversation_id: string;
  conversation_token: string;
  expires_at: string;
};

export function createAIConversation() {
  return request<AIConversationSession>('/ai-assistant/conversations', {
    method: 'POST',
  });
}

export function submitAIAssistantFeedback(payload: {
  response_id: string;
  conversation_id: string;
  conversation_token: string;
  helpful: boolean;
  reason?: string | null;
}) {
  return request<{
    saved: boolean;
    handover_recommended?: boolean;
    handover?: AIAssistantResponse['handover'];
  }>('/ai-assistant/feedback', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
