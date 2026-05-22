const GOOGLE_CLIENT_ID = '293864704533-n31a0a66ro184o9vkq8tv8m0b6l73tp1.apps.googleusercontent.com';
const GOOGLE_SCRIPT_ID = 'google-identity-services';

type GoogleCredentialResponse = {
  credential?: string;
};

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (options: {
            client_id: string;
            callback: (response: GoogleCredentialResponse) => void;
          }) => void;
          prompt: (listener?: (notification: unknown) => void) => void;
          cancel: () => void;
        };
      };
    };
  }
}

function loadGoogleScript() {
  return new Promise<void>((resolve, reject) => {
    if (window.google?.accounts?.id) {
      resolve();
      return;
    }

    const existingScript = document.getElementById(GOOGLE_SCRIPT_ID) as HTMLScriptElement | null;
    if (existingScript) {
      existingScript.addEventListener('load', () => resolve(), { once: true });
      existingScript.addEventListener('error', () => reject(new Error('Không tải được Google Login.')), { once: true });
      return;
    }

    const script = document.createElement('script');
    script.id = GOOGLE_SCRIPT_ID;
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error('Không tải được Google Login.'));
    document.head.appendChild(script);
  });
}

function decodeJwtPayload(token: string) {
  const payload = token.split('.')[1];
  if (!payload) throw new Error('Google token không hợp lệ.');

  const normalized = payload.replace(/-/g, '+').replace(/_/g, '/');
  const decoded = decodeURIComponent(
    atob(normalized)
      .split('')
      .map(char => `%${(`00${char.charCodeAt(0).toString(16)}`).slice(-2)}`)
      .join('')
  );

  return JSON.parse(decoded) as { email?: string; name?: string; picture?: string };
}

export async function requestGoogleProfile() {
  await loadGoogleScript();

  return new Promise<{ email: string; name: string; picture?: string }>((resolve, reject) => {
    if (!window.google?.accounts?.id) {
      reject(new Error('Google Login chưa sẵn sàng.'));
      return;
    }

    window.google.accounts.id.initialize({
      client_id: GOOGLE_CLIENT_ID,
      callback: response => {
        try {
          if (!response.credential) throw new Error('Không nhận được phản hồi từ Google.');
          const payload = decodeJwtPayload(response.credential);
          if (!payload.email) throw new Error('Tài khoản Google chưa có email.');
          resolve({
            email: payload.email,
            name: payload.name || payload.email,
            picture: payload.picture,
          });
        } catch (error) {
          reject(error);
        }
      },
    });

    window.google.accounts.id.prompt();
  });
}
