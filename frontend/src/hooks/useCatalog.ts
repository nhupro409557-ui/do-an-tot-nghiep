import { useEffect, useMemo, useRef, useState } from 'react';
import { brandApi } from '../services/brandApi';
import { categoryApi } from '../services/categoryApi';
import { publicApi } from '../services/publicApi';
import {
  CatalogCategory,
  CatalogGroup,
  categoryIconMap,
  defaultCategoryIcon,
} from '../data/categories';

const CHILD_CATEGORY_TITLE = 'Danh m\u1ee5c con';

const normalizeSlug = (value: string) =>
  value
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/\u0111/g, 'd')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');

const unique = <T,>(items: T[]) => Array.from(new Set(items.filter(Boolean)));

const includesAny = (values: unknown[], candidates: string[]) =>
  values.some((value) => value && candidates.includes(String(value)));

const toFeaturedProducts = (products: any[]) =>
  products
    .map((product: any) => ({ id: product.id, name: product.name }))
    .filter((product: any) => product.id && product.name);

type UseCatalogOptions = {
  includeRankedFeatured?: boolean;
};

export function useCatalog(options: UseCatalogOptions = {}) {
  const includeRankedFeaturedRef = useRef(Boolean(options.includeRankedFeatured));
  const [categories, setCategories] = useState<CatalogCategory[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let isActive = true;
    const loadCatalog = async () => {
      setLoading(true);
      const [categoryDocs, brandDocs, productDocs] = await Promise.all([
        categoryApi.listCategories(),
        brandApi.listBrands(),
        publicApi.listProducts(),
      ]);
      const subcategoryDocs = categoryDocs.flatMap((category: any) =>
        (category.children || []).map((child: any) => ({
          ...child,
          categoryId: category.id,
          categorySlug: category.slug,
          groupTitle: CHILD_CATEGORY_TITLE,
        }))
      );

      const sourceCategories = categoryDocs.length > 0
        ? categoryDocs
        : Array.from(new Map(productDocs.map((product: any) => {
            const slug = product.categorySlug || normalizeSlug(product.category || 'san-pham');
            return [slug, { id: slug, slug, name: product.category || slug, icon: slug, order: 99 }];
          })).values());

      const baseCategories = sourceCategories
        .map((category: any) => {
          const slug = category.slug || category.categorySlug || normalizeSlug(category.name || category.id);
          const id = category.id || slug;
          const childCategories = subcategoryDocs.filter((item: any) => item.categoryId === id || item.categorySlug === slug);
          const relatedSlugs = unique([
            id,
            slug,
            ...(category.slugs || []),
            ...childCategories.flatMap((child: any) => [
              child.id,
              child.slug,
              child.categorySlug,
              normalizeSlug(child.name || child.title || ''),
            ]),
          ]);
          const icon = categoryIconMap[category.icon || category.iconKey || slug] || defaultCategoryIcon;

          const grouped = childCategories
            .sort((a: any, b: any) => (a.order || 0) - (b.order || 0))
            .reduce<Record<string, string[]>>((acc, item: any) => {
              const title = item.groupTitle || item.group || item.type || CHILD_CATEGORY_TITLE;
              acc[title] = acc[title] || [];
              acc[title].push(item.name || item.title);
              return acc;
            }, {});

          const categoryProducts = productDocs.filter((product: any) => includesAny([
            product.categorySlug,
            product.categoryId,
            product.subcategorySlug,
            product.subcategoryId,
            product.category,
            normalizeSlug(product.category || ''),
            normalizeSlug(product.categoryName || ''),
            normalizeSlug(product.subcategory || ''),
            normalizeSlug(product.subcategoryName || ''),
          ], relatedSlugs));

          const dbBrands = brandDocs
            .filter((brand: any) => {
              const brandCategoryIds = brand.categoryIds || [];
              return relatedSlugs.includes(brand.categoryId || brand.categorySlug)
                || brandCategoryIds.some((categoryId: string) => relatedSlugs.includes(categoryId));
            })
            .sort((a: any, b: any) => (a.order || 0) - (b.order || 0))
            .map((brand: any) => brand.name || brand.title);

          const productBrands = categoryProducts.map((product: any) => product.brand);
          const fallbackFeaturedProducts = toFeaturedProducts(categoryProducts.slice(0, 10));

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
            featuredProducts: fallbackFeaturedProducts,
            order: category.order || 0,
          };
        });

      const sortedBaseCategories = baseCategories.sort((a: any, b: any) => (a.order || 0) - (b.order || 0));
      if (!isActive) return;
      setCategories(sortedBaseCategories);
      setLoading(false);

      if (!includeRankedFeaturedRef.current) return;

      const rankedCategories = await Promise.all(
        baseCategories.map(async (category: CatalogCategory & { order?: number }) => {
          const rankedProducts = await publicApi
            .listRankings({ period: '7d', criteria: 'trending', category: category.slug, limit: 10 })
            .then(toFeaturedProducts)
            .catch(() => []);

          return {
            ...category,
            featuredProducts: rankedProducts.length > 0 ? rankedProducts : category.featuredProducts,
          };
        })
      );

      if (!isActive) return;
      setCategories(rankedCategories.sort((a: any, b: any) => (a.order || 0) - (b.order || 0)));
    };
    loadCatalog().catch(error => {
      if (!isActive) return;
      console.error(error);
      setCategories([]);
      setLoading(false);
    });
    return () => {
      isActive = false;
    };
  }, []);

  return useMemo(() => ({
    categories,
    loading,
    findCategoryById: (id?: string) => categories.find(category => category.id === id || category.slug === id || category.slugs.includes(id || '')),
  }), [categories, loading]);
}
