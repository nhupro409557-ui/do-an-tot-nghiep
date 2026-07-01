import { useEffect, useState } from 'react';
import type { NavigateFunction } from 'react-router-dom';
import { signOut } from '../../../services/authDb';
import { publicApi } from '../../../services/publicApi';
import type { AccountTab, AuthSession } from '../types/accountDashboardTypes';

export function useAccountSessions(userId: string | undefined, activeTab: AccountTab, navigate: NavigateFunction) {
  const [authSessions, setAuthSessions] = useState<AuthSession[]>([]);

  useEffect(() => {
    if (!userId || activeTab !== 'settings') return;
    publicApi.listAuthSessions()
      .then(data => setAuthSessions(data))
      .catch(e => console.log('Error loading auth sessions', e));
  }, [userId, activeTab]);

  const revokeSession = async (sessionId: string, isCurrent: boolean) => {
    if (isCurrent) {
      await publicApi.revokeAuthSession(sessionId);
      await signOut();
      navigate('/login');
      return;
    }

    await publicApi.revokeAuthSession(sessionId);
    setAuthSessions(sessions => sessions.filter(session => session.id !== sessionId));
  };

  return { authSessions, revokeSession };
}
