# Ghi chú sửa lỗi React Doctor

Ngày cập nhật: 2026-06-03

## Mục tiêu

- Chạy `react-doctor` theo cách tạm thời, không cài package vào đồ án.
- Ưu tiên sửa nhóm `Bugs errors` trước, vì đây là nhóm có nguy cơ gây lỗi runtime hoặc hành vi React không ổn định.
- Giữ nguyên giao diện hiện tại, chỉ chỉnh logic nền, thứ tự hook, cleanup async/timer và lỗi mã hóa tiếng Việt trong các vùng đã chạm.

## Cách đã chạy React Doctor

Chạy trong thư mục `frontend`:

```powershell
npx react-doctor@latest --no-telemetry --offline
```

Lý do dùng cách này:

- Không thêm dependency vào `package.json`.
- Không sửa `package-lock.json`.
- Không cài hook hay skill vào project.
- `--no-telemetry` tắt telemetry.
- `--offline` không gửi score/share API.

Không dùng:

```powershell
npx react-doctor@latest install
```

Vì lệnh này có thể tạo skill/hook/config và làm đồ án có thêm file ngoài ý muốn.

## Kết quả kiểm tra

Trước khi sửa:

- React Doctor báo `Bugs > 29 errors`.

Sau khi sửa:

- React Doctor báo `Bugs > 0 errors`.
- Vẫn còn optional warnings như accessibility, maintainability, performance, security warning.
- `npm run lint` pass.

Lệnh kiểm tra đã dùng:

```powershell
npm run lint
npx react-doctor@latest --no-telemetry --offline
```

## Các file đã chỉnh

### `frontend/src/components/product/ProductDetail.tsx`

Nội dung chính:

- Sửa lỗi hook bị gọi có điều kiện bằng cách đưa effect xử lý phím media viewer lên trước nhánh `return` sớm.
- Thêm cleanup cho timer thông báo thêm vào giỏ hàng.
- Cleanup `document.body.style.overflow` khi component unmount.
- Chuyển reset lựa chọn sản phẩm/media từ `useEffect` sang cập nhật có điều kiện theo `product.id` và `activeVariant.id`.
- Effect Swiper chỉ còn điều khiển slide, không set state React.

Lưu ý:

- Với state phụ thuộc trực tiếp vào `product` hoặc `activeVariant`, tránh reset trong `useEffect` nếu mục tiêu chỉ là đồng bộ state theo prop.
- Nếu cần reset state khi đổi product, dùng key theo `product.id` hoặc cập nhật có điều kiện trong render theo mẫu `prevId !== currentId`.

### `frontend/src/pages/VerifyEmailPage.tsx`

Nội dung chính:

- Thêm cleanup cho timer chuyển hướng sau khi xác nhận email.
- Chặn cập nhật state nếu component đã unmount.
- Sửa lại tiếng Việt bị lỗi mã hóa trong file.

Lưu ý:

- Mọi `setTimeout` trong effect nên có `clearTimeout`.
- Promise trong effect nên có cờ `isActive` hoặc cơ chế hủy tương đương.

### `frontend/src/pages/CheckoutPage.tsx`

Nội dung chính:

- Sửa lỗi hook bị gọi có điều kiện do return giỏ hàng trống nằm trước `useEffect`.
- Chuyển nhánh UI giỏ hàng trống xuống sau hook.
- Phục hồi chữ tiếng Việt bị lỗi mã hóa trong file.

Lưu ý:

- Không đặt `return` sớm trước các hook trong cùng component.
- Nếu UI rỗng cần return sớm, vẫn phải đặt tất cả hook trước nhánh return đó.

### `frontend/src/components/admin/tabs/AdminOverviewTab.tsx`

Nội dung chính:

- Sửa cảnh báo component được định nghĩa bên trong component cha.
- Đổi tooltip nội bộ sang hàm render thường để Recharts dùng, tránh tạo component mới mỗi render.

Lưu ý:

- Không định nghĩa component viết hoa bên trong component khác nếu component đó được render như JSX.
- Nếu thư viện nhận render function, dùng function thường là đủ.

### `frontend/src/components/admin/tabs/AdminCustomersTab.tsx`

Nội dung chính:

- Đưa `usePermission('sys:manage_users')` ra biến top-level trong component.
- Không gọi hook trực tiếp trong JSX.
- Sửa lại tiếng Việt bị lỗi mã hóa trong file.

Lưu ý:

- Dù `usePermission` được truyền qua props, nếu bản chất nó là hook thì vẫn phải gọi ở top-level của component.

### `frontend/src/components/admin/tabs/AdminPermissionsTab.tsx`

Nội dung chính:

- Đưa các lời gọi `usePermission('customer:loyalty_adjust')` và `usePermission('customer:issue_voucher')` ra biến top-level.
- JSX chỉ dùng biến boolean đã tính.

Lưu ý:

- Không gọi hook trong điều kiện JSX như `{usePermission(...) && (...)}`.

### `frontend/src/components/admin/hooks/useAdminLogic.ts`

Nội dung chính:

- Sửa lỗi `useAnyPermission` bị gọi bên trong callback của `useMemo`.
- Tính từng quyền bằng hook ở top-level.
- Tạo `tabAccess` bằng `useMemo` từ các boolean quyền đã có.

Lưu ý:

- Không gọi hook trong callback của `useMemo`, `useCallback`, `.filter`, `.map`, hoặc helper function thông thường.
- Nếu cần lọc theo quyền, gọi hook trước để ra boolean, sau đó lọc bằng boolean.

### `frontend/src/hooks/useCatalog.ts`

Nội dung chính:

- Chốt `includeRankedFeatured` ở lần mount đầu bằng `useRef`.
- Thêm cleanup cho async load catalog.
- Tránh cập nhật state sau khi component đã unmount.

Lưu ý:

- Với option chỉ dùng để cấu hình lần mount đầu, dùng `useRef(Boolean(option))` giúp tránh effect bị xem như sync state theo prop.
- Với fetch async trong effect, luôn kiểm tra component còn active trước khi `setState`.

### `frontend/src/components/video/ImagesModal.tsx`

Nội dung chính:

- Tách outer modal và inner content.
- Outer kiểm tra `isOpen` và `playlist.length`.
- Inner được remount bằng `key` theo `initialIndex` và danh sách ảnh.
- Bỏ effect reset hàng loạt state khi mở modal.
- Thêm cleanup URL query `view` khi modal đóng/unmount.

Lưu ý:

- Với modal cần reset nhiều state khi mở, ưu tiên remount inner content bằng `key` thay vì gọi nhiều `setState` trong `useEffect`.
- Cách này giảm nhấp nháy UI và tránh cảnh báo state sync.

### `frontend/src/components/video/ReelsModal.tsx`

Nội dung chính:

- Tách outer modal và inner content giống `ImagesModal`.
- Bỏ effect reset state khi mở modal.
- Thêm cleanup URL query `watch` khi modal đóng/unmount.

Lưu ý:

- Modal video có nhiều state như pause, progress, comment, active slide. Remount inner content là cách gọn và ít rủi ro hơn reset thủ công.

### `frontend/src/components/product/ProductReviews.tsx`

Nội dung chính:

- Tách content theo key `productId + user`.
- Thêm cleanup cho fetch reviews và eligibility.
- Bỏ effect sync form từ `eligibility.existingReview`.
- Prefill form review ngay khi nhận eligibility.

Lưu ý:

- Nếu form cần prefill từ dữ liệu async, nên prefill tại thời điểm nhận dữ liệu thay vì thêm effect riêng chỉ để copy dữ liệu sang state.

### `frontend/src/components/VietnamAddressSelector.tsx`

Nội dung chính:

- Bỏ state `wards`.
- Derive danh sách phường/xã bằng `useMemo` từ `provinces` và `value.provinceId`.
- Sửa một số nhãn tiếng Việt có dấu.

Lưu ý:

- State nào có thể suy ra từ props/state khác thì không nên lưu thêm.
- Tránh pattern `useEffect(() => setDerivedState(...), [source])` nếu giá trị có thể tính bằng `useMemo`.

### `backend/PRODUCT_MANAGEMENT_NOTES.md`

Nội dung chính:

- Ghi lại các thay đổi React Doctor safe fixes.
- Ghi lại kết quả đã giảm `Bugs errors` về 0.

## Kinh nghiệm cho phiên sau

### 1. Không cài React Doctor vào project nếu chỉ cần audit

Nên chạy:

```powershell
npx react-doctor@latest --no-telemetry --offline
```

Chỉ cân nhắc `install` khi thật sự muốn thêm workflow/hook cho agent hoặc CI.

### 2. Sửa `Bugs errors` trước optional warnings

React Doctor có rất nhiều warning về style, accessibility, performance. Không nên sửa đại trà trong cùng lượt vì dễ làm đổi giao diện hoặc tạo diff lớn.

Thứ tự ưu tiên nên là:

1. Hook gọi sai vị trí.
2. Timer/subscription thiếu cleanup.
3. State sync từ prop/effect gây nhấp nháy hoặc stale UI.
4. Component định nghĩa bên trong component khác.
5. Accessibility/performance/maintainability optional warnings.

### 3. Với hook, nguyên tắc là top-level

Không gọi hook trong:

- JSX condition.
- `useMemo` callback.
- `useCallback` callback.
- `.map`, `.filter`, `.reduce`.
- `if`, `for`, function phụ thông thường.

Nên gọi hook trước, lưu vào biến:

```tsx
const canManageUsers = usePermission('sys:manage_users');
```

Sau đó JSX chỉ dùng biến:

```tsx
title={canManageUsers ? 'Quản lý khách hàng' : 'Tra cứu khách hàng'}
```

### 4. Với modal nhiều state, ưu tiên remount bằng `key`

Nếu modal cần reset nhiều state mỗi lần mở:

- `paused`
- `showComments`
- `copied`
- `activeIndex`
- `commentText`
- `replyTarget`
- `progress`

Không nên reset bằng một effect chứa nhiều `setState`.

Nên tách:

```tsx
function ModalOuter({ isOpen, items, initialIndex }) {
  if (!isOpen || items.length === 0) return null;
  return <ModalContent key={`${initialIndex}-${items.map(item => item.id).join('|')}`} />;
}
```

### 5. Với state suy ra được, dùng `useMemo`

Không nên:

```tsx
const [wards, setWards] = useState([]);

useEffect(() => {
  setWards(findWards(provinceId));
}, [provinceId]);
```

Nên:

```tsx
const wards = useMemo(() => findWards(provinceId), [provinceId, provinces]);
```

### 6. Với async effect, luôn có cleanup

Mẫu nên dùng:

```tsx
useEffect(() => {
  let isActive = true;

  loadData().then(data => {
    if (!isActive) return;
    setData(data);
  });

  return () => {
    isActive = false;
  };
}, []);
```

### 7. Với timer, luôn clear timer

Mẫu nên dùng:

```tsx
useEffect(() => {
  const timer = setTimeout(doSomething, 1200);
  return () => clearTimeout(timer);
}, []);
```

### 8. Cẩn thận với mã hóa tiếng Việt

Nếu đang chỉnh file có tiếng Việt bị lỗi như `Ã`, `Ä`, `á»`, `Æ`, nên sửa lại trong vùng đang chạm.

Trước khi hoàn tất, kiểm tra nhanh các file vừa sửa để tránh còn mojibake.

### 9. Không dùng Git khi chưa được yêu cầu

Theo quy định của project, không tự ý chạy:

- `git status`
- `git diff`
- `git add`
- `git commit`
- `git push`

Chỉ dùng Git khi user yêu cầu trực tiếp.

## Trạng thái hiện tại

- `npm run lint`: pass.
- React Doctor: không còn `Bugs errors`.
- Còn optional warnings, chủ yếu thuộc các nhóm:
  - Accessibility.
  - Maintainability.
  - Performance.
  - Security warnings.

Các optional warnings này nên xử lý theo từng nhóm nhỏ riêng để tránh đổi giao diện quá rộng.
