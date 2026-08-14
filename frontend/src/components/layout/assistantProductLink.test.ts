import assert from 'node:assert/strict';
import test from 'node:test';

import { buildAssistantProductHref } from './assistantProductLink';


test('sản phẩm mới mở đúng trang chi tiết theo id', () => {
  assert.equal(
    buildAssistantProductHref({
      id: '1efdf734-8628-45fc-b953-b3ea4ca29bad',
      slug: 'iphone-17-pro',
      isUsed: false,
    }),
    '/product/1efdf734-8628-45fc-b953-b3ea4ca29bad',
  );
});

test('hàng cũ ưu tiên slug để mở trang chi tiết hàng cũ', () => {
  assert.equal(
    buildAssistantProductHref({
      id: 'used-product-id',
      slug: 'iphone-15-pro-max-cu',
      isUsed: true,
    }),
    '/used-products/iphone-15-pro-max-cu',
  );
});
