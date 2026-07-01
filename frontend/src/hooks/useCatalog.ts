import { useEffect, useMemo, useRef, useState } from 'react';
import { brandApi } from '../services/brandApi';
import { categoryApi } from '../services/categoryApi';
import { publicApi } from '../services/publicApi';
import {
  CatalogBrand,
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

const unique = <T,>(items: T[]) => {
  const values = new Set<T>();
  for (const item of items) {
    if (item) values.add(item);
  }
  return Array.from(values);
};

const uniqueBrands = (items: CatalogBrand[]) => {
  const values = new Map<string, CatalogBrand>();
  for (const item of items) {
    const name = item.name?.trim();
    if (!name) continue;
    const key = name.toLowerCase();
    const current = values.get(key);
    if (!current || (!current.logoUrl && item.logoUrl)) {
      values.set(key, { ...item, name });
    }
  }
  return Array.from(values.values());
};

const includesAny = (values: unknown[], candidates: Set<string>) =>
  values.some((value) => value && candidates.has(String(value)));

const toFeaturedProducts = (products: any[]) => {
  const featuredProducts: { id: string; name: string }[] = [];
  for (const product of products) {
    if (product.id && product.name) featuredProducts.push({ id: product.id, name: product.name });
  }
  return featuredProducts;
};

function collectSubcategories(categoryDocs: any[]) {
  const subcategories: any[] = [];
  for (const category of categoryDocs) {
    for (const child of category.children || []) {
      subcategories.push({
        ...child,
        categoryId: category.id,
        categorySlug: category.slug,
        groupTitle: CHILD_CATEGORY_TITLE,
      });
    }
  }
  return subcategories;
}

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
      const subcategoryDocs = collectSubcategories(categoryDocs);

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
          const relatedSlugSet = new Set(relatedSlugs);
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
          ], relatedSlugSet));

          const matchedBrands = [];
          for (const brand of brandDocs) {
            const brandCategoryIds = brand.categoryIds || [];
            if (
              relatedSlugSet.has(brand.categoryId || brand.categorySlug)
              || brandCategoryIds.some((categoryId: string) => relatedSlugSet.has(categoryId))
            ) {
              matchedBrands.push(brand);
            }
          }
          matchedBrands.sort((a: any, b: any) => (a.order || 0) - (b.order || 0));
          const dbBrands = matchedBrands.map((brand: any) => ({
            name: brand.name || brand.title,
            logoUrl: brand.logoUrl,
            logoAltText: brand.logoAltText,
          }));

          const productBrands = categoryProducts.map((product: any) => ({ name: product.brand }));
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
            brands: uniqueBrands([...dbBrands, ...productBrands]),
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
