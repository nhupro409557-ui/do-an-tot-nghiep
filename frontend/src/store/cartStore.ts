import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface AttachedServiceItem {
  serviceId: string;
  code: string;
  name: string;
  price: number;
}

export interface CartItem {
  cartItemId?: string; // Khóa chính duy nhất trong store
  productId: string; // ID sản phẩm/variant thực tế
  variantId?: string; // ID biến thể để checkout đúng giá/flash sale của biến thể
  usedDeviceId?: string;
  name: string;
  price: number;
  imageUrl: string;
  quantity: number;
  originalPrice?: number;
  categoryId?: string | null;
  category_id?: string | null;
  brandId?: string | null;
  brand_id?: string | null;
  isFlashSale?: boolean;
  is_flash_sale?: boolean;
  flashSaleId?: string;
  flashSalePerUserLimit?: number | null;

  // Dịch vụ đi kèm
  attachedServices?: AttachedServiceItem[];

  // Sản phẩm mua kèm
  isAccessory?: boolean;
  parentProductId?: string;
  isUsedDevice?: boolean;

  // Trạng thái tích chọn để thanh toán
  checked?: boolean;
}

interface CartState {
  items: CartItem[];
  addToCart: (item: CartItem) => void;
  removeFromCart: (cartItemId: string) => void;
  updateQuantity: (cartItemId: string, quantity: number) => void;
  clearCart: () => void;
  toggleCheckItem: (cartItemId: string) => void;
  toggleCheckAll: (checked: boolean) => void;
  clearCheckedItems: () => void;
}

// Hàm so sánh các dịch vụ đi kèm có giống nhau không
const areServicesEqual = (a?: AttachedServiceItem[], b?: AttachedServiceItem[]) => {
  if (!a && !b) return true;
  if (!a || !b) return false;
  if (a.length !== b.length) return false;
  const aIds = a.map(s => s.serviceId).sort();
  const bIds = b.map(s => s.serviceId).sort();
  return aIds.length === bIds.length && aIds.every((id, idx) => id === bIds[idx]);
};

// Hàm sinh cartItemId duy nhất cho item trong store
export const generateCartItemId = (item: CartItem): string => {
  if (item.isUsedDevice && item.usedDeviceId) {
    return `used-${item.usedDeviceId}`;
  }
  const serviceSuffix = item.attachedServices && item.attachedServices.length > 0
    ? `_srv-${item.attachedServices.map(s => s.serviceId).sort().join('-')}`
    : '';
  const accessorySuffix = item.isAccessory
    ? `_acc-${item.parentProductId}`
    : '';
  const variantSuffix = item.variantId
    ? `_var-${item.variantId}`
    : '';
  return `${item.productId}${variantSuffix}${serviceSuffix}${accessorySuffix}`;
};

export const useCartStore = create<CartState>()(
  persist(
    (set) => ({
      items: [],
      addToCart: (newItem) =>
        set((state) => {
          const cartItemId = newItem.cartItemId || generateCartItemId(newItem);
          const itemToInsert = { ...newItem, cartItemId, checked: newItem.checked ?? true };

          const existingIdx = state.items.findIndex((item) => item.cartItemId === cartItemId);
          if (existingIdx === -1) {
            return { items: [...state.items, itemToInsert] };
          }

          const updatedItems = [...state.items];
          if (updatedItems[existingIdx].isUsedDevice) {
            updatedItems[existingIdx] = {
              ...updatedItems[existingIdx],
              quantity: 1,
              checked: updatedItems[existingIdx].checked ?? true,
            };
            return { items: updatedItems };
          }
          updatedItems[existingIdx] = {
            ...updatedItems[existingIdx],
            quantity: updatedItems[existingIdx].quantity + newItem.quantity,
            checked: updatedItems[existingIdx].checked ?? true,
          };
          return { items: updatedItems };
        }),
      removeFromCart: (cartItemId) =>
        set((state) => ({
          items: state.items.filter((item) => (item.cartItemId || generateCartItemId(item)) !== cartItemId),
        })),
      updateQuantity: (cartItemId, quantity) =>
        set((state) => ({
          items:
            quantity <= 0
              ? state.items.filter((item) => (item.cartItemId || generateCartItemId(item)) !== cartItemId)
              : state.items.map((item) =>
                  (item.cartItemId || generateCartItemId(item)) === cartItemId
                    ? { ...item, cartItemId: item.cartItemId || generateCartItemId(item), quantity }
                    : item,
                ).map((item) =>
                  (item.cartItemId || generateCartItemId(item)) === cartItemId && item.isUsedDevice
                    ? { ...item, quantity: 1 }
                    : item,
                ),
        })),
      clearCart: () => set({ items: [] }),
      toggleCheckItem: (cartItemId) =>
        set((state) => {
          // 1. Cập nhật checked của item đích
          const updatedItems = state.items.map((item) => {
            const currentId = item.cartItemId || generateCartItemId(item);
            if (currentId === cartItemId) {
              return { ...item, checked: !item.checked };
            }
            return item;
          });

          // 2. Tìm item vừa toggle
          const targetItem = state.items.find(
            (item) => (item.cartItemId || generateCartItemId(item)) === cartItemId
          );

          if (targetItem && !targetItem.isAccessory) {
            // targetItem là sản phẩm chính. Đồng bộ checked của các phụ kiện đi kèm với nó.
            const targetId = targetItem.productId;
            const parentChecked = !targetItem.checked; // Trạng thái mới sau khi toggle

            return {
              items: updatedItems.map((item) => {
                if (item.isAccessory && item.parentProductId === targetId) {
                  return { ...item, checked: parentChecked };
                }
                return item;
              }),
            };
          }

          return { items: updatedItems };
        }),
      toggleCheckAll: (checked) =>
        set((state) => ({
          items: state.items.map((item) => ({ ...item, checked })),
        })),
      clearCheckedItems: () =>
        set((state) => ({
          items: state.items.filter((item) => item.checked === false),
        })),
    }),
    {
      name: 'cartItems',
      partialize: (state) => ({ items: state.items }),
    },
  ),
);

// Helper chuẩn hóa, phân bổ và tách dòng phụ kiện mua kèm
export function getNormalizedCartItems(items: CartItem[]): CartItem[] {
  // Đảm bảo mọi item đều có cartItemId
  const sanitizedItems = (items || []).map(item => ({
    ...item,
    cartItemId: item.cartItemId || generateCartItemId(item)
  }));

  // 1. Phân loại sản phẩm chính và sản phẩm phụ
  const mainItems = sanitizedItems.filter(item => !item.isAccessory);
  const accessoryItems = sanitizedItems.filter(item => item.isAccessory);

  // Lưu trữ danh sách ID các sản phẩm chính đang có trong giỏ hàng
  const mainProductIds = new Set(mainItems.map(item => item.productId));

  const normalized: CartItem[] = [];

  // Thêm tất cả sản phẩm chính vào danh sách normalized
  mainItems.forEach(item => {
    normalized.push({ ...item });
  });

  // Nhóm các accessory theo productId để gộp số lượng trước khi phân bổ
  const accessoryGroups: Record<string, CartItem[]> = {};
  accessoryItems.forEach(item => {
    if (!accessoryGroups[item.productId]) {
      accessoryGroups[item.productId] = [];
    }
    accessoryGroups[item.productId].push(item);
  });

  // Phân bổ từng nhóm accessory
  Object.entries(accessoryGroups).forEach(([productId, group]) => {
    // Tổng số lượng của phụ kiện này trong giỏ hàng
    const totalQty = group.reduce((sum, item) => sum + item.quantity, 0);

    // Tìm xem phụ kiện này đi kèm với sản phẩm chính nào (lấy parentProductId từ item đầu tiên)
    const parentProductId = group[0].parentProductId;

    // Kiểm tra xem sản phẩm chính đó có trong giỏ hàng không
    const hasParentInCart = parentProductId && mainProductIds.has(parentProductId);

    if (hasParentInCart) {
      // Có sản phẩm chính -> ưu đãi mua kèm nhưng backend chưa xác nhận offer nên không tự giảm giá.
      const baseOriginalPrice = Number(group[0].originalPrice || 0);
      const finalPrice = baseOriginalPrice || Number(group[0].price || 0);

      normalized.push({
        ...group[0],
        cartItemId: `${group[0].cartItemId}-normal`,
        productId: `${productId}-normal`,
        name: group[0].name.replace(' (Sản phẩm mua kèm được giảm giá)', ''),
        quantity: totalQty,
        price: finalPrice,
        originalPrice: undefined,
        isAccessory: false,
        parentProductId: undefined,
      });
    } else {
      // Không có sản phẩm chính -> tính theo giá gốc cho toàn bộ số lượng
      const baseOriginalPrice = Number(group[0].originalPrice || 0);
      normalized.push({
        ...group[0],
        cartItemId: `${group[0].cartItemId}-normal`,
        productId: `${productId}-normal`,
        name: group[0].name.replace(' (Sản phẩm mua kèm được giảm giá)', ''),
        quantity: totalQty,
        price: baseOriginalPrice || group[0].price, // Sử dụng giá gốc
        originalPrice: undefined,
        isAccessory: false,
        parentProductId: undefined,
      });
    }
  });

  return normalized;
}
