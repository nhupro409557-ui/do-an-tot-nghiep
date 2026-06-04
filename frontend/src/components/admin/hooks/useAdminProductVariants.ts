import { type VariantForm, buildVariantSku, emptyVariant } from '../AdminDashboardConfig';

type UseAdminProductVariantsParams = {
  productForm: any;
  setProductForm: React.Dispatch<React.SetStateAction<any>>;
  variantFields: any[];
  activeVariantFields: any[];
};

export function useAdminProductVariants({
  productForm,
  setProductForm,
  variantFields,
  activeVariantFields,
}: UseAdminProductVariantsParams) {
  const colorOptionName = 'Màu sắc';

  function normalizeOptionKey(value: string) {
    return String(value || '')
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .trim()
      .toLowerCase();
  }

  function activeVariantOptionName(key: string) {
    return activeVariantFields.find((field) => field.key === key)?.label || key;
  }

  function variantSpecValue(variant: any, key: string, label?: string) {
    const sources = [variant.specs || {}, variant.attributes || {}];
    const normalizedKey = normalizeOptionKey(key);
    const normalizedLabel = normalizeOptionKey(label || '');
    for (const source of sources) {
      if (source[key]) return source[key];
      if (label && source[label]) return source[label];
      const match = Object.entries(source).find(([sourceKey]) => {
        const normalizedSourceKey = normalizeOptionKey(sourceKey);
        return normalizedSourceKey === normalizedKey || Boolean(normalizedLabel && normalizedSourceKey === normalizedLabel);
      });
      if (match) return match[1];
    }
    return '';
  }

  function resolveVariantSpecKey(value: string) {
    const normalizedValue = normalizeOptionKey(value);
    const matchedField = variantFields.find((field) => {
      return normalizeOptionKey(field.key) === normalizedValue || normalizeOptionKey(field.label || '') === normalizedValue;
    });
    if (matchedField) return matchedField.key;
    if (['bo nho trong', 'bo nho', 'dung luong', 'rom', 'storage'].includes(normalizedValue)) return 'storage';
    if (['ram', 'bo nho ram'].includes(normalizedValue)) return 'ram';
    return value;
  }

  function buildVariantAttributes(variant: VariantForm): Record<string, string> {
    const attributes: Record<string, string> = {};
    const colorValue = String(
      variant.colorName ||
      variantSpecValue(variant, 'color', colorOptionName) ||
      variantSpecValue(variant, 'mau sac', colorOptionName)
    ).trim();
    if (colorValue) {
      attributes[colorOptionName] = colorValue;
    }
    productForm.variantSpecKeys.forEach((key: string) => {
      const optionName = activeVariantOptionName(key);
      const value = String(variantSpecValue(variant, key, optionName)).trim();
      if (value) {
        attributes[optionName] = value;
      }
    });
    return attributes;
  }

  function deriveOptionsFromVariants(variants: VariantForm[]) {
    const optionValues = new Map<string, string[]>();
    variants.forEach((variant) => {
      Object.entries(buildVariantAttributes(variant)).forEach(([name, value]) => {
        if (!optionValues.has(name)) optionValues.set(name, []);
        const values = optionValues.get(name)!;
        if (!values.includes(value)) values.push(value);
      });
    });
    return Array.from(optionValues.entries()).map(([name, values]) => ({ name, values }));
  }

  function addVariant() {
    setProductForm((prev: any) => ({
      ...prev,
      variants: [
        ...prev.variants,
        {
          ...emptyVariant,
          price: prev.price,
          salePrice: prev.discountPrice,
          stockQuantity: Number(prev.stock || 0),
          isDefault: prev.variants.length === 0,
        },
      ],
    }));
  }

  function patchVariant(index: number, patch: Partial<VariantForm>) {
    setProductForm((prev: any) => ({
      ...prev,
      variants: prev.variants.map((item: any, i: number) => (i === index ? { ...item, ...patch } : item)),
    }));
  }

  function toggleVariantSpecField(key: string, checked: boolean) {
    setProductForm((prev: any) => ({
      ...prev,
      variantSpecKeys: checked ? [...new Set([...prev.variantSpecKeys, key])] : prev.variantSpecKeys.filter((item: any) => item !== key),
      variants: checked
        ? prev.variants
        : prev.variants.map((variant: any) => {
            const specs = { ...variant.specs };
            delete specs[key];
            return { ...variant, specs };
          }),
    }));
  }

  return {
    colorOptionName,
    normalizeOptionKey,
    activeVariantOptionName,
    variantSpecValue,
    resolveVariantSpecKey,
    buildVariantAttributes,
    deriveOptionsFromVariants,
    addVariant,
    patchVariant,
    toggleVariantSpecField,
  };
}
