import assert from 'node:assert/strict';
import test from 'node:test';

import { formatCompareSpecValue } from './compareSpecValue';


test('định dạng chính sách bảo hành dạng object thành nội dung có thể hiển thị', () => {
  assert.equal(
    formatCompareSpecValue({
      hasWarranty: true,
      warrantyMonths: 12,
      allowOneForOne: true,
      oneForOneDays: 30,
      inheritWarrantyPolicy: false,
    }),
    'Bảo hành 12 tháng · 1 đổi 1 trong 30 ngày',
  );
});

test('giữ nguyên thông số dạng chuỗi và dùng dấu gạch cho giá trị rỗng', () => {
  assert.equal(formatCompareSpecValue('12 GB'), '12 GB');
  assert.equal(formatCompareSpecValue(null), '-');
});
