# Ghi chÃº sá»­a lá»—i React Doctor

NgÃ y cáº­p nháº­t: 2026-06-03

## Má»¥c tiÃªu

- Cháº¡y `react-doctor` theo cÃ¡ch táº¡m thá»i, khÃ´ng cÃ i package vÃ o Ä‘á»“ Ã¡n.
- Æ¯u tiÃªn sá»­a nhÃ³m `Bugs errors` trÆ°á»›c, vÃ¬ Ä‘Ã¢y lÃ  nhÃ³m cÃ³ nguy cÆ¡ gÃ¢y lá»—i runtime hoáº·c hÃ nh vi React khÃ´ng á»•n Ä‘á»‹nh.
- Giá»¯ nguyÃªn giao diá»‡n hiá»‡n táº¡i, chá»‰ chá»‰nh logic ná»n, thá»© tá»± hook, cleanup async/timer vÃ  lá»—i mÃ£ hÃ³a tiáº¿ng Viá»‡t trong cÃ¡c vÃ¹ng Ä‘Ã£ cháº¡m.

## CÃ¡ch Ä‘Ã£ cháº¡y React Doctor

Cháº¡y trong thÆ° má»¥c `frontend`:

```powershell
npx react-doctor@latest --no-telemetry --offline
```

LÃ½ do dÃ¹ng cÃ¡ch nÃ y:

- KhÃ´ng thÃªm dependency vÃ o `package.json`.
- KhÃ´ng sá»­a `package-lock.json`.
- KhÃ´ng cÃ i hook hay skill vÃ o project.
- `--no-telemetry` táº¯t telemetry.
- `--offline` khÃ´ng gá»­i score/share API.

KhÃ´ng dÃ¹ng:

```powershell
npx react-doctor@latest install
```

VÃ¬ lá»‡nh nÃ y cÃ³ thá»ƒ táº¡o skill/hook/config vÃ  lÃ m Ä‘á»“ Ã¡n cÃ³ thÃªm file ngoÃ i Ã½ muá»‘n.

## Káº¿t quáº£ kiá»ƒm tra

TrÆ°á»›c khi sá»­a:

- React Doctor bÃ¡o `Bugs > 29 errors`.

Sau khi sá»­a:

- React Doctor bÃ¡o `Bugs > 0 errors`.
- Váº«n cÃ²n optional warnings nhÆ° accessibility, maintainability, performance, security warning.
- `npm run lint` pass.

Lá»‡nh kiá»ƒm tra Ä‘Ã£ dÃ¹ng:

```powershell
npm run lint
npx react-doctor@latest --no-telemetry --offline
```

## CÃ¡c file Ä‘Ã£ chá»‰nh

### `frontend/src/features/products/components/ProductDetail.tsx`

Ná»™i dung chÃ­nh:

- Sá»­a lá»—i hook bá»‹ gá»i cÃ³ Ä‘iá»u kiá»‡n báº±ng cÃ¡ch Ä‘Æ°a effect xá»­ lÃ½ phÃ­m media viewer lÃªn trÆ°á»›c nhÃ¡nh `return` sá»›m.
- ThÃªm cleanup cho timer thÃ´ng bÃ¡o thÃªm vÃ o giá» hÃ ng.
- Cleanup `document.body.style.overflow` khi component unmount.
- Chuyá»ƒn reset lá»±a chá»n sáº£n pháº©m/media tá»« `useEffect` sang cáº­p nháº­t cÃ³ Ä‘iá»u kiá»‡n theo `product.id` vÃ  `activeVariant.id`.
- Effect Swiper chá»‰ cÃ²n Ä‘iá»u khiá»ƒn slide, khÃ´ng set state React.

LÆ°u Ã½:

- Vá»›i state phá»¥ thuá»™c trá»±c tiáº¿p vÃ o `product` hoáº·c `activeVariant`, trÃ¡nh reset trong `useEffect` náº¿u má»¥c tiÃªu chá»‰ lÃ  Ä‘á»“ng bá»™ state theo prop.
- Náº¿u cáº§n reset state khi Ä‘á»•i product, dÃ¹ng key theo `product.id` hoáº·c cáº­p nháº­t cÃ³ Ä‘iá»u kiá»‡n trong render theo máº«u `prevId !== currentId`.

### `frontend/src/features/account/pages/VerifyEmailPage.tsx`

Ná»™i dung chÃ­nh:

- ThÃªm cleanup cho timer chuyá»ƒn hÆ°á»›ng sau khi xÃ¡c nháº­n email.
- Cháº·n cáº­p nháº­t state náº¿u component Ä‘Ã£ unmount.
- Sá»­a láº¡i tiáº¿ng Viá»‡t bá»‹ lá»—i mÃ£ hÃ³a trong file.

LÆ°u Ã½:

- Má»i `setTimeout` trong effect nÃªn cÃ³ `clearTimeout`.
- Promise trong effect nÃªn cÃ³ cá» `isActive` hoáº·c cÆ¡ cháº¿ há»§y tÆ°Æ¡ng Ä‘Æ°Æ¡ng.

### `frontend/src/features/storefront-commerce/pages/CheckoutPage.tsx`

Ná»™i dung chÃ­nh:

- Sá»­a lá»—i hook bá»‹ gá»i cÃ³ Ä‘iá»u kiá»‡n do return giá» hÃ ng trá»‘ng náº±m trÆ°á»›c `useEffect`.
- Chuyá»ƒn nhÃ¡nh UI giá» hÃ ng trá»‘ng xuá»‘ng sau hook.
- Phá»¥c há»“i chá»¯ tiáº¿ng Viá»‡t bá»‹ lá»—i mÃ£ hÃ³a trong file.

LÆ°u Ã½:

- KhÃ´ng Ä‘áº·t `return` sá»›m trÆ°á»›c cÃ¡c hook trong cÃ¹ng component.
- Náº¿u UI rá»—ng cáº§n return sá»›m, váº«n pháº£i Ä‘áº·t táº¥t cáº£ hook trÆ°á»›c nhÃ¡nh return Ä‘Ã³.

### `frontend/src/features/admin-overview/components/AdminOverviewTab.tsx`

Ná»™i dung chÃ­nh:

- Sá»­a cáº£nh bÃ¡o component Ä‘Æ°á»£c Ä‘á»‹nh nghÄ©a bÃªn trong component cha.
- Äá»•i tooltip ná»™i bá»™ sang hÃ m render thÆ°á»ng Ä‘á»ƒ Recharts dÃ¹ng, trÃ¡nh táº¡o component má»›i má»—i render.

LÆ°u Ã½:

- KhÃ´ng Ä‘á»‹nh nghÄ©a component viáº¿t hoa bÃªn trong component khÃ¡c náº¿u component Ä‘Ã³ Ä‘Æ°á»£c render nhÆ° JSX.
- Náº¿u thÆ° viá»‡n nháº­n render function, dÃ¹ng function thÆ°á»ng lÃ  Ä‘á»§.

### `frontend/src/features/admin-customers/components/AdminCustomersTab.tsx`

Ná»™i dung chÃ­nh:

- ÄÆ°a `usePermission('sys:manage_users')` ra biáº¿n top-level trong component.
- KhÃ´ng gá»i hook trá»±c tiáº¿p trong JSX.
- Sá»­a láº¡i tiáº¿ng Viá»‡t bá»‹ lá»—i mÃ£ hÃ³a trong file.

LÆ°u Ã½:

- DÃ¹ `usePermission` Ä‘Æ°á»£c truyá»n qua props, náº¿u báº£n cháº¥t nÃ³ lÃ  hook thÃ¬ váº«n pháº£i gá»i á»Ÿ top-level cá»§a component.

### `frontend/src/features/admin-permissions/components/AdminPermissionsTab.tsx`

Ná»™i dung chÃ­nh:

- ÄÆ°a cÃ¡c lá»i gá»i `usePermission('customer:loyalty_adjust')` vÃ  `usePermission('customer:issue_voucher')` ra biáº¿n top-level.
- JSX chá»‰ dÃ¹ng biáº¿n boolean Ä‘Ã£ tÃ­nh.

LÆ°u Ã½:

- KhÃ´ng gá»i hook trong Ä‘iá»u kiá»‡n JSX nhÆ° `{usePermission(...) && (...)}`.

### `frontend/src/features/admin-shell/hooks/useAdminLogic.ts`

Ná»™i dung chÃ­nh:

- Sá»­a lá»—i `useAnyPermission` bá»‹ gá»i bÃªn trong callback cá»§a `useMemo`.
- TÃ­nh tá»«ng quyá»n báº±ng hook á»Ÿ top-level.
- Táº¡o `tabAccess` báº±ng `useMemo` tá»« cÃ¡c boolean quyá»n Ä‘Ã£ cÃ³.

LÆ°u Ã½:

- KhÃ´ng gá»i hook trong callback cá»§a `useMemo`, `useCallback`, `.filter`, `.map`, hoáº·c helper function thÃ´ng thÆ°á»ng.
- Náº¿u cáº§n lá»c theo quyá»n, gá»i hook trÆ°á»›c Ä‘á»ƒ ra boolean, sau Ä‘Ã³ lá»c báº±ng boolean.

### `frontend/src/hooks/useCatalog.ts`

Ná»™i dung chÃ­nh:

- Chá»‘t `includeRankedFeatured` á»Ÿ láº§n mount Ä‘áº§u báº±ng `useRef`.
- ThÃªm cleanup cho async load catalog.
- TrÃ¡nh cáº­p nháº­t state sau khi component Ä‘Ã£ unmount.

LÆ°u Ã½:

- Vá»›i option chá»‰ dÃ¹ng Ä‘á»ƒ cáº¥u hÃ¬nh láº§n mount Ä‘áº§u, dÃ¹ng `useRef(Boolean(option))` giÃºp trÃ¡nh effect bá»‹ xem nhÆ° sync state theo prop.
- Vá»›i fetch async trong effect, luÃ´n kiá»ƒm tra component cÃ²n active trÆ°á»›c khi `setState`.

### `frontend/src/features/media/components/ImagesModal.tsx`

Ná»™i dung chÃ­nh:

- TÃ¡ch outer modal vÃ  inner content.
- Outer kiá»ƒm tra `isOpen` vÃ  `playlist.length`.
- Inner Ä‘Æ°á»£c remount báº±ng `key` theo `initialIndex` vÃ  danh sÃ¡ch áº£nh.
- Bá» effect reset hÃ ng loáº¡t state khi má»Ÿ modal.
- ThÃªm cleanup URL query `view` khi modal Ä‘Ã³ng/unmount.

LÆ°u Ã½:

- Vá»›i modal cáº§n reset nhiá»u state khi má»Ÿ, Æ°u tiÃªn remount inner content báº±ng `key` thay vÃ¬ gá»i nhiá»u `setState` trong `useEffect`.
- CÃ¡ch nÃ y giáº£m nháº¥p nhÃ¡y UI vÃ  trÃ¡nh cáº£nh bÃ¡o state sync.

### `frontend/src/features/media/components/ReelsModal.tsx`

Ná»™i dung chÃ­nh:

- TÃ¡ch outer modal vÃ  inner content giá»‘ng `ImagesModal`.
- Bá» effect reset state khi má»Ÿ modal.
- ThÃªm cleanup URL query `watch` khi modal Ä‘Ã³ng/unmount.

LÆ°u Ã½:

- Modal video cÃ³ nhiá»u state nhÆ° pause, progress, comment, active slide. Remount inner content lÃ  cÃ¡ch gá»n vÃ  Ã­t rá»§i ro hÆ¡n reset thá»§ cÃ´ng.

### `frontend/src/features/products/components/ProductReviews.tsx`

Ná»™i dung chÃ­nh:

- TÃ¡ch content theo key `productId + user`.
- ThÃªm cleanup cho fetch reviews vÃ  eligibility.
- Bá» effect sync form tá»« `eligibility.existingReview`.
- Prefill form review ngay khi nháº­n eligibility.

LÆ°u Ã½:

- Náº¿u form cáº§n prefill tá»« dá»¯ liá»‡u async, nÃªn prefill táº¡i thá»i Ä‘iá»ƒm nháº­n dá»¯ liá»‡u thay vÃ¬ thÃªm effect riÃªng chá»‰ Ä‘á»ƒ copy dá»¯ liá»‡u sang state.

### `frontend/src/features/shipping/components/VietnamAddressSelector.tsx`

Ná»™i dung chÃ­nh:

- Bá» state `wards`.
- Derive danh sÃ¡ch phÆ°á»ng/xÃ£ báº±ng `useMemo` tá»« `provinces` vÃ  `value.provinceId`.
- Sá»­a má»™t sá»‘ nhÃ£n tiáº¿ng Viá»‡t cÃ³ dáº¥u.

LÆ°u Ã½:

- State nÃ o cÃ³ thá»ƒ suy ra tá»« props/state khÃ¡c thÃ¬ khÃ´ng nÃªn lÆ°u thÃªm.
- TrÃ¡nh pattern `useEffect(() => setDerivedState(...), [source])` náº¿u giÃ¡ trá»‹ cÃ³ thá»ƒ tÃ­nh báº±ng `useMemo`.

### `backend/PRODUCT_MANAGEMENT_NOTES.md`

Ná»™i dung chÃ­nh:

- Ghi láº¡i cÃ¡c thay Ä‘á»•i React Doctor safe fixes.
- Ghi láº¡i káº¿t quáº£ Ä‘Ã£ giáº£m `Bugs errors` vá» 0.

## Kinh nghiá»‡m cho phiÃªn sau

### 1. KhÃ´ng cÃ i React Doctor vÃ o project náº¿u chá»‰ cáº§n audit

NÃªn cháº¡y:

```powershell
npx react-doctor@latest --no-telemetry --offline
```

Chá»‰ cÃ¢n nháº¯c `install` khi tháº­t sá»± muá»‘n thÃªm workflow/hook cho agent hoáº·c CI.

### 2. Sá»­a `Bugs errors` trÆ°á»›c optional warnings

React Doctor cÃ³ ráº¥t nhiá»u warning vá» style, accessibility, performance. KhÃ´ng nÃªn sá»­a Ä‘áº¡i trÃ  trong cÃ¹ng lÆ°á»£t vÃ¬ dá»… lÃ m Ä‘á»•i giao diá»‡n hoáº·c táº¡o diff lá»›n.

Thá»© tá»± Æ°u tiÃªn nÃªn lÃ :

1. Hook gá»i sai vá»‹ trÃ­.
2. Timer/subscription thiáº¿u cleanup.
3. State sync tá»« prop/effect gÃ¢y nháº¥p nhÃ¡y hoáº·c stale UI.
4. Component Ä‘á»‹nh nghÄ©a bÃªn trong component khÃ¡c.
5. Accessibility/performance/maintainability optional warnings.

### 3. Vá»›i hook, nguyÃªn táº¯c lÃ  top-level

KhÃ´ng gá»i hook trong:

- JSX condition.
- `useMemo` callback.
- `useCallback` callback.
- `.map`, `.filter`, `.reduce`.
- `if`, `for`, function phá»¥ thÃ´ng thÆ°á»ng.

NÃªn gá»i hook trÆ°á»›c, lÆ°u vÃ o biáº¿n:

```tsx
const canManageUsers = usePermission('sys:manage_users');
```

Sau Ä‘Ã³ JSX chá»‰ dÃ¹ng biáº¿n:

```tsx
title={canManageUsers ? 'Quáº£n lÃ½ khÃ¡ch hÃ ng' : 'Tra cá»©u khÃ¡ch hÃ ng'}
```

### 4. Vá»›i modal nhiá»u state, Æ°u tiÃªn remount báº±ng `key`

Náº¿u modal cáº§n reset nhiá»u state má»—i láº§n má»Ÿ:

- `paused`
- `showComments`
- `copied`
- `activeIndex`
- `commentText`
- `replyTarget`
- `progress`

KhÃ´ng nÃªn reset báº±ng má»™t effect chá»©a nhiá»u `setState`.

NÃªn tÃ¡ch:

```tsx
function ModalOuter({ isOpen, items, initialIndex }) {
  if (!isOpen || items.length === 0) return null;
  return <ModalContent key={`${initialIndex}-${items.map(item => item.id).join('|')}`} />;
}
```

### 5. Vá»›i state suy ra Ä‘Æ°á»£c, dÃ¹ng `useMemo`

KhÃ´ng nÃªn:

```tsx
const [wards, setWards] = useState([]);

useEffect(() => {
  setWards(findWards(provinceId));
}, [provinceId]);
```

NÃªn:

```tsx
const wards = useMemo(() => findWards(provinceId), [provinceId, provinces]);
```

### 6. Vá»›i async effect, luÃ´n cÃ³ cleanup

Máº«u nÃªn dÃ¹ng:

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

### 7. Vá»›i timer, luÃ´n clear timer

Máº«u nÃªn dÃ¹ng:

```tsx
useEffect(() => {
  const timer = setTimeout(doSomething, 1200);
  return () => clearTimeout(timer);
}, []);
```

### 8. Cáº©n tháº­n vá»›i mÃ£ hÃ³a tiáº¿ng Viá»‡t

Náº¿u Ä‘ang chá»‰nh file cÃ³ tiáº¿ng Viá»‡t bá»‹ lá»—i nhÆ° `Ãƒ`, `Ã„`, `Ã¡Â»`, `Ã†`, nÃªn sá»­a láº¡i trong vÃ¹ng Ä‘ang cháº¡m.

TrÆ°á»›c khi hoÃ n táº¥t, kiá»ƒm tra nhanh cÃ¡c file vá»«a sá»­a Ä‘á»ƒ trÃ¡nh cÃ²n mojibake.

### 9. KhÃ´ng dÃ¹ng Git khi chÆ°a Ä‘Æ°á»£c yÃªu cáº§u

Theo quy Ä‘á»‹nh cá»§a project, khÃ´ng tá»± Ã½ cháº¡y:

- `git status`
- `git diff`
- `git add`
- `git commit`
- `git push`

Chá»‰ dÃ¹ng Git khi user yÃªu cáº§u trá»±c tiáº¿p.

## Tráº¡ng thÃ¡i hiá»‡n táº¡i

- `npm run lint`: pass.
- React Doctor: khÃ´ng cÃ²n `Bugs errors`.
- CÃ²n optional warnings, chá»§ yáº¿u thuá»™c cÃ¡c nhÃ³m:
  - Accessibility.
  - Maintainability.
  - Performance.
  - Security warnings.

CÃ¡c optional warnings nÃ y nÃªn xá»­ lÃ½ theo tá»«ng nhÃ³m nhá» riÃªng Ä‘á»ƒ trÃ¡nh Ä‘á»•i giao diá»‡n quÃ¡ rá»™ng.
