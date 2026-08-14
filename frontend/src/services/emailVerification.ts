import { API_BASE_URL } from './apiBaseUrl';

export async function sendRegistrationVerificationEmail(payload: {
  email: string;
  name: string;
  code: string;
  link: string;
  purpose?: 'registration' | 'password_reset';
}) {
  const response = await fetch(`${API_BASE_URL}/auth/send-verification-email`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(data?.detail || 'Không gửi được email xác nhận.');
  }
}
