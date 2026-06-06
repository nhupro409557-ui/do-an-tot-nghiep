import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ChevronDown, ChevronUp, ShieldPlus, Star, Droplets, Clock,
  AlertTriangle, BadgeCheck, ArrowRight, Package, RefreshCw, Archive,
} from 'lucide-react';

function Table({ headers, rows, highlight }: { headers: string[]; rows: string[][]; highlight?: number }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50">
          <tr>
            {headers.map((h) => (
              <th key={h} className="px-4 py-2.5 text-left text-xs font-bold uppercase tracking-wide text-slate-600">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {rows.map((row, i) => (
            <tr key={i} className={`transition-colors hover:bg-slate-50/60 ${highlight === i ? 'bg-indigo-50/60' : ''}`}>
              {row.map((cell, j) => (
                <td
                  key={j}
                  className={`px-4 py-2.5 leading-relaxed text-slate-600 ${j === 0 ? 'font-semibold text-slate-700' : ''}`}
                >
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Note({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
      <div className="leading-relaxed">{children}</div>
    </div>
  );
}

function BulletList({ items }: { items: string[] }) {
  return (
    <ul className="space-y-1.5 text-sm text-slate-600">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2 leading-relaxed">
          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-indigo-500" />
          {item}
        </li>
      ))}
    </ul>
  );
}

function PricingNote({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex items-start gap-2 rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-3 text-sm text-indigo-800">
      <BadgeCheck className="mt-0.5 h-4 w-4 shrink-0 text-indigo-600" />
      <div className="leading-relaxed">{children}</div>
    </div>
  );
}

interface Section {
  id: string;
  number: string;
  title: string;
  icon: React.ReactNode;
  content: React.ReactNode;
}

export default function ExtendedWarrantyPage() {
  const [expanded, setExpanded] = useState<string | null>('ew-1');
  const toggle = (id: string) => setExpanded((p) => (p === id ? null : id));

  const pkgCards = [
    {
      icon: <Star className="h-5 w-5 text-indigo-600" />,
      name: '1 đổi 1 VIP',
      targets: 'Điện thoại, máy tính bảng, laptop, đồng hồ thông minh, tai nghe cao cấp',
      benefit: 'Đổi sản phẩm tương đương khi phát sinh lỗi phần cứng nhà sản xuất',
      color: 'border-indigo-200 bg-indigo-50',
      badge: 'bg-indigo-600',
    },
    {
      icon: <Droplets className="h-5 w-5 text-cyan-600" />,
      name: 'Rơi vỡ – Rơi nước',
      targets: 'Điện thoại, máy tính bảng',
      benefit: 'Hỗ trợ tới 90% chi phí sửa chữa khi rơi vỡ, vào nước hoặc tác động ngoại lực',
      color: 'border-cyan-200 bg-cyan-50',
      badge: 'bg-cyan-600',
    },
    {
      icon: <ShieldPlus className="h-5 w-5 text-violet-600" />,
      name: 'Bảo hành mở rộng S24+',
      targets: 'Điện thoại mới, MacBook, phụ kiện cao cấp',
      benefit: 'Gia hạn bảo hành 24–36 tháng sau khi hết bảo hành chính hãng',
      color: 'border-violet-200 bg-violet-50',
      badge: 'bg-violet-600',
    },
  ];

  const sections: Section[] = [
    {
      id: 'ew-1',
      number: '1',
      title: 'Quy định chung',
      icon: <ShieldPlus className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <p>
            Chính sách bảo hành mở rộng của ElectroMart Việt Nam được xây dựng nhằm gia tăng quyền lợi hậu mãi cho khách hàng sau khi mua sản phẩm. Bên cạnh bảo hành tiêu chuẩn của nhà sản xuất, khách hàng có thể lựa chọn thêm các gói bảo hành mở rộng để được hỗ trợ tốt hơn trong trường hợp phát sinh lỗi kỹ thuật, lỗi phần cứng hoặc sự cố ngoài ý muốn.
          </p>
          <Note>
            Việc tham gia gói bảo hành mở rộng là <strong>tự nguyện</strong> và được ghi nhận trực tiếp trên hệ thống tại thời điểm mua hàng hoặc trong khoảng thời gian cho phép theo quy định của ElectroMart Việt Nam.
          </Note>

          {/* 3 package cards */}
          <div className="grid gap-3 sm:grid-cols-3">
            {pkgCards.map((pkg) => (
              <div key={pkg.name} className={`rounded-xl border p-4 ${pkg.color}`}>
                <div className="mb-2 flex items-center gap-2">
                  <div className={`flex h-7 w-7 items-center justify-center rounded-lg ${pkg.badge} text-white`}>
                    {pkg.icon}
                  </div>
                  <span className="text-xs font-bold text-slate-700">{pkg.name}</span>
                </div>
                <p className="text-xs text-slate-500 leading-relaxed">{pkg.targets}</p>
                <p className="mt-2 text-xs font-semibold text-slate-700">{pkg.benefit}</p>
              </div>
            ))}
          </div>
        </div>
      ),
    },
    {
      id: 'ew-2',
      number: '2',
      title: 'Tổng quan các gói bảo hành mở rộng',
      icon: <Package className="h-5 w-5" />,
      content: (
        <Table
          headers={['Tên gói bảo hành', 'Đối tượng áp dụng', 'Mục đích chính']}
          rows={[
            ['Bảo hành 1 đổi 1 VIP', 'Điện thoại, máy tính bảng, laptop, đồng hồ thông minh, tai nghe cao cấp', 'Đổi sản phẩm tương đương khi phát sinh lỗi phần cứng do nhà sản xuất'],
            ['Bảo hành rơi vỡ – rơi nước', 'Điện thoại, máy tính bảng', 'Hỗ trợ chi phí sửa chữa khi rơi vỡ, vào nước hoặc tác động ngoại lực'],
            ['Bảo hành mở rộng S24+', 'Điện thoại, MacBook, phụ kiện cao cấp', 'Gia hạn thời gian bảo hành sau khi hết bảo hành chính hãng'],
          ]}
        />
      ),
    },
    {
      id: 'ew-3',
      number: '3',
      title: 'Gói bảo hành 1 đổi 1 VIP',
      icon: <Star className="h-5 w-5" />,
      content: (
        <div className="space-y-5 text-sm text-slate-600 leading-relaxed">
          {/* 3.1 */}
          <div className="space-y-2">
            <h4 className="text-sm font-bold text-slate-800">3.1. Sản phẩm áp dụng</h4>
            <BulletList
              items={[
                'Điện thoại mới hoặc đã qua sử dụng',
                'Máy tính bảng mới hoặc đã qua sử dụng',
                'Tai nghe cao cấp',
                'Đồng hồ thông minh Apple hoặc Samsung',
                'Laptop, MacBook hoặc một số sản phẩm công nghệ khác nếu được ElectroMart Việt Nam công bố áp dụng tại thời điểm bán hàng',
              ]}
            />
          </div>
          {/* 3.2 */}
          <div className="space-y-2">
            <h4 className="text-sm font-bold text-slate-800">3.2. Thời gian tham gia</h4>
            <Table
              headers={['Gói thời hạn', 'Thời gian hiệu lực']}
              rows={[
                ['Gói 6 tháng', '06 tháng kể từ ngày kích hoạt gói'],
                ['Gói 12 tháng', '12 tháng kể từ ngày kích hoạt gói'],
              ]}
            />
          </div>
          {/* 3.3 */}
          <div className="space-y-2">
            <h4 className="text-sm font-bold text-slate-800">3.3. Quyền lợi bảo hành</h4>
            <BulletList
              items={[
                'Được kiểm tra và xác định lỗi sản phẩm theo quy trình kỹ thuật của ElectroMart Việt Nam hoặc trung tâm bảo hành được ủy quyền.',
                'Được đổi sang sản phẩm tương đương nếu lỗi thuộc phạm vi bảo hành của gói.',
                'Không giới hạn số lần bảo hành đổi sản phẩm trong thời gian hiệu lực, với điều kiện mỗi lần đều đáp ứng đầy đủ điều kiện của chính sách.',
                'Sản phẩm đổi bảo hành có thể là cùng loại, cùng cấu hình, cùng tình trạng thương mại hoặc tương đương về giá trị sử dụng.',
                'Khách hàng có thể chuyển nhượng quyền sở hữu sản phẩm và gói bảo hành trong thời gian còn hiệu lực nếu được ghi nhận hợp lệ trên hệ thống.',
              ]}
            />
          </div>
          {/* 3.4 */}
          <div className="space-y-2">
            <h4 className="text-sm font-bold text-slate-800">3.4. Điều kiện bảo hành</h4>
            <BulletList
              items={[
                'Sản phẩm còn thời hạn bảo hành mở rộng.',
                'Lỗi do nhà sản xuất hoặc lỗi phần cứng trong điều kiện sử dụng bình thường.',
                'Sản phẩm không bị cấn móp, cong vênh, nứt vỡ, biến dạng hoặc có dấu hiệu tác động vật lý nghiêm trọng.',
                'Sản phẩm không bị vào nước, ẩm mốc, cháy nổ, oxy hóa hoặc hư hỏng do môi trường.',
                'Chưa từng bị tự ý tháo mở, sửa chữa, thay linh kiện hoặc can thiệp phần mềm trái phép.',
                'Số IMEI, Serial hoặc mã định danh còn nguyên vẹn và trùng khớp với thông tin trên hệ thống.',
              ]}
            />
          </div>
          {/* 3.5 */}
          <div className="flex items-center gap-3 rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-3">
            <Clock className="h-5 w-5 shrink-0 text-indigo-600" />
            <div>
              <p className="text-sm font-semibold text-indigo-800">3.5. Thời gian xử lý</p>
              <p className="text-sm text-indigo-700">Từ <strong>24 giờ đến tối đa 14 ngày làm việc</strong>, tùy tình trạng sản phẩm, khả năng xác định lỗi và tình trạng hàng thay thế.</p>
            </div>
          </div>
        </div>
      ),
    },
    {
      id: 'ew-4',
      number: '4',
      title: 'Gói bảo hành rơi vỡ – Rơi nước',
      icon: <Droplets className="h-5 w-5" />,
      content: (
        <div className="space-y-5 text-sm text-slate-600 leading-relaxed">
          {/* 4.1 */}
          <div className="space-y-2">
            <h4 className="text-sm font-bold text-slate-800">4.1. Sản phẩm áp dụng</h4>
            <BulletList items={['Điện thoại mới hoặc đã qua sử dụng', 'Máy tính bảng mới hoặc đã qua sử dụng', 'Một số nhóm sản phẩm khác nếu được ElectroMart Việt Nam công bố tại thời điểm bán hàng']} />
          </div>
          {/* 4.2 */}
          <div className="flex items-center gap-3 rounded-lg border border-cyan-200 bg-cyan-50 px-4 py-3">
            <Clock className="h-5 w-5 shrink-0 text-cyan-600" />
            <p className="text-sm text-cyan-800"><strong>4.2. Thời hạn hiệu lực:</strong> 12 tháng kể từ ngày kích hoạt gói trên hệ thống.</p>
          </div>
          {/* 4.3 */}
          <div className="space-y-2">
            <h4 className="text-sm font-bold text-slate-800">4.3. Quyền lợi bảo hành</h4>
            <BulletList
              items={[
                'Được hỗ trợ chi phí sửa chữa khi sản phẩm bị hư hỏng do rơi vỡ, vào nước hoặc tác động ngoại lực.',
                'ElectroMart Việt Nam hỗ trợ tối đa 90% chi phí sửa chữa; khách hàng thanh toán phần còn lại theo báo giá.',
                'Không giới hạn số lần hỗ trợ trong thời gian hiệu lực, với điều kiện tổng chi phí hỗ trợ không vượt giới hạn bảo hành của sản phẩm.',
                'Nếu sản phẩm không thể sửa chữa, ElectroMart Việt Nam có thể hỗ trợ đổi sản phẩm đã qua sử dụng tương đương hoặc nhập lại để khách hàng nâng cấp.',
                'Sau khi đổi sản phẩm do không thể sửa chữa, gói bảo hành đối với sản phẩm ban đầu được xem là đã hoàn tất hiệu lực.',
              ]}
            />
          </div>
          {/* 4.4 */}
          <div className="space-y-2">
            <h4 className="text-sm font-bold text-slate-800">4.4. Điều kiện bảo hành</h4>
            <BulletList
              items={[
                'Sản phẩm còn thời hạn hiệu lực của gói.',
                'Sản phẩm bị vỡ, nứt, hư hỏng linh kiện hoặc ngấm nước/chất lỏng làm ảnh hưởng đến hoạt động.',
                'Còn xác định được IMEI, Serial hoặc mã định danh sản phẩm.',
                'Chưa bị can thiệp sửa chữa tại đơn vị không được ElectroMart Việt Nam hoặc hãng sản xuất ủy quyền.',
                'Khách hàng cung cấp đủ thông tin đơn hàng, hóa đơn hoặc dữ liệu mua gói bảo hành trên hệ thống.',
              ]}
            />
          </div>
          {/* 4.5 */}
          <div className="space-y-2">
            <h4 className="text-sm font-bold text-slate-800">4.5. Giới hạn hỗ trợ — Không áp dụng khi:</h4>
            <BulletList
              items={[
                'Sản phẩm bị mất hoàn toàn hoặc không còn khả năng xác định mã định danh.',
                'Sản phẩm bị cố ý phá hoại, sử dụng sai mục đích hoặc trong điều kiện không phù hợp khuyến cáo nhà sản xuất.',
                'Sản phẩm đã được sửa chữa trước đó bởi bên thứ ba không được ủy quyền.',
                'Sản phẩm bị thay đổi linh kiện, thay đổi cấu trúc phần cứng hoặc có dấu hiệu gian lận bảo hành.',
                'Dữ liệu trong thiết bị bị mất, lỗi hoặc không thể phục hồi trong quá trình sửa chữa.',
              ]}
            />
          </div>
          {/* 4.6 */}
          <div className="flex items-center gap-3 rounded-lg border border-cyan-200 bg-cyan-50 px-4 py-3">
            <Clock className="h-5 w-5 shrink-0 text-cyan-600" />
            <p className="text-sm text-cyan-800"><strong>4.6. Thời gian xử lý:</strong> Từ <strong>07 đến 14 ngày làm việc</strong>, tùy mức độ hư hỏng, tình trạng linh kiện và kết quả thẩm định kỹ thuật.</p>
          </div>
        </div>
      ),
    },
    {
      id: 'ew-5',
      number: '5',
      title: 'Gói bảo hành mở rộng S24+',
      icon: <ShieldPlus className="h-5 w-5" />,
      content: (
        <div className="space-y-5 text-sm text-slate-600 leading-relaxed">
          {/* 5.1 */}
          <div className="space-y-2">
            <h4 className="text-sm font-bold text-slate-800">5.1. Sản phẩm áp dụng</h4>
            <BulletList items={['Điện thoại mới', 'MacBook', 'Phụ kiện cao cấp', 'Một số thiết bị công nghệ khác nếu được ElectroMart Việt Nam công bố tại từng thời điểm']} />
          </div>
          {/* 5.2 */}
          <div className="space-y-2">
            <h4 className="text-sm font-bold text-slate-800">5.2. Thời gian tham gia</h4>
            <p>Gói S24+ kéo dài từ <strong>24 đến 36 tháng</strong>, bao gồm thời gian bảo hành tiêu chuẩn từ nhà sản xuất.</p>
            <div className="rounded-lg border border-violet-200 bg-violet-50 px-4 py-3">
              <p className="text-sm font-semibold text-violet-800">Ví dụ minh họa:</p>
              <p className="mt-1 text-sm text-violet-700">Sản phẩm có 12 tháng bảo hành chính hãng + gói S24+ 24 tháng → khách hàng tiếp tục được ElectroMart Việt Nam bảo hành lỗi nhà sản xuất <strong>thêm 12 tháng</strong> sau khi hết bảo hành chính hãng.</p>
            </div>
          </div>
          {/* 5.3 */}
          <div className="space-y-2">
            <h4 className="text-sm font-bold text-slate-800">5.3. Quyền lợi bảo hành</h4>
            <BulletList
              items={[
                'Sau khi hết bảo hành chính hãng, sản phẩm tiếp tục được bảo hành với các lỗi phát sinh từ nhà sản xuất.',
                'Miễn phí chi phí sửa chữa và thay thế linh kiện đối với lỗi thuộc phạm vi bảo hành.',
                'Nếu sản phẩm không thể sửa chữa, ElectroMart Việt Nam có thể đổi sản phẩm tương đương hoặc hỗ trợ nhập lại để nâng cấp.',
              ]}
            />
          </div>
          {/* 5.4 */}
          <div className="space-y-2">
            <h4 className="text-sm font-bold text-slate-800">5.4. Điều kiện bảo hành</h4>
            <BulletList
              items={[
                'Sản phẩm đã hết bảo hành chính hãng nhưng vẫn còn thời hạn bảo hành mở rộng.',
                'Lỗi phát sinh được xác định là lỗi do nhà sản xuất.',
                'Sản phẩm không bị cấn móp, cong vênh, nứt vỡ, vào nước, cháy nổ hoặc biến dạng.',
                'Chưa bị tự ý tháo mở, sửa chữa, thay linh kiện hoặc can thiệp phần mềm trái phép.',
                'IMEI, Serial còn nguyên vẹn và trùng khớp với dữ liệu bảo hành trên hệ thống.',
              ]}
            />
          </div>
          {/* 5.5 */}
          <div className="flex items-center gap-3 rounded-lg border border-violet-200 bg-violet-50 px-4 py-3">
            <Clock className="h-5 w-5 shrink-0 text-violet-600" />
            <p className="text-sm text-violet-800"><strong>5.5. Thời gian xử lý:</strong> <strong>07–14 ngày làm việc</strong>. Với MacBook có thể kéo dài <strong>03–04 tuần</strong> tùy quy trình kiểm tra của hãng.</p>
          </div>
        </div>
      ),
    },
    {
      id: 'ew-6',
      number: '6',
      title: 'Biểu phí bảo hành mở rộng',
      icon: <BadgeCheck className="h-5 w-5" />,
      content: (
        <div className="space-y-6 text-sm text-slate-600 leading-relaxed">
          {/* 6.1 */}
          <div className="space-y-2">
            <h4 className="text-sm font-bold text-slate-800">6.1. Điện thoại và máy tính bảng</h4>
            <Table
              headers={['Khoảng giá sản phẩm', '1đ1 VIP 6T', '1đ1 VIP 12T', 'Rơi vỡ / Nước', 'S24+ 12T']}
              rows={[
                ['Dưới 2.500.000đ', '150.000đ', '200.000đ', '250.000đ', '150.000đ'],
                ['2.500.001 – 4.000.000đ', '180.000đ', '250.000đ', '350.000đ', '180.000đ'],
                ['4.000.001 – 5.000.000đ', '200.000đ', '300.000đ', '450.000đ', '250.000đ'],
                ['5.000.001 – 6.500.000đ', '300.000đ', '400.000đ', '550.000đ', '320.000đ'],
                ['6.500.001 – 7.500.000đ', '350.000đ', '450.000đ', '600.000đ', '400.000đ'],
                ['7.500.001 – 8.500.000đ', '400.000đ', '550.000đ', '700.000đ', '450.000đ'],
                ['8.500.001 – 10.000.000đ', '450.000đ', '600.000đ', '800.000đ', '500.000đ'],
                ['10.000.001 – 12.000.000đ', '500.000đ', '750.000đ', '1.000.000đ', '600.000đ'],
                ['12.000.001 – 14.000.000đ', '600.000đ', '850.000đ', '1.100.000đ', '700.000đ'],
                ['14.000.001 – 16.000.000đ', '700.000đ', '1.000.000đ', '1.300.000đ', '800.000đ'],
                ['16.000.001 – 18.000.000đ', '800.000đ', '1.100.000đ', '1.400.000đ', '900.000đ'],
                ['18.000.001 – 20.000.000đ', '900.000đ', '1.200.000đ', '1.500.000đ', '1.000.000đ'],
                ['20.000.001 – 25.000.000đ', '1.100.000đ', '1.400.000đ', '1.800.000đ', '1.200.000đ'],
                ['25.000.001 – 30.000.000đ', '1.200.000đ', '1.600.000đ', '2.000.000đ', '1.400.000đ'],
                ['30.000.001 – 40.000.000đ', '1.300.000đ', '1.800.000đ', '2.400.000đ', '1.600.000đ'],
                ['40.000.001 – 50.000.000đ', '1.500.000đ', '2.200.000đ', '3.000.000đ', '2.000.000đ'],
                ['50.000.001 – 60.000.000đ', '1.800.000đ', '2.500.000đ', '3.500.000đ', '2.200.000đ'],
              ]}
            />
          </div>
          {/* 6.2 */}
          <div className="space-y-2">
            <h4 className="text-sm font-bold text-slate-800">6.2. Laptop và MacBook</h4>
            <Table
              headers={['Khoảng giá sản phẩm', '1 đổi 1 VIP', 'S24+ 12 tháng', 'S24+ 24 tháng']}
              rows={[
                ['Dưới 10.000.000đ', '700.000đ', '700.000đ', '1.400.000đ'],
                ['10.000.001 – 15.000.000đ', '1.000.000đ', '1.000.000đ', '1.800.000đ'],
                ['15.000.001 – 20.000.000đ', '1.500.000đ', '1.400.000đ', '2.300.000đ'],
                ['20.000.001 – 25.000.000đ', '1.800.000đ', '1.800.000đ', '2.800.000đ'],
                ['25.000.001 – 30.000.000đ', '2.200.000đ', '2.200.000đ', '3.400.000đ'],
                ['30.000.001 – 35.000.000đ', '2.600.000đ', '2.600.000đ', '3.800.000đ'],
                ['35.000.001 – 40.000.000đ', '3.000.000đ', '3.000.000đ', '4.000.000đ'],
                ['45.000.001 – 100.000.000đ', '4.000.000đ', '4.000.000đ', '5.000.000đ'],
              ]}
            />
            <PricingNote>Gói S24+ chỉ áp dụng cho MacBook hoặc các sản phẩm được ElectroMart Việt Nam công bố hỗ trợ tại từng thời điểm.</PricingNote>
          </div>
          {/* 6.3 */}
          <div className="space-y-2">
            <h4 className="text-sm font-bold text-slate-800">6.3. Phụ kiện cao cấp</h4>
            <Table
              headers={['Khoảng giá sản phẩm', '1 đổi 1 VIP', 'S24+ 12 tháng']}
              rows={[
                ['Dưới 1.000.000đ', '100.000đ', '100.000đ'],
                ['1.000.001 – 2.000.000đ', '200.000đ', '100.000đ'],
                ['2.000.001 – 3.000.000đ', '300.000đ', '150.000đ'],
                ['3.000.001 – 4.000.000đ', '400.000đ', '200.000đ'],
                ['4.000.001 – 5.000.000đ', '400.000đ', '300.000đ'],
                ['5.000.001 – 8.000.000đ', '600.000đ', '400.000đ'],
                ['8.000.001 – 10.000.000đ', '800.000đ', '500.000đ'],
                ['10.000.001 – 15.000.000đ', '1.000.000đ', '650.000đ'],
                ['15.000.001 – 20.000.000đ', '1.400.000đ', '800.000đ'],
                ['20.000.001 – 30.000.000đ', '2.000.000đ', '1.000.000đ'],
                ['30.000.001 – 40.000.000đ', '2.000.000đ', '1.200.000đ'],
              ]}
            />
          </div>
          {/* 6.4 */}
          <div className="space-y-2">
            <h4 className="text-sm font-bold text-slate-800">6.4. Tivi</h4>
            <Table
              headers={['Khoảng giá sản phẩm', '1 đổi 1 VIP']}
              rows={[
                ['3.000.000 – 5.000.000đ', '300.000đ'],
                ['5.000.001 – 7.000.000đ', '400.000đ'],
                ['7.000.001 – 10.000.000đ', '500.000đ'],
                ['10.000.001 – 12.000.000đ', '600.000đ'],
                ['12.000.001 – 14.000.000đ', '700.000đ'],
                ['14.000.001 – 16.000.000đ', '800.000đ'],
                ['16.000.001 – 18.000.000đ', '900.000đ'],
                ['18.000.001 – 20.000.000đ', '1.000.000đ'],
                ['20.000.001 – 22.000.000đ', '1.100.000đ'],
                ['22.000.001 – 25.000.000đ', '1.300.000đ'],
                ['25.000.001 – 30.000.000đ', '1.500.000đ'],
                ['30.000.001 – 40.000.000đ', '2.000.000đ'],
                ['40.000.001 – 50.000.000đ', '2.500.000đ'],
                ['50.000.001 – 60.000.000đ', '3.000.000đ'],
                ['60.000.001 – 70.000.000đ', '3.500.000đ'],
                ['70.000.001 – 80.000.000đ', '4.000.000đ'],
                ['80.000.001 – 100.000.000đ', '5.000.000đ'],
              ]}
            />
          </div>
        </div>
      ),
    },
    {
      id: 'ew-7',
      number: '7',
      title: 'Phân loại gói theo nhóm sản phẩm',
      icon: <Package className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Nhóm sản phẩm', '1 đổi 1 VIP', 'Rơi vỡ – Rơi nước', 'S24+']}
            rows={[
              ['Điện thoại mới', 'Có', 'Có', 'Có'],
              ['Điện thoại đã qua sử dụng', 'Có', 'Có', 'Không áp dụng mặc định'],
              ['Máy tính bảng mới', 'Có', 'Có', 'Có'],
              ['Máy tính bảng đã qua sử dụng', 'Có', 'Có', 'Không áp dụng mặc định'],
              ['Laptop', 'Có', 'Không áp dụng mặc định', 'Có'],
              ['MacBook', 'Có', 'Không áp dụng mặc định', 'Có'],
              ['Phụ kiện cao cấp', 'Có', 'Không áp dụng', 'Có'],
              ['Đồng hồ Apple/Samsung', 'Có', 'Không áp dụng mặc định', 'Không áp dụng mặc định'],
              ['Tivi', 'Có', 'Không áp dụng', 'Không áp dụng mặc định'],
            ]}
          />
          <Note>Một số nhóm sản phẩm đặc thù có thể bị giới hạn quyền tham gia gói bảo hành mở rộng, tùy theo cấu tạo sản phẩm, chính sách nhà sản xuất, khả năng sửa chữa và quy định của ElectroMart Việt Nam tại từng thời điểm.</Note>
        </div>
      ),
    },
    {
      id: 'ew-8',
      number: '8',
      title: 'Các trường hợp không áp dụng bảo hành mở rộng',
      icon: <AlertTriangle className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList
            items={[
              'Sản phẩm hết thời hạn bảo hành mở rộng.',
              'Sản phẩm không có dữ liệu đăng ký gói bảo hành trên hệ thống.',
              'Sản phẩm bị mất IMEI, Serial hoặc mã định danh.',
              'Sản phẩm bị can thiệp phần cứng, thay linh kiện hoặc sửa chữa tại đơn vị không được ủy quyền.',
              'Sản phẩm bị biến dạng nghiêm trọng, không còn khả năng kiểm tra kỹ thuật.',
              'Hư hỏng do cố ý phá hoại, sử dụng sai mục đích hoặc vi phạm hướng dẫn sử dụng.',
              'Sản phẩm không thuộc nhóm hàng được hỗ trợ gói bảo hành đã mua.',
              'Khách hàng không cung cấp được thông tin đơn hàng, hóa đơn hoặc tài khoản liên quan đến gói bảo hành.',
            ]}
          />
        </div>
      ),
    },
    {
      id: 'ew-9',
      number: '9',
      title: 'Quy định hoàn trả gói bảo hành mở rộng',
      icon: <RefreshCw className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Khách hàng có thể yêu cầu hoàn trả gói trong thời hạn <strong>07 ngày</strong> kể từ ngày mua gói, với điều kiện:</p>
          <BulletList
            items={[
              'Sản phẩm chưa phát sinh yêu cầu bảo hành theo gói.',
              'Gói bảo hành chưa được sử dụng để đổi sản phẩm, sửa chữa, hỗ trợ rơi vỡ/nước hoặc xử lý kỹ thuật.',
              'Khách hàng cung cấp đầy đủ hóa đơn, thông tin đơn hàng và chứng từ liên quan.',
            ]}
          />
          <div className="rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-3">
            <p className="text-sm font-semibold text-indigo-800">Mức hoàn trả:</p>
            <p className="mt-1 text-sm font-bold text-indigo-700">Giá trị hoàn trả = Giá trị gói bảo hành × 50%</p>
          </div>
          <Note>Sau thời hạn 07 ngày hoặc sau khi gói đã phát sinh quyền lợi bảo hành, ElectroMart Việt Nam không áp dụng hoàn trả phí gói bảo hành mở rộng.</Note>
        </div>
      ),
    },
    {
      id: 'ew-10',
      number: '10',
      title: 'Quy định về chuyển nhượng gói bảo hành',
      icon: <ArrowRight className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList
            items={[
              'Gói bảo hành mở rộng có thể được chuyển nhượng cùng với sản phẩm trong thời gian còn hiệu lực, nếu sản phẩm vẫn đáp ứng điều kiện bảo hành.',
              'Người nhận chuyển nhượng cần cung cấp thông tin sản phẩm, hóa đơn hoặc dữ liệu mua hàng để ElectroMart Việt Nam xác nhận quyền lợi trên hệ thống.',
              'Việc chuyển nhượng không làm thay đổi thời hạn hiệu lực, quyền lợi, giới hạn bảo hành hoặc điều kiện áp dụng của gói đã mua.',
            ]}
          />
        </div>
      ),
    },
    {
      id: 'ew-11',
      number: '11',
      title: 'Lưu trữ dữ liệu bảo hành mở rộng trên hệ thống',
      icon: <Archive className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Trường dữ liệu', 'Nội dung']}
            rows={[
              ['Mã gói bảo hành', 'Mã định danh duy nhất của gói'],
              ['Loại gói', '1 đổi 1 VIP, rơi vỡ – rơi nước, S24+'],
              ['Mã sản phẩm', 'Sản phẩm được áp dụng gói'],
              ['IMEI / Serial', 'Mã định danh thiết bị'],
              ['Mã khách hàng', 'Người mua hoặc người đang sở hữu hợp lệ'],
              ['Ngày kích hoạt', 'Ngày bắt đầu hiệu lực'],
              ['Ngày hết hạn', 'Ngày kết thúc hiệu lực'],
              ['Giá trị gói', 'Phí khách hàng đã thanh toán'],
              ['Trạng thái gói', 'Còn hiệu lực / Đã hết hạn / Đã sử dụng / Đã hoàn trả / Đã chuyển nhượng'],
              ['Lịch sử bảo hành', 'Các lần tiếp nhận và xử lý theo gói'],
              ['Giới hạn hỗ trợ', 'Mức hỗ trợ tối đa nếu có'],
            ]}
          />
          <p>Việc lưu trữ dữ liệu này giúp hạn chế tranh chấp, hỗ trợ tra cứu nhanh quyền lợi bảo hành và tạo cơ sở xây dựng chức năng quản lý bảo hành mở rộng trong hệ thống ElectroMart Việt Nam.</p>
        </div>
      ),
    },
    {
      id: 'ew-12',
      number: '12',
      title: 'Kết luận',
      icon: <BadgeCheck className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Chính sách bảo hành mở rộng của ElectroMart Việt Nam được xây dựng nhằm tăng cường quyền lợi hậu mãi, nâng cao sự an tâm của khách hàng và hỗ trợ hệ thống vận hành chính sách bảo hành một cách minh bạch, nhất quán.</p>
          <div className="rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-3">
            <p className="text-sm font-semibold text-indigo-800">
              Thông qua việc phân loại rõ từng gói bảo hành, quy định cụ thể quyền lợi, điều kiện áp dụng, thời gian xử lý, biểu phí và dữ liệu cần lưu trữ, ElectroMart Việt Nam có thể triển khai chính sách bảo hành mở rộng phù hợp với thực tiễn vận hành của một hệ thống thương mại điện tử chuyên về thiết bị công nghệ.
            </p>
          </div>
        </div>
      ),
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Banner */}
      <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-900/60">
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage:
              'radial-gradient(circle at 20% 60%, #4f46e5 0%, transparent 50%), radial-gradient(circle at 80% 20%, #7c3aed 0%, transparent 40%)',
          }}
        />
        <div className="relative mx-auto max-w-5xl px-4 py-12 lg:px-6">
          {/* Breadcrumb */}
          <nav className="mb-5 flex items-center gap-1.5 text-xs text-slate-400">
            <Link to="/" className="transition hover:text-white">Trang chủ</Link>
            <span>/</span>
            <Link to="/about" className="transition hover:text-white">Giới thiệu công ty</Link>
            <span>/</span>
            <span className="text-slate-200">Bảo hành mở rộng</span>
          </nav>

          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-indigo-600 shadow-lg shadow-indigo-500/30">
              <ShieldPlus className="h-6 w-6 text-white" />
            </div>
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-indigo-400">Chính sách</p>
              <h1 className="text-2xl font-bold font-display leading-tight text-white lg:text-3xl">
                Chính sách bảo hành mở rộng
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-300">
                Ba gói bảo hành mở rộng cao cấp — 1 đổi 1 VIP, Rơi vỡ – Rơi nước và S24+ — giúp khách hàng yên tâm mua sắm với quyền lợi hậu mãi vượt trội tại ElectroMart Việt Nam.
              </p>
            </div>
          </div>

          {/* Quick stats */}
          <div className="mt-8 grid grid-cols-3 gap-4 border-t border-white/10 pt-6">
            {[
              { label: 'Gói bảo hành mở rộng', value: '3' },
              { label: 'Nhóm sản phẩm hỗ trợ', value: '9' },
              { label: 'Hỗ trợ rơi vỡ / nước', value: '90%' },
            ].map((s) => (
              <div key={s.label} className="text-center">
                <div className="text-2xl font-bold text-indigo-400">{s.value}</div>
                <div className="mt-0.5 text-xs text-slate-500">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="mx-auto max-w-5xl px-4 py-10 lg:px-6">
        <div className="space-y-3">
          {sections.map((section) => {
            const isOpen = expanded === section.id;
            return (
              <div
                key={section.id}
                className={`overflow-hidden rounded-xl border transition-all duration-200 ${
                  isOpen
                    ? 'border-indigo-200 bg-white shadow-md shadow-indigo-500/5'
                    : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm'
                }`}
              >
                <button
                  id={`extwarranty-section-${section.number}`}
                  onClick={() => toggle(section.id)}
                  className="flex w-full items-center gap-4 px-5 py-4 text-left"
                  aria-expanded={isOpen}
                >
                  <div
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors ${
                      isOpen ? 'bg-indigo-600 text-white' : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    {section.icon}
                  </div>
                  <div className="flex-1">
                    <div className="mb-0.5">
                      <span className={`text-xs font-bold ${isOpen ? 'text-indigo-600' : 'text-slate-400'}`}>
                        Điều {section.number}
                      </span>
                    </div>
                    <div className={`text-sm font-semibold leading-tight ${isOpen ? 'text-indigo-700' : 'text-slate-800'}`}>
                      {section.title}
                    </div>
                  </div>
                  <div className={`shrink-0 transition-colors ${isOpen ? 'text-indigo-600' : 'text-slate-400'}`}>
                    {isOpen ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
                  </div>
                </button>

                {isOpen && (
                  <div className="border-t border-slate-100 px-5 py-5">
                    {section.content}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Navigation */}
        <div className="mt-10 flex flex-wrap gap-3">
          <Link
            to="/about"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
          >
            ← Về trang giới thiệu
          </Link>
          <Link
            to="/warranty"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
          >
            Chính sách bảo hành tiêu chuẩn
          </Link>
          <Link
            to="/products"
            className="inline-flex items-center gap-2 rounded-xl bg-primary px-5 py-2.5 text-sm font-bold text-white shadow-sm transition hover:bg-red-700"
          >
            Xem sản phẩm
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>
      </div>
    </div>
  );
}
