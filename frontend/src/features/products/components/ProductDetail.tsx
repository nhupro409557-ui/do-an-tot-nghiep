import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  Check,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  Gift,
  Heart,
  ListChecks,
  MessageCircle,
  Minus,
  PackageCheck,
  PlayCircle,
  Plus,
  PlusCircle,
  RotateCcw,
  ShieldCheck,
  ShoppingCart,
  Star,
  Truck,
  X,
  Zap,
} from 'lucide-react';
import { ProductReviews } from './ProductReviews';
import { ProductQuestions } from './ProductQuestions';
import { SuggestedProducts } from './SuggestedProducts';
import { useCart } from '../../../context/CartContext';
import { useAuth } from '../../../context/AuthContext';
import { publicApi } from '../../../services/publicApi';
import { ProductGallery } from './ProductGallery';
import { ProductSpecsTable, SpecsModal } from './ProductSpecsTable';
import { ProductPurchaseActions } from './ProductPurchaseActions';
import { ImageWithFallback } from '../../../components/ui/ImageWithFallback';
import { AttachedServices, BundleOffers, FeatureHighlights, type ProductDetailProps, accessoryBasePrice, accessoryOfferPrice, getAttachedServicePriceNumeric, productPolicyHighlights } from './ProductDetailSections';
import {
  buildMediaItems,
  buildProductSpecs,
  plainTextFromHtml,
  productWithActiveVariantSpecs,
  selectedConfigName,
  selectedConfigParts,
  uniqueVariantValues,
  normalizeOptionList,
  variantMatchesColor,
  variantSpecValue,
  optionLabel,
  variantConfigLabel,
  firstVariantImage,
  formatPrice,
  asArray,
  normalizeImages,
  variantMatchesConfig,
  sameOptionValue,
  variantMatchesSelectedSpecs,
  buildConfigurationOptions,
  youtubeEmbedUrl,
} from '../utils/ProductDetailUtils';

function initialProductSelection(product: any, requestedVariantId: string) {
  const requestedVariant = (product?.variants || []).find((variant: any) => String(variant.id) === requestedVariantId);
  const initialColor = requestedVariant?.colorName || optionLabel(product?.colors?.[0]);
  const initialVariants = (product?.variants || []).filter((variant: any) => variantMatchesColor(variant, initialColor));
  const initialVariant = requestedVariant || initialVariants[0];
  const initialRam = variantSpecValue(initialVariant, 'ram');
  const initialStorage = variantSpecValue(initialVariant, 'storage');
  const initialConfiguration = optionLabel(initialVariant?.configuration || initialVariant?.specs?.configuration);
  return {
    capacity: variantConfigLabel(initialVariant),
    color: initialColor,
    configuration: initialConfiguration
      && !sameOptionValue(initialConfiguration, initialRam)
      && !sameOptionValue(initialConfiguration, initialStorage)
      ? initialConfiguration
      : '',
    ram: initialRam,
    storage: initialStorage,
  };
}

const ProductDetailContent = ({
  product: externalProduct,
  initialVariantId,
}: ProductDetailProps & { initialVariantId: string }) => {
  const { addToCart } = useCart();
  const product = useMemo(() => {
    if (!externalProduct) return null;
    return {
      ...externalProduct,
      images: normalizeImages(externalProduct),
      salePrice: externalProduct.salePrice || externalProduct.discountPrice || externalProduct.price || 0,
      originalPrice: externalProduct.originalPrice || externalProduct.price || null,
      capacities: buildConfigurationOptions(externalProduct),
      colors: externalProduct.colors || [],
      promotions: externalProduct.promotions || [],
    };
  }, [externalProduct]);
  const initialSelection = useMemo(
    () => initialProductSelection(product, initialVariantId),
    [initialVariantId, product],
  );
  const [selectedMediaIndex, setSelectedMediaIndex] = useState(0);
  const [selectedCapacity, setSelectedCapacity] = useState(initialSelection.capacity);
  const [selectedRam, setSelectedRam] = useState(initialSelection.ram);
  const [selectedStorage, setSelectedStorage] = useState(initialSelection.storage);
  const [selectedConfiguration, setSelectedConfiguration] = useState(initialSelection.configuration);
  const [selectedColor, setSelectedColor] = useState(initialSelection.color);
  const [quantity, setQuantity] = useState(1);
  const [liked, setLiked] = useState(false);
  const { user } = useAuth();
  const [addedToCart, setAddedToCart] = useState(false);
  const [selectedServices, setSelectedServices] = useState<any[]>([]);
  const [selectedAccessories, setSelectedAccessories] = useState<any[]>([]);

  const handleServiceChange = (service: any, checked: boolean) => {
    setSelectedServices((prev) => {
      if (checked) {
        return [...prev, service];
      }
      return prev.filter(s => (s.serviceId || s.code) !== (service.serviceId || service.code));
    });
  };

  const handleAccessoryChange = (offer: any, checked: boolean) => {
    setSelectedAccessories((prev) => {
      if (checked) {
        return [...prev, offer];
      }
      return prev.filter(acc => acc.productId !== offer.productId);
    });
  };
  const [showSpecsModal, setShowSpecsModal] = useState(false);
  const [activeSpecGroup, setActiveSpecGroup] = useState('all');
  const [showMediaViewer, setShowMediaViewer] = useState(false);
  const [isDescCollapsed, setIsDescCollapsed] = useState(true);
  const [showStickyPurchaseBar, setShowStickyPurchaseBar] = useState(false);
  const purchaseActionsRef = useRef<HTMLDivElement | null>(null);
  const addedToCartTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const features = useMemo(() => {
    if (!product) return [];
    const lines = plainTextFromHtml(product.description)
      .split(/[.\n]/)
      .map((line) => line.trim())
      .filter((line) => line.length > 24);

    const fromSpecs = [
      product.specs?.processor && `Hiệu năng mạnh mẽ với ${product.specs.processor}`,
      product.specs?.screenSize && `Màn hình ${product.specs.screenSize} hiển thị sắc nét`,
      product.specs?.camera && `Camera ${product.specs.camera} hỗ trợ chụp ảnh linh hoạt`,
      product.specs?.battery && `Dung lượng pin ${product.specs.battery} đáp ứng nhu cầu cả ngày`,
    ].filter(Boolean) as string[];

    return (lines.length ? lines : fromSpecs).slice(0, 5);
  }, [product]);

  const activeVariant = useMemo(() => product?.variants?.find((variant: any) => {
    if (!variantMatchesColor(variant, selectedColor)) return false;
    return variantMatchesSelectedSpecs(variant, {
      ram: selectedRam,
      storage: selectedStorage,
      configuration: selectedConfiguration,
    });
  }), [product, selectedColor, selectedRam, selectedStorage, selectedConfiguration]);

  const mediaItems = useMemo(() => (product ? buildMediaItems(product, activeVariant) : []), [product, activeVariant]);

  useEffect(() => {
    const productId = product?.id;
    if (!productId || !user) return;
    let isActive = true;
    publicApi.listFavorites().then(favs => {
      if (!isActive) return;
      setLiked(favs.some((f: any) => f.id === productId));
    }).catch(console.error);
    return () => {
      isActive = false;
    };
  }, [product?.id, user]);

  const selectedMedia = mediaItems[selectedMediaIndex];
  const selectedImage = selectedMedia?.type !== 'video'
    ? selectedMedia?.url || null
    : mediaItems.find((item) => item.type !== 'video')?.url || product?.images?.[0] || null;

  const closeMediaViewer = () => {
    setShowMediaViewer(false);
  };

  const viewMedia = (index: number) => {
    if (!mediaItems.length) return;
    const boundedIndex = (index + mediaItems.length) % mediaItems.length;
    setSelectedMediaIndex(boundedIndex);
  };

  useEffect(() => {
    if (!showMediaViewer) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setShowMediaViewer(false);
      if (event.key === 'ArrowLeft') {
        setSelectedMediaIndex((current) => (current - 1 + mediaItems.length) % mediaItems.length);
      }
      if (event.key === 'ArrowRight') {
        setSelectedMediaIndex((current) => (current + 1) % mediaItems.length);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [showMediaViewer, mediaItems.length]);

  useLayoutEffect(() => {
    return () => {
      if (addedToCartTimerRef.current) clearTimeout(addedToCartTimerRef.current);
    };
  }, []);

  useEffect(() => {
    let animationFrame = 0;
    const syncPurchaseActionsVisibility = () => {
      window.cancelAnimationFrame(animationFrame);
      animationFrame = window.requestAnimationFrame(() => {
        const target = purchaseActionsRef.current;
        if (!target) return;
        setShowStickyPurchaseBar(window.scrollY >= target.offsetTop + 180);
      });
    };

    syncPurchaseActionsVisibility();
    window.addEventListener('scroll', syncPurchaseActionsVisibility, { passive: true });
    window.addEventListener('resize', syncPurchaseActionsVisibility);
    document.addEventListener('scroll', syncPurchaseActionsVisibility, { passive: true, capture: true });
    const syncTimer = window.setInterval(syncPurchaseActionsVisibility, 250);
    return () => {
      window.clearInterval(syncTimer);
      window.cancelAnimationFrame(animationFrame);
      window.removeEventListener('scroll', syncPurchaseActionsVisibility);
      window.removeEventListener('resize', syncPurchaseActionsVisibility);
      document.removeEventListener('scroll', syncPurchaseActionsVisibility, { capture: true });
    };
  });

  if (!product) {
    return <div className="mx-auto max-w-7xl px-4 py-16 text-center text-gray-500">Không tìm thấy dữ liệu sản phẩm.</div>;
  }

  const activeFlashSale = activeVariant?.flashSale || product.flashSale || null;
  const isDiscontinued = product.status === 'DISCONTINUED';
  const policyHighlights = productPolicyHighlights(product);
  const displayPrice = activeVariant?.salePrice || activeVariant?.price || product.salePrice;
  const displayOriginalPrice = activeVariant?.originalPrice || activeVariant?.price || product.originalPrice;
  const discount =
    displayOriginalPrice && displayOriginalPrice > displayPrice
      ? Math.round(((displayOriginalPrice - displayPrice) / displayOriginalPrice) * 100)
      : 0;
  const monthlyPrice = displayPrice ? Math.ceil(displayPrice / 12 / 1000) * 1000 : 0;

  const selectedSpecs = {
    ram: selectedRam,
    storage: selectedStorage,
    configuration: selectedConfiguration,
  };
  const displayProduct = productWithActiveVariantSpecs(product, activeVariant, selectedSpecs);
  const headerConfigName = selectedConfigName(product, activeVariant, selectedSpecs);
  const displayProductName = headerConfigName ? `${product.name} - ${headerConfigName}` : product.name;
  const specs = buildProductSpecs(displayProduct);
  const cleanDescription = plainTextFromHtml(product.description);
  const variantsForColor = (product.variants || []).filter((variant: any) => variantMatchesColor(variant, selectedColor));
  const ramOptions = uniqueVariantValues(variantsForColor, 'ram');
  const storageOptions = uniqueVariantValues(
    variantsForColor.filter((variant: any) => !selectedRam || sameOptionValue(variantSpecValue(variant, 'ram'), selectedRam)),
    'storage'
  );
  const configurationOptions = uniqueVariantValues(
    variantsForColor.filter((variant: any) => {
      if (selectedRam && !sameOptionValue(variantSpecValue(variant, 'ram'), selectedRam)) return false;
      if (selectedStorage && !sameOptionValue(variantSpecValue(variant, 'storage'), selectedStorage)) return false;
      return true;
    }),
    'configuration'
  );
  const colorOptions = normalizeOptionList(product.colors);

  const selectColor = (colorName: string) => {
    setSelectedMediaIndex(0);
    setSelectedColor(colorName);
    const variants = (product.variants || []).filter((variant: any) => variantMatchesColor(variant, colorName));
    const stillAvailable = activeVariant && variantMatchesColor(activeVariant, colorName);
    const nextVariant = stillAvailable ? activeVariant : variants[0];
    const nextRam = variantSpecValue(nextVariant, 'ram');
    const nextStorage = variantSpecValue(nextVariant, 'storage');
    const nextConfiguration = optionLabel(nextVariant?.configuration || nextVariant?.specs?.configuration);
    setSelectedRam(nextRam);
    setSelectedStorage(nextStorage);
    setSelectedConfiguration(
      nextConfiguration &&
      !sameOptionValue(nextConfiguration, nextRam) &&
      !sameOptionValue(nextConfiguration, nextStorage)
        ? nextConfiguration
        : ''
    );
    setSelectedCapacity(variantConfigLabel(nextVariant));
  };

  const selectRam = (ram: string) => {
    setSelectedMediaIndex(0);
    const matchingVariants = variantsForColor.filter((variant: any) => sameOptionValue(variantSpecValue(variant, 'ram'), ram));
    const keepCurrentStorage = matchingVariants.some((variant: any) => sameOptionValue(variantSpecValue(variant, 'storage'), selectedStorage));
    const nextVariant = matchingVariants.find((variant: any) => keepCurrentStorage && sameOptionValue(variantSpecValue(variant, 'storage'), selectedStorage)) || matchingVariants[0];
    setSelectedRam(ram);
    setSelectedStorage(keepCurrentStorage ? selectedStorage : variantSpecValue(nextVariant, 'storage'));
    const configuration = optionLabel(nextVariant?.configuration || nextVariant?.specs?.configuration);
    setSelectedConfiguration(configuration && !sameOptionValue(configuration, ram) && !sameOptionValue(configuration, variantSpecValue(nextVariant, 'storage')) ? configuration : '');
    setSelectedCapacity(variantConfigLabel(nextVariant));
  };

  const selectStorage = (storage: string) => {
    setSelectedMediaIndex(0);
    const matchingVariants = variantsForColor.filter((variant: any) => {
      if (selectedRam && !sameOptionValue(variantSpecValue(variant, 'ram'), selectedRam)) return false;
      return sameOptionValue(variantSpecValue(variant, 'storage'), storage);
    });
    const nextVariant = matchingVariants[0];
    setSelectedStorage(storage);
    const configuration = optionLabel(nextVariant?.configuration || nextVariant?.specs?.configuration);
    setSelectedConfiguration(configuration && !sameOptionValue(configuration, selectedRam) && !sameOptionValue(configuration, storage) ? configuration : '');
    setSelectedCapacity(variantConfigLabel(nextVariant));
  };

  const selectConfiguration = (configuration: string) => {
    setSelectedMediaIndex(0);
    setSelectedConfiguration(configuration);
    const nextVariant = variantsForColor.find((variant: any) => {
      if (selectedRam && !sameOptionValue(variantSpecValue(variant, 'ram'), selectedRam)) return false;
      if (selectedStorage && !sameOptionValue(variantSpecValue(variant, 'storage'), selectedStorage)) return false;
      return sameOptionValue(optionLabel(variant?.configuration || variant?.specs?.configuration), configuration);
    });
    setSelectedCapacity(variantConfigLabel(nextVariant));
  };

  const openMediaViewer = (index: number) => {
    viewMedia(index);
    setShowMediaViewer(true);
  };

  const handleAddToCart = () => {
    if (isDiscontinued) return;
    const cartImage = selectedImage || product.imageUrl || product.images?.[0] || firstVariantImage(activeVariant) || firstVariantImage(product.variants?.[0]) || '';

    // Thêm sản phẩm chính kèm dịch vụ đi kèm
    addToCart({
      productId: product.id,
      name: [displayProductName, selectedColor].filter(Boolean).join(' - '),
      price: displayPrice,
      imageUrl: cartImage,
      quantity,
      originalPrice: displayOriginalPrice,
      attachedServices: selectedServices.map(s => ({
        serviceId: s.serviceId || s.id || s.code,
        code: s.code,
        name: s.name,
        price: getAttachedServicePriceNumeric(s, displayPrice)
      }))
    });

    // Thêm các phụ kiện mua kèm đã chọn
    selectedAccessories.forEach((acc) => {
      const offerPrice = accessoryOfferPrice(acc);
      const basePrice = accessoryBasePrice(acc);
      addToCart({
        productId: acc.productId,
        name: acc.productName,
        price: offerPrice, // Giá bán kèm ưu đãi
        imageUrl: acc.imageUrl || product.imageUrl || product.images?.[0] || '',
        quantity: quantity, // Số lượng tương ứng với sản phẩm chính
        originalPrice: basePrice, // Giá gốc hoặc giá đang bán trước ưu đãi mua kèm
        isAccessory: true,
        parentProductId: product.id
      });
    });

    setAddedToCart(true);
    setSelectedServices([]);
    setSelectedAccessories([]);

    if (addedToCartTimerRef.current) clearTimeout(addedToCartTimerRef.current);
    addedToCartTimerRef.current = setTimeout(() => {
      setAddedToCart(false);
      addedToCartTimerRef.current = null;
    }, 1800);
  };

  const handleBuyNow = () => {
    if (isDiscontinued) return;
    handleAddToCart();
    window.location.href = '/checkout';
  };

  const fallbackImage = product.imageUrl || product.images?.[0] || firstVariantImage(product.variants?.[0]) || undefined;
  const rating = Number(product.rating || 0);
  const reviewCount = Number(product.reviewCount || 0);
  const soldCount = Number(product.soldCount || 0);
  const brandSlug = optionLabel(product.brand).toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/đ/g, 'd').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-$/g, '');
  const breadcrumbs = [
    product.category && { label: product.category, href: `/products/${product.categorySlug || ''}` },
    product.subcategory && { label: product.subcategory, href: `/products/${product.subcategorySlug || product.categorySlug || ''}` },
    product.brand && { label: product.brand, href: brandSlug ? `/brands/${brandSlug}` : `/products?brand=${encodeURIComponent(product.brand)}` },
  ].filter(Boolean) as Array<{ label: string; href: string }>;

  return (
    <div className="bg-white pb-24 md:pb-8">
      <div className="mx-auto max-w-[1200px] px-3 py-3 sm:px-4">
        <nav className="mb-3 flex items-center gap-1 overflow-hidden text-sm text-gray-500">
          <Link to="/" className="shrink-0 hover:text-primary">Trang chủ</Link>
          <ChevronRight className="h-4 w-4 shrink-0 text-gray-300" />
          {breadcrumbs.map((item) => (
            <React.Fragment key={`${item.label}-${item.href}`}>
              <Link to={item.href} className="shrink-0 hover:text-primary">
                {item.label}
              </Link>
              <ChevronRight className="h-4 w-4 shrink-0 text-gray-300" />
            </React.Fragment>
          ))}
          <span className="truncate font-medium text-gray-700">{product.name}</span>
        </nav>

        <div className="mb-4 border-b border-gray-150 pb-3">
          <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <h1 className="text-xl font-bold leading-snug text-gray-900 md:text-2xl">{displayProductName}</h1>
              {isDiscontinued && (
                <div className="mt-2 inline-flex rounded-md border border-slate-200 bg-slate-100 px-2.5 py-1 text-xs font-black uppercase text-slate-700">
                  Ngừng kinh doanh
                </div>
              )}
              <div className="mt-1 flex flex-wrap items-center gap-3 text-sm text-gray-500">
                <span className="flex items-center gap-1 font-semibold text-amber-500">
                  {[...Array(5)].map((_, index) => (
                    <Star key={index} className={`h-4 w-4 ${index < Math.round(rating) ? 'fill-amber-400' : 'text-gray-300'}`} />
                  ))}
                  <span>{rating > 0 ? rating.toFixed(1) : 'Chưa có đánh giá'}</span>
                </span>
                {reviewCount > 0 && <span>{reviewCount.toLocaleString('vi-VN')} đánh giá</span>}
                {soldCount > 0 && (
                  <>
                    <span className="hidden text-gray-300 sm:inline">|</span>
                    <span>Đã bán {soldCount.toLocaleString('vi-VN')}</span>
                  </>
                )}
              </div>
            </div>

            <div className="flex flex-wrap gap-2 text-sm">
              {!isDiscontinued && <button
                type="button"
                onClick={() => {
                  if (!user) return alert('Vui lòng đăng nhập để lưu sản phẩm yêu thích.');
                  const nextLiked = !liked;
                  setLiked(nextLiked);
                  publicApi.toggleFavorite(product.id).catch(() => setLiked(!nextLiked));
                }}
                className={`flex h-10 items-center gap-1.5 rounded-lg border px-3 font-bold transition-all duration-200 ${liked ? 'border-red-200 bg-red-50 text-primary' : 'border-gray-200 text-primary hover:border-red-200 hover:bg-red-50/30'}`}
              >
                <Heart className={`h-5 w-5 ${liked ? 'fill-primary' : ''}`} />
                <span>Yêu thích</span>
              </button>}
              <a href="#product-questions" className="flex h-10 items-center gap-1.5 rounded-lg border border-gray-200 px-3 font-bold text-primary hover:border-red-200 hover:bg-red-50/30 transition-all duration-200">
                <MessageCircle className="h-5 w-5" />
                <span>Hỏi đáp</span>
              </a>
              <button
                type="button"
                onClick={() => {
                  setActiveSpecGroup('all');
                  setShowSpecsModal(true);
                }}
                className="flex h-10 items-center gap-1.5 rounded-lg border border-gray-200 px-3 font-bold text-primary hover:border-red-200 hover:bg-red-50/30 transition-all duration-200"
              >
                <ListChecks className="h-5 w-5" />
                <span>Thông số</span>
              </button>
              {!isDiscontinued && <Link to={`/compare?product=${product.id}`} className="flex h-10 items-center gap-1.5 rounded-lg border border-gray-200 px-3 font-bold text-primary hover:border-red-200 hover:bg-red-50/30 transition-all duration-200">
                <PlusCircle className="h-5 w-5" />
                <span>So sánh</span>
              </Link>}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-1 items-start gap-6 lg:grid-cols-[500px_1fr] lg:gap-8">
          <aside className="lg:sticky lg:top-16 lg:self-start w-full space-y-3">
            <ProductGallery
              key={activeVariant?.id || product.id}
              product={product}
              mediaItems={mediaItems}
              selectedMediaIndex={selectedMediaIndex}
              setSelectedMediaIndex={setSelectedMediaIndex}
              discount={isDiscontinued ? 0 : discount}
              fallbackImage={fallbackImage}
              openMediaViewer={openMediaViewer}
            />

            <div className="grid grid-cols-2 gap-2.5 w-full">
              {policyHighlights.map(([Icon, title, desc]: any) => (
                <div key={title} className="flex gap-2.5 rounded-xl p-3 bg-gray-50/60 border border-gray-100/50 transition-all hover:bg-gray-100/40">
                  <Icon className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
                  <div>
                    <div className="font-bold text-gray-800 leading-snug">{title}</div>
                    <div className="text-[10px] sm:text-[11px] leading-normal text-gray-500 mt-0.5">{desc}</div>
                  </div>
                </div>
              ))}
            </div>

            {(features.length > 0 || cleanDescription) && (
              <section className="rounded-2xl border border-gray-200 bg-white p-4 space-y-4">
                {features.length > 0 && (
                  <div>
                    <h2 className="mb-3 text-base font-bold text-gray-900">Đặc điểm nổi bật</h2>
                    <div className="space-y-2">
                      {features.map((feature, index) => (
                        <div key={feature} className="flex gap-3 text-sm leading-relaxed text-gray-700 bg-gray-50/40 p-2.5 rounded-xl border border-gray-100/50">
                          <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-red-50 text-xs font-bold text-primary">
                            {index + 1}
                          </span>
                          <span>{feature}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {features.length > 0 && cleanDescription && <hr className="border-gray-100" />}

                {cleanDescription && (
                  <div>
                    <h2 className="mb-3 text-base font-bold text-gray-900">Thông tin chi tiết</h2>
                    <div className="relative">
                      <div
                        className={`overflow-hidden transition-all duration-300 ${
                          isDescCollapsed ? 'max-h-[350px]' : 'max-h-none'
                        }`}
                      >
                        <p className="whitespace-pre-line text-sm leading-7 text-gray-700">{cleanDescription}</p>
                      </div>

                      {isDescCollapsed && (
                        <div className="absolute bottom-0 left-0 right-0 h-28 bg-gradient-to-t from-white via-white/80 to-transparent pointer-events-none" />
                      )}
                    </div>

                    <div className="mt-4 flex justify-center">
                      <button
                        type="button"
                        onClick={() => setIsDescCollapsed(!isDescCollapsed)}
                        className="flex items-center gap-1.5 rounded-xl border border-primary bg-white px-6 py-2.5 text-sm font-bold text-primary shadow-sm transition-all hover:bg-red-50 hover:shadow cursor-pointer"
                      >
                        <span>{isDescCollapsed ? 'Xem thêm nội dung' : 'Thu gọn nội dung'}</span>
                        <ChevronDown className={`h-4 w-4 transition-transform duration-300 ${!isDescCollapsed ? 'rotate-180' : ''}`} />
                      </button>
                    </div>
                  </div>
                )}
              </section>
            )}
          </aside>

          <main className="space-y-4 md:space-y-5">
            <div ref={purchaseActionsRef} data-product-purchase-actions>
              <ProductPurchaseActions
                product={product}
                activeVariant={activeVariant}
                displayPrice={displayPrice}
                displayOriginalPrice={displayOriginalPrice}
                monthlyPrice={monthlyPrice}
                discount={discount}
                activeFlashSale={activeFlashSale}
                ramOptions={ramOptions}
                storageOptions={storageOptions}
                configurationOptions={configurationOptions}
                colorOptions={colorOptions}
                selectedRam={selectedRam}
                selectedStorage={selectedStorage}
                selectedConfiguration={selectedConfiguration}
                selectedColor={selectedColor}
                selectRam={selectRam}
                selectStorage={selectStorage}
                selectConfiguration={selectConfiguration}
                selectColor={selectColor}
                quantity={quantity}
                setQuantity={setQuantity}
                handleBuyNow={handleBuyNow}
                handleAddToCart={handleAddToCart}
                addedToCart={addedToCart}
                variantsForColor={variantsForColor}
                selectedCapacity={selectedCapacity}
                isDiscontinued={isDiscontinued}
              />
            </div>

            <ProductSpecsTable specs={specs} />
            {!isDiscontinued && (
              <BundleOffers
                offers={product.salesConfig?.accessoryOffers}
                price={displayPrice}
                selectedAccessories={selectedAccessories}
                onChange={handleAccessoryChange}
              />
            )}
            {!isDiscontinued && (
              <AttachedServices
                services={product.salesConfig?.attachedServices}
                price={displayPrice}
                selectedServices={selectedServices}
                onChange={handleServiceChange}
              />
            )}

          </main>
        </div>
        <SuggestedProducts currentProductId={product.id} category={product.categorySlug} />
        <ProductQuestions productId={product.id} />
        <div id="product-reviews">
          <ProductReviews productId={product.id} />
        </div>
      </div>

      {!isDiscontinued && showStickyPurchaseBar && (
        <div className="fixed bottom-[88px] left-0 right-0 z-[49] px-3 md:px-4 lg:bottom-4" data-sticky-purchase-bar>
          <div className="mx-auto flex max-w-[1210px] items-center gap-3 rounded-2xl border border-gray-200 bg-white/95 p-3 shadow-[0_8px_32px_rgba(15,23,42,0.16)] backdrop-blur">
            <div className="flex min-w-0 flex-1 items-center gap-3">
              <div className="hidden h-16 w-16 shrink-0 items-center justify-center rounded-xl border border-gray-100 bg-white p-1 shadow-sm sm:flex">
                <ImageWithFallback
                  src={selectedImage || product.images?.[0]}
                  fallbackSrc={fallbackImage}
                  alt={product.name}
                  className="h-full w-full object-contain"
                />
              </div>
              <div className="min-w-0">
                <div className="line-clamp-2 text-sm font-bold leading-snug text-gray-900 md:text-lg">{displayProductName}</div>
              </div>
            </div>
            <div className="hidden shrink-0 text-right sm:block">
              <div className="text-lg font-black text-primary md:text-2xl">{formatPrice(displayPrice)}</div>
              {displayOriginalPrice && displayOriginalPrice > displayPrice && (
                <div className="text-sm font-semibold text-gray-400 line-through md:text-base">{formatPrice(displayOriginalPrice)}</div>
              )}
            </div>
            <button type="button" className="hidden h-14 shrink-0 items-center justify-center rounded-xl border border-blue-500 bg-white px-5 text-base font-bold text-blue-600 transition-colors hover:bg-blue-50 md:flex">
              Trả góp 0%
            </button>
            <button
              type="button"
              onClick={handleBuyNow}
              className="flex h-12 shrink-0 items-center justify-center rounded-xl bg-primary px-5 text-center text-base font-extrabold text-white shadow-sm transition-colors hover:bg-red-700 md:h-14 md:px-8 md:text-lg"
            >
              Mua Ngay
            </button>
            <button
              type="button"
              onClick={handleAddToCart}
              className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border-2 transition-all md:h-14 md:w-14 ${
                addedToCart ? 'border-green-500 bg-green-50 text-green-600' : 'border-primary bg-white text-primary hover:bg-red-50'
              }`}
              aria-label="Thêm vào giỏ hàng"
              title="Thêm vào giỏ hàng"
            >
              {addedToCart ? <Check className="h-5 w-5" /> : <ShoppingCart className="h-5 w-5" />}
            </button>
          </div>
        </div>
      )}

      {showSpecsModal && (
        <SpecsModal
          specs={specs}
          activeGroup={activeSpecGroup}
          onSelectGroup={setActiveSpecGroup}
          onClose={() => setShowSpecsModal(false)}
        />
      )}

      {showMediaViewer && mediaItems[selectedMediaIndex] && (
        <div className="fixed inset-0 z-[100] flex flex-col bg-black/95">
          <div className="flex h-14 items-center justify-between px-4 text-white">
            <div className="text-sm font-semibold">
              {selectedMediaIndex + 1} / {mediaItems.length}
            </div>
            <button
              type="button"
              onClick={closeMediaViewer}
              className="flex h-10 w-10 items-center justify-center rounded-full bg-white/10 hover:bg-white/20"
              aria-label="Đóng xem ảnh"
            >
              <X className="h-6 w-6" />
            </button>
          </div>

          <div className="relative flex flex-1 items-center justify-center overflow-hidden px-4 pb-5">
            {mediaItems.length > 1 && (
              <button
                type="button"
                onClick={() => viewMedia(selectedMediaIndex - 1)}
                className="absolute left-4 z-10 flex h-11 w-11 items-center justify-center rounded-full bg-white/10 text-white hover:bg-white/20"
                aria-label="Ảnh trước"
              >
                <ChevronLeft className="h-7 w-7" />
              </button>
            )}

            {mediaItems[selectedMediaIndex].type === 'video' ? (
              youtubeEmbedUrl(mediaItems[selectedMediaIndex].url) ? (
                <iframe
                  src={youtubeEmbedUrl(mediaItems[selectedMediaIndex].url, true)}
                  title={mediaItems[selectedMediaIndex].label}
                  className="aspect-video w-full max-w-5xl rounded-xl bg-black"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
                  sandbox="allow-scripts allow-presentation allow-popups"
                  allowFullScreen
                />
              ) : (
                <video
                  aria-label="Video sản phẩm"
                  src={mediaItems[selectedMediaIndex].url}
                  poster={mediaItems[selectedMediaIndex].poster}
                  controls
                  autoPlay
                  className="max-h-[82vh] max-w-full bg-black object-contain"
                >
                  <track kind="captions" />
                </video>
              )
            ) : (
              <ImageWithFallback
                src={mediaItems[selectedMediaIndex].url}
                fallbackSrc={fallbackImage}
                alt={product.name}
                className="max-h-[82vh] max-w-full object-contain"
              />
            )}

            {mediaItems.length > 1 && (
              <button
                type="button"
                onClick={() => viewMedia(selectedMediaIndex + 1)}
                className="absolute right-4 z-10 flex h-11 w-11 items-center justify-center rounded-full bg-white/10 text-white hover:bg-white/20"
                aria-label="Ảnh sau"
              >
                <ChevronRight className="h-7 w-7" />
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

const ProductDetail = ({ product }: ProductDetailProps) => {
  const [searchParams] = useSearchParams();
  const requestedVariantId = searchParams.get('variant') || '';
  return <ProductDetailContent key={`${product?.id || 'empty'}:${requestedVariantId}`} product={product} initialVariantId={requestedVariantId} />;
};

export default ProductDetail;
