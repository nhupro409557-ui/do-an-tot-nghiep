import assert from 'node:assert/strict';
import test from 'node:test';

import { resolveApiBaseUrl } from './apiBaseUrl';


test('Vercel dùng API cùng origin để refresh cookie không bị chặn', () => {
  assert.equal(
    resolveApiBaseUrl(
      'https://do-an-tot-nghiep-8k43.vercel.app/api',
      'do-an-tot-nghiep-rho.vercel.app',
    ),
    '/api',
  );
});

test('local và hosting khác vẫn dùng backend đã cấu hình', () => {
  assert.equal(
    resolveApiBaseUrl('http://localhost:8000/api', 'localhost'),
    'http://localhost:8000/api',
  );
  assert.equal(
    resolveApiBaseUrl('https://api.example.com/api', 'shop.example.com'),
    'https://api.example.com/api',
  );
});
