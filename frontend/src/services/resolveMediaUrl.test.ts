import assert from 'node:assert/strict';
import test from 'node:test';

import { resolveMediaUrl } from './resolveMediaUrl';


test('đổi URL upload localhost sang domain backend đang cấu hình', () => {
  assert.equal(
    resolveMediaUrl(
      'http://localhost:8000/uploads/content/banner.png',
      'https://api.example.com/api',
    ),
    'https://api.example.com/uploads/content/banner.png',
  );
});

test('giữ nguyên URL CDN và đường dẫn ảnh tĩnh của frontend', () => {
  assert.equal(resolveMediaUrl('https://cdn.example.com/banner.png', 'https://api.example.com/api'), 'https://cdn.example.com/banner.png');
  assert.equal(resolveMediaUrl('/images/banner.png', 'https://api.example.com/api'), '/images/banner.png');
});

test('ghép storage key trong database với đường dẫn media của backend', () => {
  assert.equal(
    resolveMediaUrl('products/123/photo.webp', 'https://api.example.com/api'),
    'https://api.example.com/media/products/123/photo.webp',
  );
  assert.equal(
    resolveMediaUrl('content/banners/home.webp', 'https://api.example.com/api'),
    'https://api.example.com/media/content/banners/home.webp',
  );
});

test('không dựng URL cho storage key có thành phần đi ngược thư mục', () => {
  assert.equal(
    resolveMediaUrl('products/../secret.txt', 'https://api.example.com/api'),
    '',
  );
});
