const systemActorLabels: Record<string, string> = {
  'system-expirer': 'Tác vụ tự động hết hạn',
  'system-checkout': 'Hệ thống checkout',
  'sepay-ipn': 'Webhook SePay',
  'momo-ipn': 'Webhook MoMo',
  'zalopay-ipn': 'Webhook ZaloPay',
  'vnpay-ipn': 'Webhook VNPay',
  system: 'Hệ thống',
};

export function adminActorLabel(actor: any) {
  const rawId = String(actor.changedBy || actor.actorId || actor.userId || '').trim();
  const name = actor.changedByName || actor.actorName || actor.changedByEmail || actor.actorEmail || actor.email;
  const role = actor.changedByRole || actor.actorRole;
  const normalizedId = rawId.toLowerCase();
  const automaticName = (() => {
    if (!normalizedId) return 'Hệ thống';
    if (normalizedId.endsWith('-ipn')) return `Webhook ${rawId.slice(0, -4).toUpperCase()}`;
    if (normalizedId.endsWith('-webhook')) return `Webhook ${rawId.slice(0, -8)}`;
    if (normalizedId.endsWith('-worker')) return `Tác vụ ${rawId.slice(0, -7)}`;
    if (normalizedId.startsWith('system-')) return `Hệ thống ${rawId.slice(7).replaceAll('-', ' ')}`;
    return rawId;
  })();
  const roleLabels: Record<string, string> = {
    SUPER_ADMIN: 'Super Admin',
    STAFF_ADMIN: 'Nhân viên quản trị',
    CUSTOMER: 'Khách hàng',
  };
  return {
    name: name || systemActorLabels[normalizedId] || automaticName,
    role: role ? (roleLabels[String(role).toUpperCase()] || role) : null,
    email: actor.changedByEmail || actor.actorEmail || actor.email || null,
    isSystem: !name && (!rawId || normalizedId.includes('system') || normalizedId.includes('ipn') || normalizedId.includes('worker') || normalizedId.includes('webhook')),
  };
}
