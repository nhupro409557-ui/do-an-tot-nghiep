import { useEffect, useState } from 'react';
import { publicApi } from '../../../services/publicApi';

export function useAccountFavorites(userId?: string) {
  const [favorites, setFavorites] = useState<any[]>([]);

  useEffect(() => {
    if (!userId) return;
    publicApi.listFavorites()
      .then(data => setFavorites(data))
      .catch(e => console.log('Error loading favorites', e));
  }, [userId]);

  const removeFavorite = (productId: string) => {
    publicApi.toggleFavorite(productId).then((res) => {
      if (!res.favorited) {
        setFavorites(prev => prev.filter(product => product.id !== productId));
      }
    });
  };

  return { favorites, removeFavorite };
}
