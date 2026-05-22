import type { CatalogCategory } from '../data/categories';

export type PriceIntent = {
  min?: number;
  max?: number;
};

export type SearchIntent = {
  normalizedQuery: string;
  searchableTerms: string[];
  categoryIds: string[];
  brand?: string;
  price?: PriceIntent;
  useCases: string[];
  preferredSpecs: string[];
};

type RankedProduct = {
  product: any;
  score: number;
};

const CATEGORY_ALIASES: Record<string, string[]> = {
  smartphones: ['dien thoai', 'dienthoai', 'smartphone', 'phone', 'mobile', 'dtdd'],
  laptops: ['laptop', 'may tinh', 'may tinh xach tay', 'notebook'],
  laptop: ['laptop', 'may tinh', 'may tinh xach tay', 'notebook'],
  tablets: ['tablet', 'may tinh bang', 'ipad'],
  audio: ['tai nghe', 'loa', 'am thanh', 'headphone', 'earphone'],
  wearables: ['dong ho', 'smartwatch', 'watch'],
  accessories: ['phu kien', 'sac', 'cap', 'op lung', 'cu sac'],
  monitors: ['man hinh', 'monitor'],
  tv: ['tivi', 'tv'],
};

const BRAND_ALIASES: Record<string, string[]> = {
  Samsung: ['samsung', 'sam sung', 'sansung', 'samsng', 'samssung'],
  Apple: ['apple', 'iphone', 'ipad', 'macbook', 'mac'],
  Xiaomi: ['xiaomi', 'mi', 'redmi', 'poco', 'xiaomy'],
  Oppo: ['oppo'],
  Vivo: ['vivo'],
  Realme: ['realme'],
  Nokia: ['nokia'],
  Asus: ['asus'],
  Lenovo: ['lenovo'],
  Dell: ['dell'],
  HP: ['hp'],
  Acer: ['acer'],
  Sony: ['sony'],
  JBL: ['jbl'],
};

const STOP_WORDS = new Set([
  'tim',
  'kiem',
  'mua',
  'can',
  'tu',
  'van',
  'cho',
  'minh',
  'toi',
  'khach',
  'hang',
  'san',
  'pham',
  'gia',
  'khoang',
  'tam',
  'duoi',
  'tren',
  'tu',
  'den',
  'trieu',
  'tr',
  'vnd',
  'dong',
  'co',
  'the',
  'nao',
  'hoc',
  'sinh',
  'vien',
  'it',
  'code',
  'lap',
  'trinh',
  'muot',
  'do',
  'lai',
  'cu',
  'củ',
]);

const USE_CASE_RULES = [
  {
    id: 'student_it',
    label: 'Sinh viên IT / lập trình',
    aliases: ['sinh vien it', 'sinh vien cong nghe thong tin', 'lap trinh', 'code', 'coder', 'developer'],
    preferredSpecs: ['ram 16gb', 'core i5', 'core i7', 'ryzen 5', 'ryzen 7', 'ssd'],
    categoryHints: ['laptops'],
  },
  {
    id: 'gaming',
    label: 'Gaming',
    aliases: ['gaming', 'choi game', 'game'],
    preferredSpecs: ['rtx', 'gtx', 'ryzen 7', 'core i7', 'ram 16gb', '144hz'],
    categoryHints: ['laptops', 'smartphones'],
  },
  {
    id: 'office',
    label: 'Học tập / văn phòng',
    aliases: ['van phong', 'hoc tap', 'online', 'word', 'excel'],
    preferredSpecs: ['core i5', 'ryzen 5', 'ram 8gb', 'ssd'],
    categoryHints: ['laptops'],
  },
];

export function normalizeSearchText(value: unknown) {
  return String(value || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/đ/g, 'd')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim()
    .replace(/\s+/g, ' ');
}

const compact = (value: string) => value.replace(/\s+/g, '');

const uniq = <T,>(items: T[]) => Array.from(new Set(items.filter(Boolean)));

function parseMoneyValue(raw: string, unit?: string) {
  const value = Number(raw.replace(',', '.'));
  if (!Number.isFinite(value)) return undefined;
  const normalizedUnit = normalizeSearchText(unit || '');
  if (normalizedUnit === 'k' || normalizedUnit === 'nghin') return value * 1000;
  if (normalizedUnit === 'ty') return value * 1000000000;
  if (normalizedUnit === 'tr' || normalizedUnit === 'trieu' || normalizedUnit === 'm' || normalizedUnit === 'cu') return value * 1000000;
  return value < 1000 ? value * 1000000 : value;
}

function parsePriceIntent(query: string): PriceIntent | undefined {
  const normalized = normalizeSearchText(query);
  const pricePattern = '([0-9]+(?:[\\.,][0-9]+)?)\\s*(trieu|tr|m|cu|k|nghin|ty)?';
  const under = normalized.match(new RegExp(`(?:duoi|nho hon|toi da|khong qua|do lai|<=|it hon)\\s*${pricePattern}|${pricePattern}\\s*(?:do lai|tro xuong)`));
  if (under) {
    const max = parseMoneyValue(under[1] || under[3], under[2] || under[4]);
    return max ? { max } : undefined;
  }

  const over = normalized.match(new RegExp(`(?:tren|hon|tu|toi thieu|>=)\\s*${pricePattern}`));
  if (over && !normalized.includes(' den ')) {
    const min = parseMoneyValue(over[1], over[2]);
    return min ? { min } : undefined;
  }

  const between = normalized.match(new RegExp(`${pricePattern}\\s*(?:-|den|toi)\\s*${pricePattern}`));
  if (between) {
    const min = parseMoneyValue(between[1], between[2] || between[4]);
    const max = parseMoneyValue(between[3], between[4] || between[2]);
    if (min && max) return { min: Math.min(min, max), max: Math.max(min, max) };
  }

  return undefined;
}

function detectUseCases(normalizedQuery: string) {
  const matchedRules = USE_CASE_RULES.filter((rule) =>
    rule.aliases.some((alias) => normalizedQuery.includes(normalizeSearchText(alias)))
  );

  return {
    useCases: matchedRules.map((rule) => rule.label),
    preferredSpecs: uniq(matchedRules.flatMap((rule) => rule.preferredSpecs)),
    categoryHints: uniq(matchedRules.flatMap((rule) => rule.categoryHints)),
  };
}

function detectBrand(normalizedQuery: string, availableBrands: string[]) {
  const aliases = { ...BRAND_ALIASES };
  availableBrands.forEach((brand) => {
    aliases[brand] = uniq([...(aliases[brand] || []), brand]);
  });

  return Object.entries(aliases).find(([, names]) =>
    names.some((name) => {
      const normalizedName = normalizeSearchText(name);
      return normalizedQuery.includes(normalizedName) || compact(normalizedQuery).includes(compact(normalizedName));
    })
  )?.[0];
}

function detectCategories(normalizedQuery: string, categories: CatalogCategory[]) {
  return categories
    .filter((category) => {
      const aliases = uniq([
        category.id,
        category.slug,
        category.name,
        ...category.slugs,
        ...(CATEGORY_ALIASES[category.id] || []),
        ...(CATEGORY_ALIASES[category.slug] || []),
      ]).map(normalizeSearchText);

      return aliases.some((alias) => normalizedQuery.includes(alias) || compact(normalizedQuery).includes(compact(alias)));
    })
    .flatMap((category) => category.slugs);
}

export function analyzeProductSearch(
  query: string,
  products: any[],
  categories: CatalogCategory[],
): SearchIntent {
  const normalizedQuery = normalizeSearchText(query);
  const availableBrands = uniq(products.map((product) => product.brand).filter(Boolean));
  const brand = detectBrand(normalizedQuery, availableBrands);
  const useCaseIntent = detectUseCases(normalizedQuery);
  const categoryIds = uniq([...detectCategories(normalizedQuery, categories), ...useCaseIntent.categoryHints]);
  const price = parsePriceIntent(query);

  const ignoredTerms = [
    ...Object.values(CATEGORY_ALIASES).flat(),
    ...categories.flatMap((category) => [category.id, category.slug, category.name, ...category.slugs]),
    ...Object.values(BRAND_ALIASES).flat(),
    ...USE_CASE_RULES.flatMap((rule) => rule.aliases),
    ...(brand ? [brand] : []),
  ].map(normalizeSearchText);

  let freeText = ` ${normalizedQuery} `;
  ignoredTerms
    .filter((term) => term.length > 1)
    .sort((a, b) => b.length - a.length)
    .forEach((term) => {
      freeText = freeText.replace(new RegExp(`\\s${term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\s`, 'g'), ' ');
    });

  const searchableTerms = uniq(
    freeText
      .replace(/(^|\s)[0-9]+(?:[\.,][0-9]+)?\s*(trieu|tr|m|cu|k|nghin|ty)?(?=\s|$)/g, ' ')
      .split(' ')
      .map((term) => term.trim())
      .filter((term) => term.length > 1 && !STOP_WORDS.has(term)),
  );

  return {
    normalizedQuery,
    searchableTerms,
    categoryIds,
    brand,
    price,
    useCases: useCaseIntent.useCases,
    preferredSpecs: useCaseIntent.preferredSpecs,
  };
}

export function intentFromAiParser(
  query: string,
  aiIntent: any,
  fallback: SearchIntent,
): SearchIntent {
  if (!aiIntent || Number(aiIntent.confidence || 0) < 0.35) return fallback;

  return {
    normalizedQuery: normalizeSearchText(query),
    searchableTerms: Array.isArray(aiIntent.searchableTerms)
      ? aiIntent.searchableTerms.map(normalizeSearchText).filter(Boolean)
      : fallback.searchableTerms,
    categoryIds: Array.isArray(aiIntent.categoryIds) && aiIntent.categoryIds.length > 0
      ? aiIntent.categoryIds
      : fallback.categoryIds,
    brand: aiIntent.brand || fallback.brand,
    price: {
      min: aiIntent.minPrice ?? fallback.price?.min,
      max: aiIntent.maxPrice ?? fallback.price?.max,
    },
    useCases: Array.isArray(aiIntent.useCases) && aiIntent.useCases.length > 0
      ? aiIntent.useCases
      : fallback.useCases,
    preferredSpecs: Array.isArray(aiIntent.preferredSpecs) && aiIntent.preferredSpecs.length > 0
      ? aiIntent.preferredSpecs
      : fallback.preferredSpecs,
  };
}

function termScore(term: string, haystack: string) {
  if (!term) return 0;
  if (haystack.includes(term)) return 18;
  if (compact(haystack).includes(compact(term))) return 14;
  if (/\d/.test(term)) return 0;

  const termChars = [...term];
  let index = 0;
  for (const char of haystack) {
    if (char === termChars[index]) index += 1;
    if (index === termChars.length) return Math.max(4, Math.floor(term.length * 0.7));
  }
  return 0;
}

export function searchProductsByIntent(
  products: any[],
  intent: SearchIntent,
  selectedCategory?: CatalogCategory,
  brandFilter = 'all',
  priceRange?: { min: number; max: number },
) {
  const activeCategoryIds = uniq([...(selectedCategory?.slugs || []), ...intent.categoryIds]);

  const ranked = products.reduce<RankedProduct[]>((items, product) => {
    const price = Number(product.price || 0);
    const productCategory = product.categorySlug || product.categoryId || product.category;
    const productBrand = normalizeSearchText(product.brand);
    const haystack = normalizeSearchText([
      product.name,
      product.brand,
      product.category,
      product.categorySlug,
      product.subcategory,
      product.subcategorySlug,
      product.description,
      product.sku,
      JSON.stringify(product.specifications || {}),
    ].filter(Boolean).join(' '));

    const inCategory = activeCategoryIds.length === 0 || activeCategoryIds.includes(productCategory);
    const inBrand = brandFilter === 'all' || productBrand === normalizeSearchText(brandFilter);
    const intentBrandMatches = !intent.brand || productBrand === normalizeSearchText(intent.brand);
    const inRange = !priceRange || (price >= priceRange.min && price < priceRange.max);
    const inIntentPrice = !intent.price
      || (intent.price.min === undefined || price >= intent.price.min)
      && (intent.price.max === undefined || price < intent.price.max);

    if (!inCategory || !inBrand || !intentBrandMatches || !inRange || !inIntentPrice) return items;

    const textScore = intent.searchableTerms.reduce((score, term) => score + termScore(term, haystack), 0);
    const specScore = intent.preferredSpecs.reduce((score, term) => score + termScore(normalizeSearchText(term), haystack), 0);
    const hasTextIntent = intent.searchableTerms.length > 0;
    if (hasTextIntent && textScore === 0) return items;

    const score = textScore
      + (intent.brand ? 25 : 0)
      + (intent.categoryIds.length > 0 ? 20 : 0)
      + (intent.price ? 16 : 0)
      + (intent.useCases.length > 0 ? 12 : 0)
      + specScore
      + Number(product.rating || 0);

    items.push({ product, score });
    return items;
  }, []);

  return ranked
    .sort((a, b) => b.score - a.score)
    .map((item) => item.product);
}

export function formatPriceIntent(price?: PriceIntent) {
  if (!price) return '';
  const format = (value: number) => `${value.toLocaleString('vi-VN')}đ`;
  if (price.min !== undefined && price.max !== undefined) return `${format(price.min)} - ${format(price.max)}`;
  if (price.max !== undefined) return `< ${format(price.max)}`;
  if (price.min !== undefined) return `> ${format(price.min)}`;
  return '';
}

export function getSearchIntentBadges(intent: SearchIntent, categories: CatalogCategory[]) {
  const badges: { label: string; value: string }[] = [];
  const categoryNames = categories
    .filter((category) => intent.categoryIds.some((id) => category.slugs.includes(id) || category.id === id || category.slug === id))
    .map((category) => category.name);

  uniq(categoryNames).forEach((name) => badges.push({ label: 'Danh mục', value: name }));
  if (intent.brand) badges.push({ label: 'Hãng', value: intent.brand });
  const priceLabel = formatPriceIntent(intent.price);
  if (priceLabel) badges.push({ label: 'Giá', value: priceLabel });
  intent.useCases.forEach((useCase) => badges.push({ label: 'Nhu cầu', value: useCase }));

  return badges.slice(0, 5);
}
