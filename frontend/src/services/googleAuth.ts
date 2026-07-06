const GOOGLE_CLIENT_ID = '293864704533-n31a0a66ro184o9vkq8tv8m0b6l73tp1.apps.googleusercontent.com';
const GOOGLE_SCRIPT_ID = 'google-identity-services';

declare global {
  interface Window {
    google?: {
      accounts: {
        id?: {
          initialize: (options: {
            client_id: string;
            callback: (response: { credential?: string }) => void;
          }) => void;
          prompt: (listener?: (notification: unknown) => void) => void;
          cancel: () => void;
        };
        oauth2?: {
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
    if (window.google?.accounts?.oauth2 || window.google?.accounts?.id) {
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

export async function requestGoogleProfile() {
  await loadGoogleScript();

  return new Promise<{ access_token: string }>((resolve, reject) => {
    if (!window.google?.accounts?.oauth2) {
      reject(new Error('Thư viện Google Login chưa sẵn sàng.'));
      return;
    }

    try {
      const client = window.google.accounts.oauth2.initTokenClient({
        client_id: GOOGLE_CLIENT_ID,
        scope: 'email profile openid',
        callback: (tokenResponse) => {
          if (tokenResponse.error) {
            reject(new Error(`Yêu cầu truy cập Google thất bại: ${tokenResponse.error}`));
            return;
          }

          const accessToken = tokenResponse.access_token;
          if (!accessToken) {
            reject(new Error('Không lấy được token truy cập từ Google.'));
            return;
          }

          resolve({ access_token: accessToken });
        },
      });

      client.requestAccessToken();
    } catch (err: any) {
      reject(err);
    }
  });
}
