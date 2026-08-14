type AssistantProductLinkInput = {
  id?: string;
  slug?: string;
  name?: string;
  isUsed?: boolean;
};

export function buildAssistantProductHref(product: AssistantProductLinkInput) {
  if (product.isUsed) {
    return `/used-products/${product.slug || product.id}`;
  }
  if (product.id) {
    return `/product/${product.id}`;
  }
  return `/search?q=${encodeURIComponent(product.name || product.slug || '')}`;
}
