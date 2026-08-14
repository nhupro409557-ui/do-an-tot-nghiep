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
