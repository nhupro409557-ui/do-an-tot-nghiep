const GOOGLE_CLIENT_ID = '293864704533-n31a0a66ro184o9vkq8tv8m0b6l73tp1.apps.googleusercontent.com';
const GOOGLE_SCRIPT_ID = 'google-identity-services';

type GoogleCredentialResponse = {
  credential?: string;
};

interface GooglePromptNotification {
  isNotDisplayed: () => boolean;
  getNotDisplayedReason: () => string;
  isSkippedMoment: () => boolean;
  getSkippedReason: () => string;
  isDismissedMoment: () => boolean;
  getDismissedReason: () => string;
}

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (options: {
            client_id: string;
            callback: (response: GoogleCredentialResponse) => void;
          }) => void;
          prompt: (listener?: (notification: GooglePromptNotification) => void) => void;
          cancel: () => void;
        };
        oauth2: {
          initTokenClient: (config: {
            client_id: string;
            scope: string;
            callback: (response: { access_token: string; error?: string }) => void;
          }) => {
            requestAccessToken: () => void;
          };
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
    if (!window.google?.accounts?.oauth2) {
      reject(new Error('Thư viện Google Login chưa sẵn sàng.'));
      return;
    }

    try {
      const client = window.google.accounts.oauth2.initTokenClient({
        client_id: GOOGLE_CLIENT_ID,
        scope: 'email profile openid',
        callback: async (tokenResponse) => {
          if (tokenResponse.error) {
            reject(new Error(`Yêu cầu truy cập Google thất bại: ${tokenResponse.error}`));
            return;
          }

          const accessToken = tokenResponse.access_token;
          if (!accessToken) {
            reject(new Error('Không lấy được Token truy cập từ Google.'));
            return;
          }

          try {
            const res = await fetch(`https://www.googleapis.com/oauth2/v3/userinfo?access_token=${accessToken}`);
            if (!res.ok) throw new Error('Không thể tải thông tin hồ sơ từ Google.');

            const userInfo = await res.json();
            if (!userInfo.email) throw new Error('Tài khoản Google chưa liên kết Email.');

            resolve({
              email: userInfo.email,
              name: userInfo.name || userInfo.email,
              picture: userInfo.picture,
            });
          } catch (fetchErr: any) {
            reject(fetchErr);
          }
        },
      });

      client.requestAccessToken();
    } catch (err: any) {
      reject(err);
    }
  });
}
