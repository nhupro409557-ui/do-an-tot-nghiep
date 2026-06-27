import { useMemo } from 'react';
import {
  type AccessoryOfferForm,
  sameId,
  matchesSearch,
} from '../../admin-shell/components/AdminDashboardConfig';

type UseAdminProductOffersParams = {
  productForm: any;
  setProductForm: React.Dispatch<React.SetStateAction<any>>;
  categories: any[];
  products: any[];
  brands: any[];
  attachedServices: any[];
  editingProductId: string | null;
  accessorySearch: string;
  setAccessorySearch: (val: string) => void;
  accessoryCategoryFilter: string;
  accessoryBrandFilter: string;
  attachedServiceTypeFilter: string;
  attachedServiceGroupFilter: string;
  attachedServiceSearch: string;
};

export function useAdminProductOffers({
  productForm,
  setProductForm,
  categories,
  products,
  brands,
  attachedServices,
  editingProductId,
  accessorySearch,
  setAccessorySearch,
  accessoryCategoryFilter,
  accessoryBrandFilter,
  attachedServiceTypeFilter,
  attachedServiceGroupFilter,
  attachedServiceSearch,
}: UseAdminProductOffersParams) {
  const accessoryProductChoices = useMemo(() => {
    const selectedCategory = categories.find((category) => sameId(category.id, accessoryCategoryFilter));
    const childCategoryIds = new Set(categories.filter((category) => sameId(category.parentId, accessoryCategoryFilter)).map((category) => String(category.id)));
    return products
      .filter((product) => !sameId(product.id, editingProductId))
      .filter((product) => !productForm.accessoryOffers.some((offer: any) => sameId(offer.productId, product.id)))
      .filter((product) => {
        if (!accessoryCategoryFilter) return true;
        return sameId(product.categoryId, accessoryCategoryFilter)
          || sameId(product.subcategoryId, accessoryCategoryFilter)
          || childCategoryIds.has(String(product.categoryId || ''))
          || childCategoryIds.has(String(product.subcategoryId || ''))
          || (!!selectedCategory && [product.category, product.categoryName, product.subcategoryName].some((value) => String(value || '').toLowerCase() === String(selectedCategory.name || selectedCategory.code || selectedCategory.slug || '').toLowerCase()));
      })
      .filter((product) => !accessoryBrandFilter || sameId(product.brandId, accessoryBrandFilter) || sameId(product.brand, brands.find((brand) => sameId(brand.id, accessoryBrandFilter))?.name))
      .filter((product) => matchesSearch(product, accessorySearch, ['name', 'sku', 'brand', 'brandName', 'categoryName', 'category']))
      .slice(0, 50);
  }, [accessoryBrandFilter, accessoryCategoryFilter, accessorySearch, brands, categories, editingProductId, productForm.accessoryOffers, products]);

  const productAttachedServiceChoices = useMemo(() => {
    const keyword = attachedServiceSearch.trim().toLowerCase();
    return attachedServices
      .filter((service) => service.isActive !== false)
      .filter((service) => !productForm.attachedServices.some((item: any) => item.serviceId === service.id))
      .filter((service) => !attachedServiceTypeFilter || service.serviceType === attachedServiceTypeFilter)
      .filter((service) => !attachedServiceGroupFilter || service.attributeGroup === attachedServiceGroupFilter)
      .filter((service) => {
        if (!keyword) return true;
        return [service.name, service.code, service.attributeGroup, service.serviceType]
          .some((value) => String(value || '').toLowerCase().includes(keyword));
      });
  }, [attachedServiceGroupFilter, attachedServiceSearch, attachedServiceTypeFilter, attachedServices, productForm.attachedServices]);

  const serviceGroupOptions = useMemo(() => {
    const groups = new Set<string>();
    attachedServices.forEach((service) => {
      const group = String(service.attributeGroup || '').trim();
      if (group) groups.add(group);
    });
    return Array.from(groups).sort((left, right) => left.localeCompare(right));
  }, [attachedServices]);

  function addAccessoryOffer(item: any) {
    setProductForm((prev: any) => ({
      ...prev,
      accessoryOffers: [
        ...prev.accessoryOffers,
        {
          productId: item.id,
          productName: item.name || '',
          productSku: item.sku || '',
          imageUrl: item.imageUrl || '',
          discountType: 'PERCENT',
          discountValue: 25,
          maxQuantity: 1,
          originalPrice: Number(item.price || 0),
          salePrice: Number(item.discountPrice || item.price || 0),
          normalDiscountPrice: Number(item.discountPrice || item.price || 0),
          price: Math.round(Number(item.discountPrice || item.price || 0) * 0.75), // mặc định giảm 25%
        },
      ],
    }));
    setAccessorySearch('');
  }

  function patchAccessoryOffer(productId: string, patch: Partial<AccessoryOfferForm>) {
    setProductForm((prev: any) => ({
      ...prev,
      accessoryOffers: prev.accessoryOffers.map((item: any) => (item.productId === productId ? { ...item, ...patch } : item)),
    }));
  }

  function removeAccessoryOffer(productId: string) {
    setProductForm((prev: any) => ({
      ...prev,
      accessoryOffers: prev.accessoryOffers.filter((item: any) => item.productId !== productId),
    }));
  }

  function addAttachedService(service: any) {
    const group = String(service.attributeGroup || '').trim();
    if (group && productForm.attachedServices.some((item: any) => item.serviceType === service.serviceType && item.attributeGroup === group)) {
      window.alert('Mỗi nhóm thuộc tính của dịch vụ chỉ được chọn một lựa chọn. Hãy bỏ lựa chọn cũ trước khi chọn lựa chọn mới.');
      return;
    }
    setProductForm((prev: any) => prev.attachedServices.some((item: any) => item.serviceId === service.id)
      ? prev
      : {
        ...prev,
        attachedServices: [
          ...prev.attachedServices,
          {
            serviceId: service.id,
            name: service.name || '',
            code: service.code || '',
            serviceType: service.serviceType || 'SUPPORT_SERVICE',
            attributeGroup: service.attributeGroup || '',
            durationMonths: Number(service.durationMonths || 0),
            priceMode: service.priceMode || 'FIXED',
            fixedPrice: Number(service.fixedPrice || 0),
            percentValue: Number(service.percentValue || 0),
          },
        ],
      });
  }

  function removeAttachedService(serviceId: string) {
    setProductForm((prev: any) => ({ ...prev, attachedServices: prev.attachedServices.filter((item: any) => item.serviceId !== serviceId) }));
  }

  return {
    accessoryProductChoices,
    productAttachedServiceChoices,
    serviceGroupOptions,
    addAccessoryOffer,
    patchAccessoryOffer,
    removeAccessoryOffer,
    addAttachedService,
    removeAttachedService,
  };
}
