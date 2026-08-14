type WarrantySpec = {
  hasWarranty?: boolean;
  warrantyMonths?: number;
  allowOneForOne?: boolean;
  oneForOneDays?: number;
  inheritWarrantyPolicy?: boolean;
};

function formatWarrantySpec(value: WarrantySpec): string | null {
  const isWarrantySpec = [
    'hasWarranty',
    'warrantyMonths',
    'allowOneForOne',
    'oneForOneDays',
    'inheritWarrantyPolicy',
  ].some((key) => key in value);

  if (!isWarrantySpec) return null;
  if (value.inheritWarrantyPolicy) return 'Theo chính sách bảo hành chung';
  if (value.hasWarranty === false) return 'Không bảo hành';

  const details = [
    value.warrantyMonths ? `Bảo hành ${value.warrantyMonths} tháng` : value.hasWarranty ? 'Có bảo hành' : null,
    value.allowOneForOne && value.oneForOneDays ? `1 đổi 1 trong ${value.oneForOneDays} ngày` : null,
  ].filter(Boolean);

  return details.join(' · ') || '-';
}

export function formatCompareSpecValue(value: unknown): string {
  if (value == null || value === '') return '-';
  if (typeof value === 'string' || typeof value === 'number') return String(value);
  if (typeof value === 'boolean') return value ? 'Có' : 'Không';
  if (Array.isArray(value)) return value.map(formatCompareSpecValue).join(', ');

  if (typeof value === 'object') {
    const record = value as Record<string, unknown>;
    const warranty = formatWarrantySpec(record);
    if (warranty) return warranty;

    return Object.entries(record)
      .map(([key, item]) => `${key}: ${formatCompareSpecValue(item)}`)
      .join(' · ') || '-';
  }

  return '-';
}
