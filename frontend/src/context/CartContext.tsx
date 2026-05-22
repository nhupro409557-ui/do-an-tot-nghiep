import React, { useMemo } from 'react';
import { CartItem, useCartStore } from '../store/cartStore';

export type { CartItem };

export const CartProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return <>{children}</>;
};

export const useCart = () => {
  const items = useCartStore((state) => state.items);
  const addToCart = useCartStore((state) => state.addToCart);
  const removeFromCart = useCartStore((state) => state.removeFromCart);
  const updateQuantity = useCartStore((state) => state.updateQuantity);
  const clearCart = useCartStore((state) => state.clearCart);

  const totalQuantity = useMemo(
    () => items.reduce((sum, item) => sum + item.quantity, 0),
    [items]
  );
  const totalPrice = useMemo(
    () => items.reduce((sum, item) => sum + item.price * item.quantity, 0),
    [items]
  );

  return {
    items,
    addToCart,
    removeFromCart,
    updateQuantity,
    clearCart,
    totalQuantity,
    totalPrice,
  };
};
