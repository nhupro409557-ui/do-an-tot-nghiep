import assert from 'node:assert/strict';
import test from 'node:test';

import { formatVideoMediaData, formatVideoMediaDataForBase } from './contentMedia';


test('chuẩn hóa URL video và thumbnail localhost cho môi trường Vercel', () => {
  const video = formatVideoMediaDataForBase({
    videoUrl: 'http://localhost:8000/uploads/content/demo.mp4',
    thumbnailUrl: 'http://127.0.0.1:8000/uploads/content/demo.png',
    coverUrl: 'https://cdn.example.com/cover.png',
  }, '/api');

  assert.equal(video.videoUrl, '/uploads/content/demo.mp4');
  assert.equal(video.thumbnailUrl, '/uploads/content/demo.png');
  assert.equal(video.coverUrl, 'https://cdn.example.com/cover.png');
});

test('có thể dùng trực tiếp bộ chuẩn hóa làm callback của Array.map', () => {
  const videos = [{ videoUrl: 'https://cdn.example.com/demo.mp4' }].map(formatVideoMediaData);

  assert.equal(videos[0].videoUrl, 'https://cdn.example.com/demo.mp4');
});
