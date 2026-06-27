import React, { useMemo } from 'react';
import { CartItem, useCartStore, getNormalizedCartItems, generateCartItemId } from '../store/cartStore';

export type { CartItem };

export const CartProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  return <>{children}</>;
};

export const useCart = () => {
  const rawItems = useCartStore((state) => state.items);
  const rawAddToCart = useCartStore((state) => state.addToCart);
  const rawRemoveFromCart = useCartStore((state) => state.removeFromCart);
  const rawUpdateQuantity = useCartStore((state) => state.updateQuantity);
  const clearCart = useCartStore((state) => state.clearCart);
  const toggleCheckItem = useCartStore((state) => state.toggleCheckItem);
  const toggleCheckAll = useCartStore((state) => state.toggleCheckAll);
  const clearCheckedItems = useCartStore((state) => state.clearCheckedItems);

  // 1. Danh sách sản phẩm hiển thị sau khi chuẩn hóa (tách dòng, áp giá)
  const items = useMemo(() => getNormalizedCartItems(rawItems), [rawItems]);

  // 2. Thêm vào giỏ hàng
  const addToCart = (newItem: CartItem) => {
    rawAddToCart(newItem);
  };

  // 3. Cập nhật số lượng
  const updateQuantity = (id: string | number, newQty: number) => {
    const cartItemId = String(id);
    const isAccessoryLine = cartItemId.endsWith('-accessory');
    const isNormalLine = cartItemId.endsWith('-normal');
    
    // Tìm item hiển thị hiện tại trong danh sách đã chuẩn hóa để biết số lượng hiện tại của dòng này
    const displayItem = items.find(item => String(item.cartItemId || item.productId) === cartItemId);
    if (!displayItem) return;

    // Tìm item gốc trong store tương ứng
    const baseCartItemId = isAccessoryLine 
      ? cartItemId.slice(0, -10) 
      : (isNormalLine ? cartItemId.slice(0, -7) : cartItemId);

    // Tìm item gốc trong store
    const rawItem = rawItems.find(item => String(item.cartItemId || generateCartItemId(item)) === baseCartItemId);
    if (!rawItem) return;

    const diff = newQty - displayItem.quantity;
    const newRawQty = rawItem.quantity + diff;

    rawUpdateQuantity(rawItem.cartItemId || generateCartItemId(rawItem), newRawQty);
  };

  // 4. Xóa khỏi giỏ hàng
  const removeFromCart = (id: string | number) => {
    const cartItemId = String(id);
    const isAccessoryLine = cartItemId.endsWith('-accessory');
    const isNormalLine = cartItemId.endsWith('-normal');

    const displayItem = items.find(item => String(item.cartItemId || item.productId) === cartItemId);
    if (!displayItem) return;

    const baseCartItemId = isAccessoryLine 
      ? cartItemId.slice(0, -10) 
      : (isNormalLine ? cartItemId.slice(0, -7) : cartItemId);

    const rawItem = rawItems.find(item => String(item.cartItemId || generateCartItemId(item)) === baseCartItemId);
    if (!rawItem) return;

    // Giảm số lượng của item gốc đi đúng bằng số lượng của dòng hiển thị bị xóa
    const newRawQty = rawItem.quantity - displayItem.quantity;
    rawUpdateQuantity(rawItem.cartItemId || generateCartItemId(rawItem), newRawQty);
  };

  // 5. Tính toán tổng số lượng hiển thị (chỉ tính các item được check)
  const totalQuantity = useMemo(
    () => items.filter(item => item.checked !== false).reduce((sum, item) => sum + item.quantity, 0),
    [items]
  );

  // 6. Tính toán tổng số tiền hiển thị (đã bao gồm dịch vụ đi kèm của sản phẩm chính, chỉ tính các item được check)
  const totalPrice = useMemo(() => {
    return items.filter(item => item.checked !== false).reduce((sum, item) => {
      const servicesPrice = item.attachedServices?.reduce((s, srv) => s + srv.price, 0) || 0;
      return sum + (item.price + servicesPrice) * item.quantity;
    }, 0);
  }, [items]);

  return {
    items,
    addToCart,
    removeFromCart,
    updateQuantity,
    clearCart,
    totalQuantity,
    totalPrice,
    toggleCheckItem,
    toggleCheckAll,
    clearCheckedItems,
  };
};
