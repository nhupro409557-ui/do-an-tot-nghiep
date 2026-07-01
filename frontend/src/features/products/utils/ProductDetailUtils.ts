export interface Spec {
  label: string;
  value: string;
  group?: string;
}

export interface ProductMediaItem {
  key: string;
  type: 'video' | 'feature' | 'image';
  url: string;
  label: string;
  color?: string;
  poster?: string;
}

export const colorFallback: Record<string, string> = {
  den: '#111827',
  'đen': '#111827',
  trang: '#f8fafc',
  'trắng': '#f8fafc',
  xanh: '#8fb7c9',
  do: '#d70018',
  'đỏ': '#d70018',
  vang: '#e7c76f',
  'vàng': '#e7c76f',
  titan: '#c8c0b5',
  bac: '#d1d5db',
  'bạc': '#d1d5db',
};

export const specTranslations: Record<string, string> = {
  processor: 'Bộ vi xử lý (CPU)',
  cpu: 'Bộ vi xử lý (CPU)',
  chip: 'Bộ vi xử lý (CPU)',
  ram: 'Bộ nhớ RAM',
  storage: 'Bộ nhớ trong (ROM)',
  rom: 'Bộ nhớ trong (ROM)',
  battery: 'Dung lượng pin',
  batterycapacity: 'Dung lượng pin',
  camera: 'Camera',
  rearcamera: 'Camera sau',
  frontcamera: 'Camera trước',
  screensize: 'Kích thước màn hình',
  screenresolution: 'Độ phân giải màn hình',
  resolution: 'Độ phân giải',
  display: 'Công nghệ màn hình',
  screentype: 'Loại màn hình',
  screentechnology: 'Công nghệ màn hình',
  os: 'Hệ điều hành',
  operatingsystem: 'Hệ điều hành',
  weight: 'Trọng lượng',
  dimensions: 'Kích thước',
  dimension: 'Kích thước',
  warranty: 'Bảo hành',
  origin: 'Xuất xứ',
  material: 'Chất liệu',
  waterproof: 'Chống nước',
  waterresistance: 'Kháng nước',
  bluetooth: 'Bluetooth',
  wifi: 'Wi-Fi',
  network: 'Mạng di động',
  sim: 'Thẻ SIM',
  launchdate: 'Ngày ra mắt',
  releasedate: 'Ngày ra mắt',
  accessories: 'Phụ kiện đi kèm',
  color: 'Màu sắc',
  brand: 'Thương hiệu',
  model: 'Model (Mã máy)',
  gpu: 'Card đồ họa (GPU)',
  graphics: 'Card đồ họa',
  refreshrate: 'Tần số quét',
  chargingspeed: 'Tốc độ sạc',
  charging: 'Công nghệ sạc',
  charger: 'Công suất sạc',
  port: 'Cổng kết nối',
  ports: 'Cổng kết nối',
  jack: 'Jack tai nghe',
  sensors: 'Cảm biến',
  brightness: 'Độ sáng tối đa',
  videorecording: 'Quay video',
  connectivity: 'Kết nối khác',
  wireless: 'Kết nối không dây',
  webcam: 'Webcam',
  audio: 'Âm thanh',
  keyboard: 'Bàn phím',
  casesize: 'Kích thước mặt',
  strap: 'Dây đeo',
  sensor: 'Cảm biến',
  lens: 'Ống kính',
  zoom: 'Zoom',
  stabilization: 'Chống rung',
  fieldofview: 'Góc nhìn',
  sportsmodes: 'Chế độ luyện tập',
  accessorytype: 'Loại phụ kiện',
  compatibility: 'Tương thích',
  power: 'Công suất',
  capacity: 'Dung lượng',
  chargingstandard: 'Chuẩn sạc',
  gps: 'Định vị GPS',
  nfc: 'Kết nối NFC',
  infrared: 'Cổng hồng ngoại',
  fingerprint: 'Cảm biến vân tay',
  rearvideo: 'Quay video camera sau',
  frontvideo: 'Quay video camera trước',
  displaytype: 'Kiểu màn hình',
  displayfeatures: 'Đặc điểm màn hình',
  specialfeatures: 'Tính năng đặc biệt',
  rearcamerafeatures: 'Tính năng camera sau',
  framematerial: 'Chất liệu khung viền',
  backmaterial: 'Chất liệu mặt lưng',
  chargingport: 'Cổng sạc',
  audiocodec: 'Công nghệ âm thanh',
  noisecancellation: 'Khử tiếng ồn',
  releasetime: 'Thời gian ra mắt',
  microphone: 'Microphone',
};

export function formatPrice(value?: number | null) {
  if (!value) return 'Liên hệ';
  return `${value.toLocaleString('vi-VN')}đ`;
}

export function asArray(value: any) {
  return Array.isArray(value) ? value.filter(Boolean) : value ? [value] : [];
}

export function normalizeImages(product: any) {
  const images = product?.images?.length ? product.images : product?.imageUrl ? [product.imageUrl] : [];
  return images.filter(Boolean);
}

export function firstVariantImage(variant: any) {
  return variant?.imageUrl || variant?.image || variant?.images?.[0] || null;
}

export function youtubeVideoId(url?: string | null) {
  const value = String(url || '').trim();
  if (!value) return '';
  try {
    const parsed = new URL(value);
    const host = parsed.hostname.replace(/^www\./, '');
    if (host === 'youtube.com' && parsed.pathname.startsWith('/embed/')) return parsed.pathname.split('/embed/')[1]?.split('/')[0] || '';
    if (host === 'youtu.be') return parsed.pathname.replace(/^\//, '').split('/')[0] || '';
    if (host === 'youtube.com' && parsed.pathname.startsWith('/shorts/')) return parsed.pathname.split('/shorts/')[1]?.split('/')[0] || '';
    if (host === 'youtube.com' && parsed.pathname === '/watch') return parsed.searchParams.get('v') || '';
  } catch {
    return '';
  }
  return '';
}

export function youtubeEmbedUrl(url?: string | null, autoPlay = false) {
  const value = String(url || '').trim();
  if (!value) return '';
  const id = youtubeVideoId(value);
  if (!id) return '';
  const params = new URLSearchParams({
    rel: '0',
    modestbranding: '1',
    playsinline: '1',
  });
  if (autoPlay) params.set('autoplay', '1');
  return `https://www.youtube.com/embed/${id}?${params.toString()}`;
}

export function youtubeThumbnailUrl(url?: string | null) {
  const id = youtubeVideoId(url);
  return id ? `https://img.youtube.com/vi/${id}/hqdefault.jpg` : '';
}

export function variantImageSource(product: any, variant: any) {
  if (!variant) return null;
  if (firstVariantImage(variant) || asArray(variant?.images).length) return variant;
  const color = variant?.colorName || variant?.specs?.color;
  if (!color) return variant;
  return (product?.variants || []).find((item: any) => (
    item !== variant &&
    variantMatchesColor(item, color) &&
    (firstVariantImage(item) || asArray(item?.images).length)
  )) || variant;
}

export function buildOptions(product: any, key: string, fallback: any[] = []) {
  const fromVariants = (product.variants || []).flatMap((variant: any) => {
    const value = variant?.specs?.[key] || (key === 'storage' ? variant?.storage : undefined);
    return value ? [value] : [];
  });
  return Array.from(new Set([...(fallback || []), ...fromVariants]));
}

export function optionLabel(value: any) {
  if (value === null || value === undefined) return '';
  if (typeof value === 'object') {
    return String(value.name || value.label || value.value || value.storage || value.title || '').trim();
  }
  return String(value).trim();
}

export function optionKey(value: any, index: number) {
  return optionLabel(value) || (typeof value === 'object' ? value.id || value.key || value.code || `option-${index}` : `option-${index}`);
}

export function normalizeOptionList(values: any[] = []) {
  const seen = new Set<string>();
  const options: Array<{ raw: any; label: string; key: string }> = [];
  values.forEach((value, index) => {
    const label = optionLabel(value);
    if (!label || seen.has(label)) return;
    seen.add(label);
    options.push({ raw: value, label, key: String(optionKey(value, index)) });
  });
  return options;
}

export function variantSpecValue(variant: any, key: string) {
  const specs = variant?.specs || {};
  return optionLabel(specs[key] ?? variant?.[key]);
}

export function productSpecValue(product: any, key: string) {
  const specs = product?.specs || product?.specifications || {};
  return optionLabel(specs[key]);
}

export function sameOptionValue(left: any, right: any) {
  return optionLabel(left).toLowerCase() === optionLabel(right).toLowerCase();
}

export function variantConfigParts(variant: any) {
  const ram = variantSpecValue(variant, 'ram');
  const storage = variantSpecValue(variant, 'storage');
  const configuration = optionLabel(variant?.configuration || variant?.specs?.configuration);
  const shouldShowConfiguration = configuration && !sameOptionValue(configuration, storage) && !sameOptionValue(configuration, ram);
  const parts: Array<{ key: string; label: string; value: string }> = [];
  if (ram) parts.push({ key: 'ram', label: 'RAM', value: ram });
  if (storage) parts.push({ key: 'storage', label: 'ROM', value: storage });
  if (shouldShowConfiguration) parts.push({ key: 'configuration', label: 'Cấu hình', value: configuration });
  if (!parts.length) {
    const fallback = optionLabel(variant?.name || variant?.sku);
    return fallback ? [{ key: 'variant', label: 'Phiên bản', value: fallback }] : [];
  }
  return parts;
}

export function variantConfigLabel(variant: any) {
  const parts = variantConfigParts(variant);
  const ram = parts.find((part) => part.key === 'ram')?.value;
  const storage = parts.find((part) => part.key === 'storage')?.value;
  const configuration = parts.find((part) => part.key === 'configuration')?.value;
  if (ram && storage) return `${ram} / ${storage}`;
  if (ram) return ram;
  if (storage) return storage;
  if (configuration) return configuration;
  return parts.map((part) => part.value).join(' / ');
}

export function variantMatchesColor(variant: any, colorName: string) {
  if (!colorName) return true;
  const variantColor = variant?.colorName || variant?.specs?.color;
  return !variantColor || String(variantColor).toLowerCase() === String(colorName).toLowerCase();
}

export function variantMatchesConfig(variant: any, configLabel: string) {
  const variantSpecs = variant?.specs || {};
  return (
    variantConfigLabel(variant) === configLabel ||
    variantSpecs.storage === configLabel ||
    variant?.storage === configLabel ||
    variantSpecs.ram === configLabel ||
    variant?.ram === configLabel ||
    variant?.configuration === configLabel ||
    variantSpecs.configuration === configLabel
  );
}

export function optionVariant(option: any) {
  return option?.raw?.raw || option?.raw || option;
}

export function uniqueVariantValues(variants: any[], key: 'ram' | 'storage' | 'configuration') {
  const seen = new Set<string>();
  const values: string[] = [];
  variants.forEach((variant) => {
    let value = '';
    if (key === 'configuration') {
      const configuration = optionLabel(variant?.configuration || variant?.specs?.configuration);
      const ram = variantSpecValue(variant, 'ram');
      const storage = variantSpecValue(variant, 'storage');
      value = !configuration || sameOptionValue(configuration, ram) || sameOptionValue(configuration, storage)
        ? ''
        : configuration;
    } else {
      value = variantSpecValue(variant, key);
    }
    if (!value || seen.has(value)) return;
    seen.add(value);
    values.push(value);
  });
  return values;
}

export function variantMatchesSelectedSpecs(
  variant: any,
  selected: { ram?: string; storage?: string; configuration?: string }
) {
  if (selected.ram && !sameOptionValue(variantSpecValue(variant, 'ram'), selected.ram)) return false;
  if (selected.storage && !sameOptionValue(variantSpecValue(variant, 'storage'), selected.storage)) return false;
  if (selected.configuration) {
    const configuration = optionLabel(variant?.configuration || variant?.specs?.configuration);
    if (!sameOptionValue(configuration, selected.configuration)) return false;
  }
  return true;
}

export function buildConfigurationOptions(product: any) {
  const seen = new Set<string>();
  const fromVariants: Array<{ raw: any; label: string; key: string; details: Array<{ key: string; label: string; value: string }> }> = [];
  (product?.variants || []).forEach((variant: any, index: number) => {
    const details = variantConfigParts(variant);
    const label = variantConfigLabel(variant);
    if (!label || seen.has(label)) return;
    seen.add(label);
    fromVariants.push({
      raw: variant,
      label,
      key: String(variant?.id || variant?.sku || label || `variant-config-${index}`),
      details,
    });
  });
  if (fromVariants.length) return fromVariants;
  return normalizeOptionList(product?.capacities || []).map((item) => ({
    ...item,
    details: [{ key: 'storage', label: 'ROM', value: item.label }],
  }));
}

export const specKeyAliases: Record<string, string> = {
  screenSize: 'screen_size',
  displayType: 'display_type',
  displayFeatures: 'display_features',
  rearVideo: 'rear_video',
  frontVideo: 'front_video',
  rearCameraFeatures: 'rear_camera_features',
  frontCameraFeatures: 'front_camera_features',
  chargingPort: 'charging_port',
  waterResistance: 'water_resistance',
  frameMaterial: 'frame_material',
  backMaterial: 'back_material',
  releaseTime: 'release_time',
  specialFeatures: 'special_features',
  memoryCard: 'memory_card',
  headphoneJack: 'headphone_jack',
  otherUtilities: 'other_utilities',
  utilityTechnology: 'utility_technology',
  tabletModel: 'tablet_model',
  noiseCancellation: 'noise_cancellation',
  caseSize: 'case_size',
  sportsModes: 'sports_modes',
  fieldOfView: 'field_of_view',
};

export const specFallbackLabels: Record<string, { label: string; group: string }> = {
  screen_size: { label: 'Kích thước màn hình', group: 'Màn hình' },
  screen_technology: { label: 'Công nghệ màn hình', group: 'Màn hình' },
  display_type: { label: 'Loại màn hình', group: 'Màn hình' },
  display_features: { label: 'Tính năng màn hình', group: 'Màn hình' },
  resolution: { label: 'Độ phân giải', group: 'Màn hình' },
  refresh_rate: { label: 'Tần số quét', group: 'Màn hình' },
  brightness: { label: 'Độ sáng tối đa', group: 'Màn hình' },
  processor: { label: 'Chip xử lý', group: 'Hiệu năng' },
  cpu: { label: 'CPU', group: 'Hiệu năng' },
  gpu: { label: 'GPU', group: 'Hiệu năng' },
  graphics: { label: 'Card đồ họa', group: 'Hiệu năng' },
  ram: { label: 'RAM', group: 'Hiệu năng' },
  storage: { label: 'Bộ nhớ / lưu trữ', group: 'Hiệu năng' },
  memory_card: { label: 'Thẻ nhớ', group: 'Hiệu năng' },
  os: { label: 'Hệ điều hành', group: 'Hiệu năng' },
  rear_camera: { label: 'Camera sau', group: 'Camera' },
  front_camera: { label: 'Camera trước', group: 'Camera' },
  rear_camera_features: { label: 'Tính năng camera sau', group: 'Camera' },
  rear_video: { label: 'Quay video camera sau', group: 'Camera' },
  front_video: { label: 'Quay video camera trước', group: 'Camera' },
  video_recording: { label: 'Quay video', group: 'Camera' },
  webcam: { label: 'Webcam', group: 'Camera & âm thanh' },
  audio: { label: 'Âm thanh', group: 'Camera & âm thanh' },
  battery: { label: 'Pin', group: 'Pin & sạc' },
  charging: { label: 'Công nghệ sạc', group: 'Pin & sạc' },
  charging_standard: { label: 'Chuẩn sạc', group: 'Pin & sạc' },
  charging_port: { label: 'Cổng sạc', group: 'Pin & sạc' },
  sim: { label: 'SIM', group: 'Kết nối' },
  network: { label: 'Mạng di động', group: 'Kết nối' },
  connectivity: { label: 'Kết nối', group: 'Kết nối' },
  wifi: { label: 'Wi-Fi', group: 'Kết nối' },
  bluetooth: { label: 'Bluetooth', group: 'Kết nối' },
  nfc: { label: 'NFC', group: 'Kết nối' },
  gps: { label: 'Định vị GPS', group: 'Kết nối' },
  infrared: { label: 'Hồng ngoại', group: 'Kết nối' },
  ports: { label: 'Cổng kết nối', group: 'Kết nối' },
  wireless: { label: 'Kết nối không dây', group: 'Kết nối' },
  compatibility: { label: 'Tương thích', group: 'Kết nối' },
  sensors: { label: 'Cảm biến', group: 'Tính năng' },
  fingerprint: { label: 'Bảo mật vân tay', group: 'Tính năng' },
  special_features: { label: 'Tính năng đặc biệt', group: 'Tính năng' },
  utility_technology: { label: 'Công nghệ tiện ích', group: 'Tính năng' },
  water_resistance: { label: 'Kháng nước/bụi', group: 'Độ bền' },
  material: { label: 'Chất liệu', group: 'Thiết kế' },
  frame_material: { label: 'Chất liệu khung', group: 'Thiết kế' },
  back_material: { label: 'Chất liệu mặt lưng', group: 'Thiết kế' },
  dimensions: { label: 'Kích thước', group: 'Thiết kế' },
  weight: { label: 'Trọng lượng', group: 'Thiết kế' },
  color: { label: 'Màu sắc', group: 'Thiết kế' },
  keyboard: { label: 'Bàn phím', group: 'Thiết kế' },
  release_time: { label: 'Thời điểm ra mắt', group: 'Thông tin chung' },
  accessory_type: { label: 'Loại phụ kiện', group: 'Thông tin chung' },
  power: { label: 'Công suất', group: 'Hiệu năng' },
  capacity: { label: 'Dung lượng', group: 'Hiệu năng' },
  noise_cancellation: { label: 'Chống ồn', group: 'Tính năng' },
  microphone: { label: 'Micro', group: 'Tính năng' },
  case_size: { label: 'Kích thước mặt', group: 'Thiết kế' },
  strap: { label: 'Dây đeo', group: 'Thiết kế' },
  sports_modes: { label: 'Chế độ luyện tập', group: 'Tính năng' },
  sensor: { label: 'Hình ảnh', group: 'Hình ảnh' },
  lens: { label: 'Ống kính', group: 'Hình ảnh' },
  zoom: { label: 'Zoom', group: 'Hình ảnh' },
  stabilization: { label: 'Chống rung', group: 'Video' },
  field_of_view: { label: 'Góc nhìn', group: 'Video' },
  tablet_model: { label: 'Dòng máy tính bảng', group: 'Thông tin chung' },
  headphone_jack: { label: 'Cổng tai nghe', group: 'Kết nối' },
  other_utilities: { label: 'Tiện ích khác', group: 'Tính năng' },
};

export function normalizeSpecKey(key: string) {
  return specKeyAliases[key] || key;
}

export function inferSpecGroup(key: string) {
  const normalized = key.toLowerCase();
  if (/(screen|display|màn|man|resolution|refresh|hz|inch)/i.test(normalized)) return 'Màn hình';
  if (/(cpu|chip|processor|ram|storage|rom|gpu|hiệu năng|hieu nang)/i.test(normalized)) return 'Hiệu năng';
  if (/(camera|video|zoom)/i.test(normalized)) return 'Camera';
  if (/(battery|pin|charge|sạc|sac)/i.test(normalized)) return 'Pin & sạc';
  if (/(weight|material|dimension|design|nặng|nang|chất liệu|chat lieu)/i.test(normalized)) return 'Thiết kế';
  if (/(connect|wifi|bluetooth|sim|nfc|network)/i.test(normalized)) return 'Kết nối';
  return 'Thông số khác';
}

export function fallbackSpecMeta(key: string) {
  return specFallbackLabels[key] || {
    label: key
      .replace(/_/g, ' ')
      .replace(/\b\w/g, (char) => char.toUpperCase()),
    group: inferSpecGroup(key),
  };
}

export function formatSpecValue(value: any): string {
  if (value === null || value === undefined || value === '') return '';
  if (Array.isArray(value)) {
    return value.flatMap((item) => {
      const formatted = formatSpecValue(item);
      return formatted ? [formatted] : [];
    }).join(', ');
  }
  if (typeof value === 'object') {
    return Object.entries(value)
      .flatMap(([key, item]) => {
        const formatted = formatSpecValue(item);
        return formatted ? [`${key}: ${formatted}`] : [];
      })
      .join(', ');
  }
  return String(value);
}

export function plainTextFromHtml(value: any) {
  return String(value || '')
    .replace(/<\/(p|div|li|h[1-6]|br)>/gi, '\n')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'")
    .replace(/\n{3,}/g, '\n\n')
    .trim();
}

export function buildProductSpecs(product: any): Spec[] {
  const specFieldMap = new Map(
    (product.specFields || []).map((field: any) => [
      normalizeSpecKey(field.key || field.label),
      {
        label: field.label || field.key,
        group: field.group || inferSpecGroup(normalizeSpecKey(field.key || field.label || '')),
      },
    ]),
  );

  const rawSpecs = product.specs || product.specifications || {};

  const translateLabel = (label: string) => {
    const trimmed = label.trim();
    const keyLower = trimmed.toLowerCase().replace(/_/g, '');
    if (specTranslations[keyLower]) return specTranslations[keyLower];
    return label;
  };

  if (Array.isArray(rawSpecs)) {
    const seenKeys = new Set<string>();
    return rawSpecs
      .flatMap((item: any, index: number) => {
        const key = normalizeSpecKey(item.key || item.label || `spec-${index}`);
        if (seenKeys.has(key)) return [];
        const field = specFieldMap.get(key) as { label?: string; group?: string } | undefined;
        const fallback = fallbackSpecMeta(key);
        const value = formatSpecValue(item.value ?? item.content ?? item.text);
        const originalLabel = item.label || field?.label || fallback.label;
        if (value) seenKeys.add(key);
        return value
          ? [{
              label: translateLabel(originalLabel),
              value,
              group: item.group || field?.group || fallback.group,
            }]
          : [];
      });
  }

  const seenKeys = new Set<string>();
  const specs: Spec[] = [];
  for (const [rawKey, rawValue] of Object.entries(rawSpecs)) {
    const key = normalizeSpecKey(rawKey);
    if (key === '_variantSpecKeys' || seenKeys.has(key)) continue;
    seenKeys.add(key);
    const field = specFieldMap.get(key) as { label?: string; group?: string } | undefined;
    const fallback = fallbackSpecMeta(key);
    const originalLabel = field?.label || fallback.label;
    const value = formatSpecValue(rawValue);
    if (!value) continue;
    specs.push({
      label: translateLabel(originalLabel),
      value,
      group: field?.group || fallback.group,
    });
  }
  return specs;
}

export function productWithActiveVariantSpecs(
  product: any,
  activeVariant: any,
  selected: { ram?: string; storage?: string; configuration?: string } = {}
) {
  if (!activeVariant) return product;
  const variantSpecs = activeVariant.specs || {};
  const ram = selected.ram || variantSpecValue(activeVariant, 'ram') || productSpecValue(product, 'ram');
  const storage = selected.storage || variantSpecValue(activeVariant, 'storage') || productSpecValue(product, 'storage');
  const mergedSpecs = {
    ...(product.specs || product.specifications || {}),
    ...variantSpecs,
    ...(ram ? { ram } : {}),
    ...(storage ? { storage } : {}),
    ...(selected.configuration ? { configuration: selected.configuration } : {}),
  };
  return {
    ...product,
    specs: mergedSpecs,
    specifications: mergedSpecs,
  };
}

export function selectedConfigParts(product: any, activeVariant: any, selected: { ram?: string; storage?: string; configuration?: string; color?: string }) {
  const ram = selected.ram || variantSpecValue(activeVariant, 'ram') || productSpecValue(product, 'ram');
  const storage = selected.storage || variantSpecValue(activeVariant, 'storage') || productSpecValue(product, 'storage');
  const configuration = selected.configuration || optionLabel(activeVariant?.configuration || activeVariant?.specs?.configuration);
  const parts: Array<{ key: string; label: string; value: string }> = [];
  if (ram) parts.push({ key: 'ram', label: 'RAM', value: ram });
  if (storage) parts.push({ key: 'storage', label: 'ROM', value: storage });
  if (configuration && !sameOptionValue(configuration, ram) && !sameOptionValue(configuration, storage)) {
    parts.push({ key: 'configuration', label: 'Cấu hình', value: configuration });
  }
  if (selected.color) parts.push({ key: 'color', label: 'Màu', value: selected.color });
  return parts;
}

export function selectedConfigName(product: any, activeVariant: any, selected: { ram?: string; storage?: string; configuration?: string }) {
  const parts = selectedConfigParts(product, activeVariant, selected).filter((part) => part.key !== 'color');
  const ram = parts.find((part) => part.key === 'ram')?.value;
  const storage = parts.find((part) => part.key === 'storage')?.value;
  const configuration = parts.find((part) => part.key === 'configuration')?.value;
  if (ram && storage) return `${ram} / ${storage}`;
  if (ram) return ram;
  if (storage) return storage;
  if (configuration) return configuration;
  return parts.map((part) => part.value).join(' / ');
}

export function buildMediaItems(product: any, activeVariant?: any): ProductMediaItem[] {
  const items: ProductMediaItem[] = [];
  const seen = new Set<string>();
  const imageVariant = variantImageSource(product, activeVariant);
  const poster = firstVariantImage(imageVariant) || product?.imageUrl || product?.images?.[0] || firstVariantImage(product?.variants?.[0]);

  const add = (item: ProductMediaItem) => {
    if (!item.url || seen.has(`${item.type}:${item.url}`)) return;
    seen.add(`${item.type}:${item.url}`);
    items.push(item);
  };

  if (product?.videoUrl) {
    add({ key: `video-${product.videoUrl}`, type: 'video', url: product.videoUrl, label: 'Video sản phẩm', poster });
  }

  [
    ...asArray(product?.featureImages),
    ...asArray(product?.featuredImages),
    ...asArray(product?.highlightImages),
    ...asArray(product?.featureMedia),
    ...asArray(product?.highlightMedia),
  ].forEach((url: string, index: number) => {
    add({
      key: `feature-${index}-${url}`,
      type: 'feature',
      url,
      label: index === 0 ? 'Tính năng nổi bật' : `Tính năng ${index + 1}`,
    });
  });

  if (imageVariant) {
    const variant = imageVariant;
    const image = firstVariantImage(variant);
    const color = variant?.colorName || variant?.specs?.color;
    if (image) {
      add({
        key: `variant-${variant.id || variant.sku || color || image}`,
        type: 'image',
        url: image,
        label: color ? `Màu ${color}` : 'Ảnh biến thể',
        color,
      });
    }
    asArray(variant?.images).forEach((url: string, index: number) => {
      add({
        key: `variant-gallery-${variant.id || variant.sku || color || index}-${index}-${url}`,
        type: 'image',
        url,
        label: color ? `Màu ${color} ${index + 1}` : `Ảnh biến thể ${index + 1}`,
        color,
      });
    });
  }

  normalizeImages(product).forEach((url: string, index: number) => {
    add({ key: `image-${index}-${url}`, type: 'image', url, label: index === 0 ? 'Ảnh sản phẩm' : `Ảnh ${index + 1}` });
  });

  return items;
}

export function groupSpecs(specs: Spec[]) {
  return specs.reduce<{ title: string; specs: Spec[] }[]>((items, spec) => {
    const title = spec.group?.trim() || 'Thông số khác';
    const existing = items.find((item) => item.title === title);
    if (existing) existing.specs.push(spec);
    else items.push({ title, specs: [spec] });
    return items;
  }, []);
}
