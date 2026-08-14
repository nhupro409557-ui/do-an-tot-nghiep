import assert from 'node:assert/strict';
import test from 'node:test';

import { formatProductImageGalleryDataForBase, formatProductMediaDataForBase } from './productMedia';

test('chuẩn hóa URL video sản phẩm localhost cho môi trường Vercel', () => {
  const product = formatProductMediaDataForBase({
    imageUrl: 'http://localhost:8000/uploads/products/demo.png',
    videoUrl: 'http://localhost:8000/uploads/products/demo.mp4',
  }, '/api');

  assert.equal(product.imageUrl, '/uploads/products/demo.png');
  assert.equal(product.videoUrl, '/uploads/products/demo.mp4');
});

test('chuẩn hóa toàn bộ URL localhost trong dữ liệu thư viện ảnh phân trang', () => {
  const gallery = formatProductImageGalleryDataForBase({
    items: [{
      mainUrl: 'http://localhost:8000/uploads/products/main.png',
      product: {
        videoUrl: 'http://localhost:8000/uploads/products/demo.mp4',
      },
      images: [{
        url: 'http://127.0.0.1:8000/uploads/products/variant.png',
        product: {
          variants: [{
            imageUrl: 'http://localhost:8000/uploads/products/color.png',
          }],
        },
      }],
    }],
    relatedProducts: [{
      videoUrl: 'http://localhost:8000/uploads/products/related.mp4',
    }],
    totalProducts: 1,
  }, '/api');

  assert.equal(gallery.items[0].mainUrl, '/uploads/products/main.png');
  assert.equal(gallery.items[0].product.videoUrl, '/uploads/products/demo.mp4');
  assert.equal(gallery.items[0].images[0].url, '/uploads/products/variant.png');
  assert.equal(gallery.items[0].images[0].product.variants[0].imageUrl, '/uploads/products/color.png');
  assert.equal(gallery.relatedProducts[0].videoUrl, '/uploads/products/related.mp4');
  assert.equal(gallery.totalProducts, 1);
});
