import { useEffect, useMemo, useState } from 'react';
import { apiDb } from '../services/apiDb';
import {
  CatalogCategory,
  CatalogGroup,
  categoryIconMap,
  defaultCategoryIcon,
} from '../data/categories';

const normalizeSlug = (value: string) =>
  value
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');

const unique = <T,>(items: T[]) => Array.from(new Set(items.filter(Boolean)));

export function useCatalog() {
  const [categories, setCategories] = useState<CatalogCategory[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadCatalog = async () => {
      setLoading(true);
      const [categoryDocs, brandDocs, productDocs] = await Promise.all([
        apiDb.listCategories(),
        apiDb.listBrands(),
        apiDb.listProducts(),
      ]);
      const subcategoryDocs = categoryDocs.flatMap((category: any) =>
        (category.children || []).map((child: any) => ({ ...child, categoryId: category.id, categorySlug: category.slug, groupTitle: 'Danh mục con' }))
      );

    const sourceCategories = categoryDocs.length > 0
      ? categoryDocs
      : Array.from(new Map(productDocs.map((product: any) => {
          const slug = product.categorySlug || normalizeSlug(product.category || 'san-pham');
          return [slug, { id: slug, slug, name: product.category || slug, icon: slug, order: 99 }];
        })).values());

    const nextCategories = sourceCategories
      .map((category: any) => {
        const slug = category.slug || category.categorySlug || normalizeSlug(category.name || category.id);
        const id = category.id || slug;
        const relatedSlugs = unique([id, slug, ...(category.slugs || [])]);
        const icon = categoryIconMap[category.icon || category.iconKey || slug] || defaultCategoryIcon;

        const grouped = subcategoryDocs
          .filter((item: any) => relatedSlugs.includes(item.categoryId || item.categorySlug))
          .sort((a: any, b: any) => (a.order || 0) - (b.order || 0))
          .reduce<Record<string, string[]>>((acc, item: any) => {
            const title = item.groupTitle || item.group || item.type || 'Danh mục con';
            acc[title] = acc[title] || [];
            acc[title].push(item.name || item.title);
            return acc;
          }, {});

        const categoryProducts = productDocs.filter((product: any) =>
          relatedSlugs.includes(product.categorySlug || product.categoryId || normalizeSlug(product.category || ''))
        );

        const dbBrands = brandDocs
          .filter((brand: any) => {
            const brandCategoryIds = brand.categoryIds || [];
            return !brand.categoryId && brandCategoryIds.length === 0
              || relatedSlugs.includes(brand.categoryId || brand.categorySlug)
              || brandCategoryIds.some((categoryId: string) => relatedSlugs.includes(categoryId));
          })
          .sort((a: any, b: any) => (a.order || 0) - (b.order || 0))
          .map((brand: any) => brand.name || brand.title);

        const productBrands = categoryProducts.map((product: any) => product.brand);
        const featuredProducts = categoryProducts
          .slice(0, 10)
          .map((product: any) => ({ id: product.id, name: product.name }))
          .filter((product: any) => product.id && product.name);

        const groups: CatalogGroup[] = Object.entries(grouped).map(([title, items]) => ({
          title,
          items: unique(items),
        }));

        return {
          id,
          name: category.name || category.title || id,
          slug,
          slugs: relatedSlugs,
          icon,
          brands: unique([...dbBrands, ...productBrands]),
          groups,
          featuredProducts,
          order: category.order || 0,
        };
      })
      .sort((a: any, b: any) => (a.order || 0) - (b.order || 0));

    setCategories(nextCategories);
    setLoading(false);
    };
    loadCatalog().catch(error => {
      console.error(error);
      setCategories([]);
      setLoading(false);
    });
  }, []);

  return useMemo(() => ({
    categories,
    loading,
    findCategoryById: (id?: string) => categories.find(category => category.id === id || category.slug === id || category.slugs.includes(id || '')),
  }), [categories, loading]);
}
