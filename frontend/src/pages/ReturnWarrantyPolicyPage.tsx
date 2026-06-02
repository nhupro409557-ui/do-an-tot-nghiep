import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ChevronDown, ChevronUp, ShieldAlert, Settings, Wrench, RefreshCw, 
  RotateCcw, DollarSign, Clock, FileText, AlertTriangle, ShieldCheck, 
  Database, Smartphone, HardDrive, FileWarning, HelpCircle, Package, ArrowRight
} from 'lucide-react';

function Table({ headers, rows }: { headers: string[]; rows: string[][] }) {
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
            <tr key={i} className="transition-colors hover:bg-slate-50/60">
              {row.map((cell, j) => (
                <td
                  key={j}
                  className={`px-4 py-2.5 leading-relaxed text-slate-600 ${
                    j === 0 ? 'font-semibold text-slate-700' : ''
                  }`}
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
          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-fuchsia-500" />
          {item}
        </li>
      ))}
    </ul>
  );
}

interface Section {
  id: string;
  number: string;
  title: string;
  icon: React.ReactNode;
  content: React.ReactNode;
}

export default function ReturnWarrantyPolicyPage() {
  const [expanded, setExpanded] = useState<string | null>('rw-1');
  const toggle = (id: string) => setExpanded((p) => (p === id ? null : id));

  const sections: Section[] = [
    {
      id: 'rw-1',
      number: '1',
      title: 'Quy định chung',
      icon: <ShieldAlert className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>ElectroMart Việt Nam xây dựng chính sách bảo hành, đổi trả và hỗ trợ kỹ thuật nhằm bảo đảm quyền lợi của khách hàng sau khi mua sản phẩm tại hệ thống.</p>
          <p>Chính sách quy định rõ điều kiện bảo hành, thời hạn đổi trả, nguyên tắc nhập lại sản phẩm, quy trình tiếp nhận bảo hành, các trường hợp từ chối bảo hành miễn phí, quyền lợi bảo hành mở rộng và trách nhiệm các bên trong quá trình xử lý kỹ thuật.</p>
        </div>
      ),
    },
    {
      id: 'rw-2',
      number: '2',
      title: 'Chính sách đổi mới sản phẩm lỗi do nhà sản xuất',
      icon: <RefreshCw className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <div className="mb-4 rounded-xl overflow-hidden border border-slate-100 shadow-sm max-w-md mx-auto bg-slate-50">
            <img src="/images/policies/warranty.png" alt="Bảo hành và đổi mới" className="w-full h-auto mix-blend-multiply" />
          </div>
          <p className="font-semibold text-slate-800">Điều kiện đổi mới:</p>
          <BulletList items={[
            'Còn trong thời hạn đổi mới và lỗi do nhà sản xuất.',
            'Không rơi vỡ, cấn móp, nứt, vào nước, cháy nổ, biến dạng.',
            'Chưa tự ý tháo mở, sửa chữa, thay linh kiện hoặc can thiệp phần mềm trái phép.',
            'Còn đầy đủ hộp, phụ kiện, quà tặng và chứng từ mua hàng.',
            'IMEI/Serial nguyên vẹn và trùng khớp dữ liệu hệ thống.',
          ]} />
          <Table
            headers={['Tình huống', 'Phương án xử lý']}
            rows={[
              ['Còn sản phẩm cùng loại', 'Đổi sản phẩm mới cùng loại'],
              ['Hết sản phẩm cùng loại', 'Đổi sang sản phẩm tương đương'],
              ['Khách muốn đổi sản phẩm khác', 'Khách hàng thanh toán phần chênh lệch (nếu cao hơn)'],
              ['Sản phẩm cần kiểm tra chuyên sâu', 'Gửi đến trung tâm bảo hành hãng hoặc bộ phận kỹ thuật'],
              ['Không đủ điều kiện đổi mới', 'Chuyển sang bảo hành hoặc sửa chữa có phí'],
            ]}
          />
        </div>
      ),
    },
    {
      id: 'rw-3',
      number: '3',
      title: 'Thời hạn đổi mới và nhập lại',
      icon: <Clock className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Loại sản phẩm', 'Thời gian đổi mới', 'Quy định nhập lại']}
            rows={[
              ['Điện thoại, máy tính bảng', '30 ngày', 'Áp dụng nếu đủ điều kiện'],
              ['Laptop, MacBook', '30 ngày', 'Áp dụng nếu đủ điều kiện'],
              ['Đồng hồ thông minh', '15–30 ngày', 'Tùy từng dòng sản phẩm'],
              ['Màn hình máy tính', '15 ngày', 'Áp dụng nếu đủ điều kiện'],
              ['PC, máy in, thiết bị văn phòng', '15 ngày', 'Không mặc định áp dụng'],
              ['Loa, tai nghe', '15 ngày', 'Tùy từng nhóm sản phẩm'],
              ['Phụ kiện dưới 1 triệu', 'Theo bảo hành', 'Không áp dụng nhập lại'],
              ['Phụ kiện từ 1 triệu trở lên', '15 ngày', 'Không áp dụng (trừ sản phẩm đặc thù)'],
              ['Tivi, thiết bị gia dụng', '15–30 ngày', 'Không mặc định áp dụng'],
              ['Hàng đã qua sử dụng', '30 ngày', 'Áp dụng nếu đủ điều kiện'],
            ]}
          />
        </div>
      ),
    },
    {
      id: 'rw-4',
      number: '4',
      title: 'Mốc thời gian bắt đầu bảo hành, đổi trả',
      icon: <Clock className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Hình thức mua hàng', 'Mốc thời gian bắt đầu']}
            rows={[
              ['Mua trực tiếp tại cửa hàng', 'Tính từ ngày in hóa đơn / giao dịch hoàn tất'],
              ['Mua online giao tận nơi', 'Tính từ ngày trạng thái "Giao hàng thành công"'],
              ['Đặt online, nhận tại cửa hàng', 'Tính từ ngày ký nhận sản phẩm'],
              ['Sản phẩm đặt trước/đặt cọc', 'Tính từ ngày nhận sản phẩm thực tế'],
              ['Sản phẩm đổi bảo hành', 'Tính theo thời hạn còn lại của sản phẩm ban đầu'],
            ]}
          />
        </div>
      ),
    },
    {
      id: 'rw-5',
      number: '5',
      title: 'Quy định nhập lại và công thức khấu trừ',
      icon: <DollarSign className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <p className="font-semibold text-fuchsia-700 bg-fuchsia-50 px-3 py-2 rounded-md">Giá trị hoàn trả = Giá trị hóa đơn hợp lệ × Tỷ lệ hoàn trả còn lại</p>
          <Table
            headers={['Thời gian sử dụng', 'Tỷ lệ khấu trừ', 'Tỷ lệ hoàn trả còn lại']}
            rows={[
              ['Trong 30 ngày đầu', '20%', '80%'],
              ['Từ tháng thứ 2', '25%', '75%'],
              ['Từ tháng thứ 3', '30%', '70%'],
              ['Từ tháng thứ 4', '35%', '65%'],
              ['Từ tháng thứ 5', '40%', '60%'],
              ['Từ tháng thứ 6 trở đi', 'Tăng thêm 5% mỗi tháng', 'Theo tỷ lệ còn lại'],
            ]}
          />
          <Note>Mức khấu trừ tối đa không vượt quá 70%. Khi đạt mức tối đa, ElectroMart có thể chuyển sang phương án bảo hành/sửa chữa thay vì hoàn tiền.</Note>
        </div>
      ),
    },
    {
      id: 'rw-6',
      number: '6',
      title: 'Điều kiện đổi trả và nhập lại',
      icon: <ShieldCheck className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList items={[
            'Còn trong thời hạn quy định, mua hợp lệ tại ElectroMart Việt Nam.',
            'Không bị lỗi do người dùng gây ra.',
            'Ngoại hình nguyên vẹn, không trầy xước nghiêm trọng, nứt vỡ, biến dạng.',
            'Không bị vào nước, ẩm mốc, cháy nổ, chập điện, hóa chất.',
            'Chưa bị tự ý tháo mở, sửa chữa, thay linh kiện, can thiệp phần mềm.',
            'Đầy đủ hộp, phụ kiện, quà tặng, chứng từ.',
            'Tài khoản cá nhân (iCloud, Google, Mi...) đã đăng xuất hoàn toàn.',
          ]} />
        </div>
      ),
    },
    {
      id: 'rw-7',
      number: '7',
      title: 'Khấu trừ hộp, phụ kiện và quà tặng',
      icon: <Package className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Thành phần thiếu/hư hỏng', 'Căn cứ khấu trừ']}
            rows={[
              ['Phụ kiện có bán lẻ', 'Khấu trừ theo giá bán lẻ niêm yết tại thời điểm đó'],
              ['Hộp sản phẩm', 'Khấu trừ phí đóng gói/thay thế theo từng nhóm sản phẩm'],
              ['Quà tặng có giá bán lẻ', 'Khấu trừ theo giá bán lẻ niêm yết'],
              ['Quà tặng không có giá bán lẻ', 'Khấu trừ theo giá trị quy đổi lúc mua'],
              ['Phụ kiện/quà tặng bị hư hỏng', 'Khấu trừ theo giá trị thay thế/quy đổi tương ứng'],
            ]}
          />
        </div>
      ),
    },
    {
      id: 'rw-8',
      number: '8',
      title: 'Hóa đơn VAT khi đổi trả, nhập lại',
      icon: <FileText className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <p>Đối với khách hàng doanh nghiệp, hộ kinh doanh, khi đổi trả cần cung cấp chứng từ:</p>
          <Table
            headers={['Trường hợp', 'Chứng từ cần cung cấp']}
            rows={[
              ['Trả lại toàn bộ sản phẩm', 'Biên bản trả hàng và thu hồi hóa đơn'],
              ['Trả lại một phần sản phẩm', 'Biên bản điều chỉnh giảm giá trị hóa đơn'],
              ['Đổi sang sản phẩm khác', 'Biên bản điều chỉnh hoặc hóa đơn thay thế'],
              ['Hoàn tiền qua chuyển khoản', 'Thông tin tài khoản nhận tiền hợp lệ'],
            ]}
          />
        </div>
      ),
    },
    {
      id: 'rw-9',
      number: '9',
      title: 'Chính sách bảo hành tiêu chuẩn',
      icon: <Wrench className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Nhóm sản phẩm', 'Thời gian bảo hành', 'Quyền lợi']}
            rows={[
              ['Sản phẩm mới', '12 tháng / theo hãng', 'Sửa chữa, thay linh kiện, đổi theo chính sách hãng'],
              ['Đã kích hoạt bảo hành', 'Theo thời hạn còn lại', 'Bảo hành theo hạn còn lại'],
              ['Sản phẩm đã qua sử dụng', '6 tháng / chính sách riêng', 'Sửa chữa, thay linh kiện'],
              ['Phụ kiện', '1–24 tháng', 'Đổi mới, sửa chữa hoặc thay thế'],
              ['Linh kiện máy tính', '12–36 tháng', 'Sửa chữa / đổi tương đương'],
            ]}
          />
        </div>
      ),
    },
    {
      id: 'rw-10',
      number: '10',
      title: 'Các lỗi được xem xét bảo hành',
      icon: <Settings className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <p>Lỗi được bảo hành là lỗi phát sinh trong điều kiện bình thường và do nhà sản xuất.</p>
          <Table
            headers={['Nhóm lỗi', 'Ví dụ']}
            rows={[
              ['Lỗi nguồn', 'Không lên nguồn, sập nguồn bất thường'],
              ['Lỗi mainboard', 'Không nhận linh kiện, lỗi xử lý hệ thống'],
              ['Lỗi màn hình', 'Sọc màn hình, điểm chết vượt ngưỡng'],
              ['Lỗi âm thanh', 'Không nhận loa, mic, tai nghe'],
              ['Lỗi kết nối', 'Không nhận Wi-Fi, Bluetooth, SIM, cổng kết nối'],
            ]}
          />
          <p className="font-semibold text-slate-800">Quy định lỗi điểm chết màn hình:</p>
          <BulletList items={[
            'Điện thoại, tablet: Từ 03 điểm chết trở lên hoặc 01 điểm kích thước >1mm.',
            'Laptop, màn hình rời: Từ 05 điểm chết trở lên.',
            'Tivi: Theo quy định hãng sản xuất.',
          ]} />
        </div>
      ),
    },
    {
      id: 'rw-11',
      number: '11',
      title: 'Các trường hợp không được bảo hành miễn phí',
      icon: <AlertTriangle className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList items={[
            'Hết thời hạn bảo hành hoặc không xác định được nguồn gốc mua hàng.',
            'Mất, rách, bong tróc tem bảo hành, Serial, IMEI.',
            'Rơi vỡ, va đập, cấn móp, nứt, cong vênh, vào nước, cháy nổ, hóa chất.',
            'Hư hỏng do côn trùng, thiên tai, hỏa hoạn, sử dụng sai nguồn điện.',
            'Tự ý tháo mở, sửa chữa, thay linh kiện bởi đơn vị không ủy quyền.',
            'Can thiệp phần mềm (root, jailbreak, up ROM không chính thức).',
            'Sử dụng để đào tiền điện tử hoặc mục đích quá tải không khuyến cáo.',
          ]} />
        </div>
      ),
    },
    {
      id: 'rw-12',
      number: '12',
      title: 'Quy trình tiếp nhận bảo hành, đổi trả',
      icon: <RotateCcw className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <ol className="list-decimal pl-5 space-y-2">
            <li><strong className="text-slate-800">Tiếp nhận yêu cầu:</strong> Khách hàng liên hệ CSKH hoặc mang đến cửa hàng.</li>
            <li><strong className="text-slate-800">Kiểm tra giao dịch:</strong> Kiểm tra hóa đơn, thời hạn, phụ kiện.</li>
            <li><strong className="text-slate-800">Kiểm tra sản phẩm:</strong> Kỹ thuật kiểm tra ngoại quan, lỗi, IMEI, tài khoản bảo mật.</li>
            <li><strong className="text-slate-800">Phân loại xử lý:</strong> Đổi mới, nhập lại, gửi hãng, sửa chữa, từ chối...</li>
            <li><strong className="text-slate-800">Thông báo phương án:</strong> Thông báo kết quả, thời gian, quyền lợi cho khách.</li>
            <li><strong className="text-slate-800">Hoàn tất xử lý:</strong> Cập nhật trạng thái và lưu hồ sơ giao dịch.</li>
          </ol>
        </div>
      ),
    },
    {
      id: 'rw-13',
      number: '13',
      title: 'Cam kết thời gian xử lý',
      icon: <Clock className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Nhóm sản phẩm', 'Thời gian xử lý dự kiến']}
            rows={[
              ['Điện thoại, tablet, tivi, gia dụng', '07–14 ngày làm việc'],
              ['Laptop, PC, MacBook', '07–21 ngày làm việc'],
              ['Phụ kiện', '07–10 ngày làm việc'],
              ['Sản phẩm cần gửi hãng', 'Theo thời gian phản hồi của hãng'],
            ]}
          />
          <p>Nếu quá 15 ngày làm việc chưa có kết quả, ElectroMart có thể hỗ trợ máy mượn tạm (nếu còn). Nếu sản phẩm không thể sửa chữa: Đổi mới/tương đương, hoặc hoàn tiền theo tỷ lệ khấu hao.</p>
          <div className="rounded border border-fuchsia-200 bg-fuchsia-50 p-3 text-fuchsia-800">
            <strong>Hoàn tiền khi không thể sửa chữa:</strong> Giá trị HĐ × [100% - (5% × số tháng đã sử dụng)]
          </div>
        </div>
      ),
    },
    {
      id: 'rw-14',
      number: '14',
      title: 'Chính sách bảo hành mở rộng',
      icon: <ShieldAlert className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Tên gói', 'Đối tượng', 'Mục đích']}
            rows={[
              ['1 đổi 1 VIP', 'Điện thoại, tablet, laptop, smartwatch...', 'Đổi sản phẩm tương đương khi lỗi phần cứng'],
              ['Rơi vỡ – rơi nước', 'Điện thoại, tablet', 'Hỗ trợ chi phí sửa chữa khi rơi vỡ, vào nước'],
              ['Mở rộng S24+', 'Điện thoại mới, MacBook, phụ kiện cao cấp', 'Gia hạn bảo hành sau khi hết hạn hãng'],
            ]}
          />
        </div>
      ),
    },
    {
      id: 'rw-15',
      number: '15',
      title: 'Gói bảo hành 1 đổi 1 VIP',
      icon: <RefreshCw className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList items={[
            'Được đổi sản phẩm tương đương nếu lỗi phần cứng do nhà sản xuất.',
            'Không giới hạn số lần bảo hành trong thời gian hiệu lực (miễn đủ điều kiện).',
            'Sản phẩm đổi có thể là cùng loại, cùng cấu hình hoặc tương đương.',
            'Có thể chuyển nhượng gói cùng sản phẩm.',
            'Thời gian xử lý từ 24h đến 14 ngày làm việc.',
          ]} />
        </div>
      ),
    },
    {
      id: 'rw-16',
      number: '16',
      title: 'Gói bảo hành rơi vỡ – rơi nước',
      icon: <Smartphone className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList items={[
            'Hỗ trợ tối đa 90% chi phí sửa chữa khi sản phẩm rơi vỡ, vào nước.',
            'Không giới hạn số lần hỗ trợ (tổng chi phí không vượt giá trị giới hạn).',
            'Nếu không thể sửa chữa, có thể đổi sản phẩm tương đương hoặc nhập lại nâng cấp.',
            'Sản phẩm phải chưa bị sửa chữa ngoài hệ thống.',
            'Thời gian sửa chữa: 07-14 ngày làm việc.',
          ]} />
        </div>
      ),
    },
    {
      id: 'rw-17',
      number: '17',
      title: 'Gói bảo hành mở rộng S24+',
      icon: <ShieldCheck className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList items={[
            'Gia hạn bảo hành (đối với lỗi nhà sản xuất) sau khi hết bảo hành chính hãng.',
            'Miễn phí chi phí sửa chữa và thay thế linh kiện thuộc phạm vi.',
            'Không áp dụng cho máy bị rơi vỡ, vào nước, cháy nổ, biến dạng.',
            'Thời gian xử lý: 07-14 ngày làm việc (MacBook có thể 3-4 tuần).',
          ]} />
        </div>
      ),
    },
    {
      id: 'rw-18',
      number: '18',
      title: 'Hoàn trả gói bảo hành mở rộng',
      icon: <DollarSign className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Khách hàng có thể yêu cầu hoàn trả trong vòng <strong>07 ngày</strong> kể từ ngày mua, với điều kiện: Chưa phát sinh yêu cầu bảo hành, chưa sử dụng gói để đổi/sửa chữa.</p>
          <div className="rounded border border-fuchsia-200 bg-fuchsia-50 p-3 text-fuchsia-800 font-semibold">
            Giá trị hoàn trả = Giá trị gói bảo hành × 50%
          </div>
          <p>Sau 07 ngày hoặc đã phát sinh quyền lợi, không áp dụng hoàn trả.</p>
        </div>
      ),
    },
    {
      id: 'rw-19',
      number: '19',
      title: 'Hỗ trợ sao lưu và chuyển dữ liệu',
      icon: <Database className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Khách hàng là chủ sở hữu dữ liệu, có trách nhiệm tự sao lưu trước khi bảo hành, sửa chữa. ElectroMart hỗ trợ hướng dẫn trong các trường hợp:</p>
          <BulletList items={[
            'Hướng dẫn chuyển dữ liệu từ máy cũ sang máy mới.',
            'Hướng dẫn sao lưu ra USB, thẻ nhớ, ổ cứng, máy tính cá nhân.',
            'Hướng dẫn đăng xuất tài khoản và xóa dữ liệu trước khi gửi bảo hành/nhập lại.',
          ]} />
        </div>
      ),
    },
    {
      id: 'rw-20',
      number: '20',
      title: 'Trường hợp nhân viên hỗ trợ trực tiếp',
      icon: <HelpCircle className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Nhân viên chỉ thao tác trực tiếp khi:</p>
          <BulletList items={[
            'Khách hàng đã hiểu rủi ro và đồng ý cho nhân viên thao tác.',
            'Khách hàng ký xác nhận cam kết miễn trừ trách nhiệm dữ liệu.',
            'Khách hàng có mặt trực tiếp trong quá trình thao tác.',
            'Dữ liệu chỉ chuyển sang thiết bị/tài khoản sở hữu của khách.',
          ]} />
          <Note>Nhân viên KHÔNG được yêu cầu khách hàng cung cấp mật khẩu, OTP, thông tin thẻ/ví điện tử.</Note>
        </div>
      ),
    },
    {
      id: 'rw-21',
      number: '21',
      title: 'Cam kết miễn trừ trách nhiệm về dữ liệu',
      icon: <FileWarning className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Khi yêu cầu hỗ trợ và bàn giao thiết bị, khách hàng xác nhận:</p>
          <BulletList items={[
            'Tự chịu rủi ro đối với dữ liệu trong quá trình thao tác.',
            'Miễn trừ trách nhiệm cho ElectroMart, nhân viên và đối tác kỹ thuật đối với rủi ro mất/lỗi dữ liệu (trừ khi chứng minh được nhân viên cố ý sao chép, tiết lộ trái phép).',
          ]} />
        </div>
      ),
    },
    {
      id: 'rw-22',
      number: '22',
      title: 'Trách nhiệm của khách hàng',
      icon: <AlertTriangle className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList items={[
            'Cung cấp thông tin mua hàng, hóa đơn hợp lệ.',
            'Bảo quản sản phẩm, hộp, phụ kiện trong thời gian yêu cầu xử lý.',
            'Tự sao lưu dữ liệu, đăng xuất tài khoản bảo mật trước khi bàn giao.',
            'Cung cấp thông tin trung thực về tình trạng sản phẩm.',
            'Thanh toán chi phí phát sinh nếu lỗi không thuộc diện bảo hành miễn phí.',
          ]} />
        </div>
      ),
    },
    {
      id: 'rw-23',
      number: '23',
      title: 'Trách nhiệm của ElectroMart Việt Nam',
      icon: <ShieldCheck className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList items={[
            'Tiếp nhận yêu cầu khách quan, minh bạch, có căn cứ.',
            'Thông báo rõ kết quả, phương án và thời gian xử lý.',
            'Phối hợp hãng hoặc đơn vị kỹ thuật liên kết.',
            'Bảo mật thông tin khách hàng, lưu trữ hồ sơ giao dịch.',
            'Áp dụng phương án khắc phục phù hợp nếu lỗi từ ElectroMart.',
          ]} />
        </div>
      ),
    },
    {
      id: 'rw-24',
      number: '24',
      title: 'Lưu trữ dữ liệu bảo hành, hỗ trợ',
      icon: <HardDrive className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Trường dữ liệu', 'Nội dung']}
            rows={[
              ['Mã yêu cầu / Mã ĐH', 'Định danh yêu cầu và đơn hàng liên quan'],
              ['IMEI / Serial', 'Mã định danh sản phẩm'],
              ['Tình trạng / Lỗi', 'Loại A, B, C... và lỗi khách phản ánh / kỹ thuật ghi nhận'],
              ['Phương án / Trạng thái', 'Đổi, sửa, từ chối... & Tiếp nhận, gửi hãng, hoàn tất...'],
            ]}
          />
        </div>
      ),
    },
    {
      id: 'rw-25',
      number: '25',
      title: 'Điều khoản áp dụng',
      icon: <FileText className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Chính sách có thể điều chỉnh tùy yêu cầu vận hành, nhà sản xuất hoặc pháp luật. Mọi thay đổi quan trọng sẽ được công bố trên website. Khách hàng tiếp tục sử dụng dịch vụ đồng nghĩa với việc đồng ý với sửa đổi.</p>
        </div>
      ),
    },
    {
      id: 'rw-26',
      number: '26',
      title: 'Kết luận',
      icon: <ShieldAlert className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Chính sách bảo hành, đổi trả và hỗ trợ kỹ thuật được xây dựng để chuẩn hóa quy trình hậu mãi, bao gồm: đổi mới sản phẩm, nhập lại, bảo hành tiêu chuẩn/mở rộng và hỗ trợ dữ liệu.</p>
          <div className="rounded-lg border border-fuchsia-200 bg-fuchsia-50 px-4 py-3 text-fuchsia-800">
            <p className="text-sm font-semibold">
              Việc minh bạch các quy định giúp hạn chế tranh chấp và nâng cao độ tin cậy khi mua sắm tại ElectroMart Việt Nam.
            </p>
          </div>
        </div>
      ),
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Banner */}
      <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-fuchsia-900/60">
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage:
              'radial-gradient(circle at 20% 60%, #d946ef 0%, transparent 50%), radial-gradient(circle at 80% 20%, #e879f9 0%, transparent 40%)',
          }}
        />
        <div className="relative mx-auto max-w-5xl px-4 py-12 lg:px-6">
          {/* Breadcrumb */}
          <nav className="mb-5 flex items-center gap-1.5 text-xs text-slate-400">
            <Link to="/" className="transition hover:text-white">Trang chủ</Link>
            <span>/</span>
            <Link to="/about" className="transition hover:text-white">Giới thiệu công ty</Link>
            <span>/</span>
            <span className="text-slate-200">Bảo hành &amp; Kỹ thuật</span>
          </nav>

          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-fuchsia-500 shadow-lg shadow-fuchsia-500/30">
              <ShieldAlert className="h-6 w-6 text-white" />
            </div>
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-fuchsia-400">Chính sách</p>
              <h1 className="text-2xl font-bold font-display leading-tight text-white lg:text-3xl">
                Bảo hành, Đổi trả &amp; Hỗ trợ kỹ thuật
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-300">
                Toàn bộ quy định về đổi mới, nhập lại thiết bị, bảo hành tiêu chuẩn/mở rộng, hỗ trợ sao lưu dữ liệu và quy trình kỹ thuật nhằm bảo vệ quyền lợi tối đa cho khách hàng.
              </p>
            </div>
          </div>

          {/* Quick stats */}
          <div className="mt-8 grid grid-cols-3 gap-4 border-t border-white/10 pt-6">
            {[
              { label: 'Đổi trả phần cứng', value: 'Lên tới 30 ngày' },
              { label: 'Bảo hành hãng', value: '12 - 36 tháng' },
              { label: 'Điều khoản chi tiết', value: '26' },
            ].map((s) => (
              <div key={s.label} className="text-center">
                <div className="text-2xl font-bold text-fuchsia-400">{s.value}</div>
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
                    ? 'border-fuchsia-200 bg-white shadow-md shadow-fuchsia-500/5'
                    : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm'
                }`}
              >
                <button
                  id={`rw-section-${section.number}`}
                  onClick={() => toggle(section.id)}
                  className="flex w-full items-center gap-4 px-5 py-4 text-left"
                  aria-expanded={isOpen}
                >
                  <div
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors ${
                      isOpen ? 'bg-fuchsia-500 text-white' : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    {section.icon}
                  </div>
                  <div className="flex-1">
                    <div className="mb-0.5">
                      <span className={`text-xs font-bold ${isOpen ? 'text-fuchsia-600' : 'text-slate-400'}`}>
                        Điều {section.number}
                      </span>
                    </div>
                    <div className={`text-sm font-semibold leading-tight ${isOpen ? 'text-fuchsia-700' : 'text-slate-800'}`}>
                      {section.title}
                    </div>
                  </div>
                  <div className={`shrink-0 transition-colors ${isOpen ? 'text-fuchsia-600' : 'text-slate-400'}`}>
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
            to="/purchase-policy"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
          >
            Chính sách mua hàng & thanh toán
          </Link>
          <Link
            to="/delivery-policy"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
          >
            Chính sách giao nhận hàng
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
