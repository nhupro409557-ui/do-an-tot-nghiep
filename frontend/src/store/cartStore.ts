import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { useShallow } from 'zustand/shallow';

export interface CartItem {
  productId: string;
  name: string;
  price: number;
  imageUrl: string;
  quantity: number;
  originalPrice?: number;
}

interface CartState {
  items: CartItem[];
  addToCart: (item: CartItem) => void;
  removeFromCart: (productId: string) => void;
  updateQuantity: (productId: string, quantity: number) => void;
  clearCart: () => void;
}

export const useCartStore = create<CartState>()(
  persist(
    (set) => ({
      items: [],
      addToCart: (newItem) =>
        set((state) => {
          const existing = state.items.find((item) => item.productId === newItem.productId);
          if (!existing) {
            return { items: [...state.items, newItem] };
          }

          return {
            items: state.items.map((item) =>
              item.productId === newItem.productId
                ? { ...item, quantity: item.quantity + newItem.quantity }
                : item,
            ),
          };
        }),
      removeFromCart: (productId) =>
        set((state) => ({
          items: state.items.filter((item) => item.productId !== productId),
        })),
      updateQuantity: (productId, quantity) =>
        set((state) => ({
          items:
            quantity <= 0
              ? state.items.filter((item) => item.productId !== productId)
              : state.items.map((item) =>
                  item.productId === productId ? { ...item, quantity } : item,
                ),
        })),
      clearCart: () => set({ items: [] }),
    }),
    {
      name: 'cartItems',
      partialize: (state) => ({ items: state.items }),
    },
  ),
);

export const useCartTotals = () =>
  useCartStore(
    useShallow((state) => ({
      totalQuantity: state.items.reduce((sum, item) => sum + item.quantity, 0),
      totalPrice: state.items.reduce((sum, item) => sum + item.price * item.quantity, 0),
    }))
  );

