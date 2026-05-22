import {
  BadgePercent,
  Camera,
  Headphones,
  Home,
  Laptop,
  LucideIcon,
  Mic2,
  Monitor,
  Newspaper,
  PackageOpen,
  RefreshCw,
  Smartphone,
  Tv,
  Watch,
} from 'lucide-react';

export type CatalogGroup = {
  title: string;
  items: string[];
};

export type CatalogCategory = {
  id: string;
  name: string;
  slug: string;
  slugs: string[];
  icon: LucideIcon;
  brands: string[];
  groups: CatalogGroup[];
  featuredProducts: { id: string; name: string }[];
};

export const categoryIconMap: Record<string, LucideIcon> = {
  phone: Smartphone,
  smartphone: Smartphone,
  mobile: Smartphone,
  laptop: Laptop,
  pc: Laptop,
  audio: Mic2,
  mic: Mic2,
  headphone: Headphones,
  accessory: Headphones,
  watch: Watch,
  camera: Camera,
  home: Home,
  smarthome: Home,
  monitor: Monitor,
  tv: Tv,
  refresh: RefreshCw,
  used: PackageOpen,
  sale: BadgePercent,
  news: Newspaper,
};

export const defaultCategoryIcon = Smartphone;

export const priceRanges = [
  { id: 'under2', label: 'Dưới 2 triệu', min: 0, max: 2000000 },
  { id: '2to4', label: 'Từ 2 - 4 triệu', min: 2000000, max: 4000000 },
  { id: '4to7', label: 'Từ 4 - 7 triệu', min: 4000000, max: 7000000 },
  { id: '7to13', label: 'Từ 7 - 13 triệu', min: 7000000, max: 13000000 },
  { id: '13to20', label: 'Từ 13 - 20 triệu', min: 13000000, max: 20000000 },
  { id: 'over20', label: 'Trên 20 triệu', min: 20000000, max: Infinity },
];
