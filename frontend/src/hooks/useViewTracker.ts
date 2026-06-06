import { useEffect, useRef } from 'react';
import { publicApi } from '../services/publicApi';

const HEARTBEAT_SECONDS = 10;

function currentScrollDepth() {
  const scrollTop = window.scrollY || document.documentElement.scrollTop || 0;
  const viewportHeight = window.innerHeight || document.documentElement.clientHeight || 0;
  const documentHeight = Math.max(
    document.body.scrollHeight,
    document.documentElement.scrollHeight,
    document.body.offsetHeight,
    document.documentElement.offsetHeight,
  );
  if (documentHeight <= viewportHeight) return 1;
  return Math.min(1, Math.max(0, (scrollTop + viewportHeight) / documentHeight));
}

export function useViewTracker(productId?: string | null) {
  const countedRef = useRef(false);
  const scrollDepthRef = useRef(0);

  useEffect(() => {
    countedRef.current = false;
    scrollDepthRef.current = 0;
    if (!productId) return undefined;

    const updateScrollDepth = () => {
      scrollDepthRef.current = Math.max(scrollDepthRef.current, currentScrollDepth());
    };

    const sendHeartbeat = async (activeSeconds: number) => {
      if (countedRef.current || document.visibilityState !== 'visible') return;
      updateScrollDepth();
      try {
        const result = await publicApi.recordProductViewHeartbeat(productId, {
          activeSeconds,
          scrollDepth: scrollDepthRef.current,
          source: 'product_detail',
          clientTimestamp: Date.now(),
        });
        if (result?.counted) countedRef.current = true;
      } catch {
        // Tracking must never interrupt the product page experience.
      }
    };

    updateScrollDepth();
    window.addEventListener('scroll', updateScrollDepth, { passive: true });
    window.addEventListener('resize', updateScrollDepth);

    const interval = window.setInterval(() => {
      void sendHeartbeat(HEARTBEAT_SECONDS);
    }, HEARTBEAT_SECONDS * 1000);

    const visibilityHandler = () => {
      if (document.visibilityState === 'visible') updateScrollDepth();
    };
    document.addEventListener('visibilitychange', visibilityHandler);

    const beforeUnloadHandler = () => {
      if (!countedRef.current && document.visibilityState === 'visible') {
        void sendHeartbeat(Math.min(HEARTBEAT_SECONDS, 5));
      }
    };
    window.addEventListener('pagehide', beforeUnloadHandler);

    return () => {
      window.clearInterval(interval);
      window.removeEventListener('scroll', updateScrollDepth);
      window.removeEventListener('resize', updateScrollDepth);
      window.removeEventListener('pagehide', beforeUnloadHandler);
      document.removeEventListener('visibilitychange', visibilityHandler);
    };
  }, [productId]);
}
