import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ChevronDown, ChevronUp, ShieldCheck, Clock, Package,
  CreditCard, AlertTriangle, Database, ArrowRight, RefreshCw, Wrench, FileText,
} from 'lucide-react';

interface Section {
  id: string;
  number: string;
  title: string;
  icon: React.ReactNode;
  content: React.ReactNode;
}

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
            <tr key={i} className="hover:bg-slate-50/60 transition-colors">
              {row.map((cell, j) => (
                <td key={j} className={`px-4 py-2.5 text-slate-600 leading-relaxed ${j === 0 ? 'font-semibold text-slate-700 whitespace-nowrap' : ''}`}>
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
      <div>{children}</div>
    </div>
  );
}

export default function WarrantyPage() {
  const [expandedSection, setExpandedSection] = useState<string | null>('w-1');

  const toggle = (id: string) => setExpandedSection((p) => (p === id ? null : id));

  const sections: Section[] = [
    {
      id: 'w-1',
      number: '1',
      title: 'Mức khấu trừ khi nhập lại sản phẩm',
      icon: <RefreshCw className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <p>
            ElectroMart Việt Nam áp dụng công thức khấu trừ thống nhất thay cho hình thức "thỏa thuận" không định lượng, đảm bảo minh bạch trong quá trình nhập lại sản phẩm.
          </p>
          <div className="rounded-lg border border-primary/20 bg-primary/5 px-4 py-3">
            <p className="text-sm font-semibold text-slate-800">Công thức hoàn trả:</p>
            <p className="mt-1 text-sm text-slate-700">
              <span className="font-bold text-primary">Giá trị hoàn trả</span> = Giá trị hóa đơn hợp lệ × Tỷ lệ hoàn trả còn lại
            </p>
          </div>
          <Table
            headers={['Thời gian sử dụng', 'Tỷ lệ khấu trừ', 'Tỷ lệ hoàn trả còn lại']}
            rows={[
              ['Trong 30 ngày đầu', '20%', '80%'],
              ['Từ tháng thứ 2', '25%', '75%'],
              ['Từ tháng thứ 3', '30%', '70%'],
              ['Từ tháng thứ 4', '35%', '65%'],
              ['Từ tháng thứ 5', '40%', '60%'],
              ['Từ tháng thứ 6 trở đi', 'Tăng thêm 5%/tháng', 'Theo tỷ lệ còn lại sau khấu trừ'],
            ]}
          />
          <Note>
            <span className="font-semibold">Ví dụ:</span> Sản phẩm giá 10.000.000đ — nhập lại trong 30 ngày: hoàn <strong>8.000.000đ</strong> (khấu trừ 20%); nhập lại tháng 3: hoàn <strong>7.000.000đ</strong> (khấu trừ 30%).
          </Note>
          <p>
            Mức khấu trừ tối đa không vượt quá <strong>70% giá trị hóa đơn</strong>. Sau khi đạt mức tối đa, hệ thống chỉ tiếp nhận bảo hành, sửa chữa hoặc hỗ trợ nâng cấp — không áp dụng hoàn tiền mặc định.
          </p>
        </div>
      ),
    },
    {
      id: 'w-2',
      number: '2',
      title: 'Mốc thời gian bắt đầu bảo hành & đổi trả',
      icon: <Clock className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Hình thức mua hàng', 'Thời điểm bắt đầu tính']}
            rows={[
              ['Mua trực tiếp tại cửa hàng', 'Ngày in hóa đơn hoặc ngày hệ thống ghi nhận giao dịch hoàn tất'],
              ['Mua trực tuyến – giao tận nơi', 'Ngày hệ thống vận chuyển cập nhật trạng thái "Giao hàng thành công"'],
              ['Đặt trực tuyến – nhận tại cửa hàng', 'Ngày khách hàng ký nhận sản phẩm tại cửa hàng'],
            ]}
          />
          <p>
            Trong trường hợp hệ thống không ghi nhận được trạng thái giao hàng do lỗi kỹ thuật, ElectroMart Việt Nam căn cứ vào: biên bản bàn giao, xác nhận đơn vị vận chuyển, tin nhắn xác nhận giao hàng hoặc lịch sử cập nhật trên hệ thống nội bộ.
          </p>
        </div>
      ),
    },
    {
      id: 'w-3',
      number: '3',
      title: 'Khấu trừ hộp, phụ kiện và quà tặng khi đổi trả',
      icon: <Package className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <p>
            Sản phẩm đổi trả cần được hoàn trả kèm đầy đủ hộp, phụ kiện, quà tặng và chứng từ theo tình trạng ban đầu. Trường hợp thiếu, áp dụng khấu trừ như sau:
          </p>
          <Table
            headers={['Thành phần thiếu / hư hỏng', 'Căn cứ khấu trừ']}
            rows={[
              ['Phụ kiện có bán lẻ trên hệ thống', 'Theo giá bán lẻ niêm yết tại thời điểm đổi trả'],
              ['Hộp sản phẩm', 'Theo phí đóng gói/thay thế được hệ thống quy định cho từng nhóm sản phẩm'],
              ['Quà tặng có giá bán lẻ', 'Theo giá bán lẻ niêm yết tại thời điểm đổi trả'],
              ['Quà tặng không có giá bán lẻ', 'Theo giá trị quy đổi ghi nhận trên hệ thống tại thời điểm mua'],
              ['Phụ kiện / quà tặng bị hư hỏng', 'Theo giá trị thay thế hoặc giá trị quy đổi tương ứng'],
            ]}
          />
          <Note>
            Nếu khách hàng không đồng ý với mức khấu trừ, ElectroMart Việt Nam có quyền từ chối nhập lại và chuyển sang phương án bảo hành/sửa chữa.
          </Note>
        </div>
      ),
    },
    {
      id: 'w-4',
      number: '4',
      title: 'Thời gian xử lý bảo hành và phương án hỗ trợ',
      icon: <Wrench className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <p>
            Thời gian xử lý bảo hành dự kiến từ <strong>07 đến 14 ngày làm việc</strong> tùy nhóm sản phẩm, tình trạng lỗi và khả năng cung ứng linh kiện.
          </p>
          <p>
            Nếu quá <strong>15 ngày làm việc</strong> kể từ ngày tiếp nhận hợp lệ mà chưa có kết quả, khách hàng được hỗ trợ theo thứ tự ưu tiên:
          </p>
          <ol className="list-decimal pl-5 space-y-1.5">
            <li>Mượn thiết bị thay thế chức năng tương đương (nếu hệ thống còn thiết bị dự phòng).</li>
            <li>Thông báo rõ lý do chậm, tình trạng linh kiện và thời gian dự kiến hoàn tất.</li>
            <li>Nếu sản phẩm không thể sửa chữa, áp dụng phương án xử lý cuối cùng:</li>
          </ol>
          <Table
            headers={['Tình huống', 'Phương án áp dụng']}
            rows={[
              ['Còn sản phẩm cùng loại', 'Đổi sản phẩm mới hoặc tương đương theo chính sách bảo hành'],
              ['Không còn sản phẩm cùng loại', 'Đổi sản phẩm khác giá trị tương đương/cao hơn; khách thanh toán chênh lệch nếu có'],
              ['Khách không chọn sản phẩm thay thế', 'Hoàn tiền theo tỷ lệ khấu hao dựa trên thời gian sử dụng'],
              ['Sản phẩm thuộc diện bảo hành hãng', 'Theo kết quả và quy định cuối cùng của hãng sản xuất'],
            ]}
          />
          <div className="rounded-lg border border-primary/20 bg-primary/5 px-4 py-3">
            <p className="text-sm font-semibold text-slate-800">Công thức hoàn tiền khi sản phẩm không thể sửa chữa:</p>
            <p className="mt-1 text-sm text-slate-700">
              <span className="font-bold text-primary">Giá trị hoàn tiền</span> = Giá trị hóa đơn × [100% – 5% × số tháng đã sử dụng]
            </p>
            <p className="mt-1 text-xs text-slate-500">Số tháng làm tròn lên. Mức hoàn tiền tối thiểu không thấp hơn 30% giá trị hóa đơn hợp lệ.</p>
          </div>
        </div>
      ),
    },
    {
      id: 'w-5',
      number: '5',
      title: 'Hóa đơn VAT khi đổi trả và hoàn tiền',
      icon: <FileText className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <p>
            Giao dịch có xuất hóa đơn VAT chỉ được xử lý đổi trả/hoàn tiền sau khi hoàn tất thủ tục theo quy định pháp luật về thuế và kế toán.
          </p>
          <p>Đối với khách hàng doanh nghiệp, cần cung cấp một trong các chứng từ sau:</p>
          <Table
            headers={['Trường hợp', 'Chứng từ cần cung cấp']}
            rows={[
              ['Trả lại toàn bộ sản phẩm', 'Biên bản trả hàng và thu hồi hóa đơn'],
              ['Trả lại một phần sản phẩm', 'Biên bản điều chỉnh giảm giá trị hóa đơn'],
              ['Đổi sang sản phẩm khác', 'Biên bản điều chỉnh hoặc hóa đơn thay thế theo quy định'],
              ['Hoàn tiền qua chuyển khoản', 'Thông tin tài khoản nhận tiền hợp lệ của cá nhân/doanh nghiệp mua hàng'],
            ]}
          />
          <Note>
            Nếu thiếu chứng từ, ElectroMart Việt Nam có quyền tạm hoãn hoàn tiền. Chi phí xử lý hóa đơn phát sinh do thiếu chứng từ từ phía khách có thể được khấu trừ vào số tiền hoàn trả.
          </Note>
        </div>
      ),
    },
    {
      id: 'w-6',
      number: '6',
      title: 'Xác định lỗi sản phẩm',
      icon: <AlertTriangle className="h-5 w-5" />,
      content: (
        <div className="space-y-5 text-sm text-slate-600 leading-relaxed">
          <div className="space-y-3">
            <h4 className="text-sm font-bold text-slate-800">6.1. Lỗi do nhà sản xuất</h4>
            <p>Lỗi phát sinh trong điều kiện sử dụng bình thường, không có dấu hiệu tác động từ bên ngoài và được xác nhận bởi bộ phận kỹ thuật hoặc trung tâm bảo hành được ủy quyền.</p>
            <Table
              headers={['Nhóm lỗi', 'Ví dụ']}
              rows={[
                ['Lỗi nguồn', 'Không lên nguồn, sập nguồn bất thường'],
                ['Lỗi mainboard', 'Không nhận linh kiện, lỗi xử lý hệ thống'],
                ['Lỗi màn hình', 'Sọc màn hình, điểm chết vượt ngưỡng quy định'],
                ['Lỗi âm thanh', 'Không nhận loa, mic, tai nghe trong điều kiện bình thường'],
                ['Lỗi kết nối', 'Không nhận Wi-Fi, Bluetooth, SIM, cổng kết nối do lỗi kỹ thuật'],
                ['Lỗi linh kiện bên trong', 'Camera, cảm biến, ổ cứng, RAM hoặc linh kiện tích hợp bị lỗi kỹ thuật'],
              ]}
            />
            <Note>
              <strong>Điểm chết màn hình:</strong> Điện thoại/máy tính bảng bảo hành khi có ≥3 điểm chết hoặc 1 điểm chết &gt;1mm. Laptop/màn hình rời bảo hành khi có ≥5 điểm chết, trừ khi hãng có quy định khác.
            </Note>
          </div>
          <div className="space-y-3">
            <h4 className="text-sm font-bold text-slate-800">6.2. Lỗi do người dùng (không được bảo hành miễn phí)</h4>
            <ul className="list-disc pl-5 space-y-1.5">
              <li>Rơi, vỡ, cấn móp, cong vênh, nứt, gãy hoặc biến dạng.</li>
              <li>Vào nước, ẩm mốc, oxy hóa, cháy nổ, chập điện hoặc tiếp xúc hóa chất.</li>
              <li>Dùng sai nguồn điện, sai phụ kiện, sạc không đúng chuẩn hoặc lắp đặt sai hướng dẫn.</li>
              <li>Bị côn trùng, động vật hoặc yếu tố môi trường gây hư hỏng.</li>
              <li>Tự ý tháo mở, sửa chữa, thay linh kiện, can thiệp phần mềm hoặc thay đổi cấu trúc.</li>
              <li>Mất, rách, tẩy xóa hoặc thay đổi tem bảo hành, số serial, IMEI hoặc mã định danh.</li>
            </ul>
          </div>
        </div>
      ),
    },
    {
      id: 'w-7',
      number: '7',
      title: 'Quy định hoàn tiền',
      icon: <CreditCard className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <p>
            Hoàn tiền được thực hiện sau khi sản phẩm đủ điều kiện nhập lại và hoàn tất thủ tục hóa đơn, chứng từ, dữ liệu đơn hàng.
          </p>
          <Table
            headers={['Hình thức thanh toán ban đầu', 'Hình thức hoàn tiền']}
            rows={[
              ['Tiền mặt', 'Hoàn tiền mặt hoặc chuyển khoản'],
              ['Chuyển khoản ngân hàng', 'Hoàn về tài khoản đã thanh toán hoặc tài khoản hợp lệ của người mua'],
              ['Ví điện tử', 'Hoàn về ví điện tử hoặc chuyển khoản theo điều kiện cổng thanh toán'],
              ['Thanh toán online', 'Hoàn qua cổng thanh toán hoặc chuyển khoản theo trạng thái giao dịch'],
              ['Trả góp', 'Xử lý theo quy định của đơn vị tài chính liên kết'],
            ]}
          />
          <Note>
            Đối với đơn hàng trả góp, khách cần làm việc thêm với công ty tài chính/ngân hàng phát hành. ElectroMart Việt Nam chỉ hoàn phần giá trị sản phẩm sau khi trừ các khoản phí phát sinh (nếu có).
          </Note>
        </div>
      ),
    },
    {
      id: 'w-8',
      number: '8',
      title: 'Trạng thái sản phẩm khi nhập lại',
      icon: <ShieldCheck className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Trạng thái', 'Mô tả', 'Hướng xử lý']}
            rows={[
              ['Loại A', 'Như mới, đầy đủ hộp & phụ kiện, không trầy xước', 'Áp dụng mức khấu trừ chuẩn'],
              ['Loại B', 'Có trầy xước nhẹ, đầy đủ chức năng', 'Khấu trừ thêm 5%–10% tùy tình trạng'],
              ['Loại C', 'Cấn móp, trầy xước rõ nhưng còn hoạt động', 'Khấu trừ thêm 10%–20% hoặc từ chối nhập lại'],
              ['Loại D', 'Hư hỏng vật lý, vào nước, lỗi do người dùng', 'Không nhập lại; chỉ hỗ trợ sửa chữa có phí'],
              ['Không đủ điều kiện', 'Mất IMEI/Serial, khóa tài khoản, nghi ngờ can thiệp', 'Từ chối nhập lại và chuyển sang kiểm tra kỹ thuật'],
            ]}
          />
          <p>
            Việc phân loại do nhân viên kỹ thuật hoặc bộ phận tiếp nhận bảo hành thực hiện. Kết quả cần được ghi nhận trên hệ thống để làm căn cứ xử lý đơn hàng.
          </p>
        </div>
      ),
    },
    {
      id: 'w-9',
      number: '9',
      title: 'Tài khoản cá nhân và khóa bảo mật',
      icon: <ShieldCheck className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <p>
            Trước khi gửi sản phẩm bảo hành, đổi trả hoặc nhập lại, khách hàng có trách nhiệm đăng xuất toàn bộ tài khoản và tắt các tính năng khóa bảo mật trên thiết bị.
          </p>
          <Table
            headers={['Loại thiết bị', 'Tài khoản cần đăng xuất']}
            rows={[
              ['iPhone, iPad, MacBook, Apple Watch', 'iCloud, Apple ID, Find My'],
              ['Android', 'Google Account, Samsung/Mi/OPPO/vivo Account'],
              ['Laptop Windows', 'Microsoft Account, BitLocker, mật khẩu đăng nhập'],
              ['Thiết bị thông minh', 'Tài khoản ứng dụng điều khiển, tài khoản nhà thông minh'],
            ]}
          />
          <Note>
            Nếu thiết bị đang bị khóa bảo mật hoặc khách không đăng xuất được, ElectroMart Việt Nam có quyền từ chối tiếp nhận đổi trả/nhập lại cho đến khi khách hoàn tất mở khóa hợp lệ.
          </Note>
        </div>
      ),
    },
    {
      id: 'w-10',
      number: '10',
      title: 'Điều khoản áp dụng trong hệ thống',
      icon: <Database className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <p>
            Các chính sách đổi trả, nhập lại, hoàn tiền và bảo hành được mã hóa thành các trường dữ liệu cụ thể để triển khai trên hệ thống phần mềm:
          </p>
          <Table
            headers={['Trường dữ liệu', 'Ý nghĩa']}
            rows={[
              ['Ngày bắt đầu bảo hành', 'Ngày in hóa đơn, ngày giao hàng thành công hoặc ngày khách ký nhận'],
              ['Nhóm sản phẩm', 'Xác định thời hạn đổi mới và bảo hành'],
              ['Tình trạng sản phẩm', 'Loại A, B, C, D hoặc không đủ điều kiện'],
              ['Tỷ lệ khấu trừ', 'Tự động tính theo thời gian sử dụng'],
              ['Giá trị phụ kiện thiếu', 'Tự động lấy theo bảng giá niêm yết hoặc giá trị quy đổi'],
              ['Trạng thái hóa đơn VAT', 'Chưa xử lý / Đã thu hồi / Đã điều chỉnh / Đã hủy'],
              ['Trạng thái bảo hành', 'Tiếp nhận / Đang kiểm tra / Gửi hãng / Chờ linh kiện / Hoàn tất / Từ chối'],
              ['SLA bảo hành', 'Số ngày làm việc kể từ ngày tiếp nhận hợp lệ'],
              ['Phương án xử lý cuối cùng', 'Sửa chữa / Đổi mới / Nhập lại / Hoàn tiền / Từ chối bảo hành'],
            ]}
          />
          <p>
            Việc chuẩn hóa các trường dữ liệu này giúp ElectroMart Việt Nam hạn chế lỗi logic trong quá trình vận hành, đồng thời tạo cơ sở để xây dựng chức năng quản lý bảo hành, đổi trả và hoàn tiền rõ ràng, nhất quán và có thể kiểm soát.
          </p>
        </div>
      ),
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Banner */}
      <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-700">
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage:
              'radial-gradient(circle at 15% 60%, #3b82f6 0%, transparent 50%), radial-gradient(circle at 85% 20%, #10b981 0%, transparent 40%)',
          }}
        />
        <div className="relative mx-auto max-w-5xl px-4 py-12 lg:px-6">
          {/* Breadcrumb */}
          <nav className="mb-5 flex items-center gap-1.5 text-xs text-slate-400">
            <Link to="/" className="transition hover:text-white">Trang chủ</Link>
            <span>/</span>
            <Link to="/about" className="transition hover:text-white">Giới thiệu công ty</Link>
            <span>/</span>
            <span className="text-slate-200">Chính sách bảo hành &amp; đổi trả</span>
          </nav>

          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-blue-600 shadow-lg shadow-blue-500/30">
              <ShieldCheck className="h-6 w-6 text-white" />
            </div>
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-blue-400">Chính sách</p>
              <h1 className="text-2xl font-bold leading-tight text-white font-display lg:text-3xl">
                Chính sách bảo hành &amp; đổi trả
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-300">
                Quy định minh bạch về bảo hành, đổi trả và hoàn tiền của ElectroMart Việt Nam — được xây dựng nhằm bảo vệ quyền lợi khách hàng và đảm bảo vận hành hệ thống nhất quán.
              </p>
            </div>
          </div>

          {/* Quick stats */}
          <div className="mt-8 grid grid-cols-3 gap-4 border-t border-white/10 pt-6">
            {[
              { label: 'Thời gian đổi mới', value: '30 ngày' },
              { label: 'Xử lý bảo hành', value: '7–14 ngày' },
              { label: 'Hoàn tiền tối thiểu', value: '30%' },
            ].map((s) => (
              <div key={s.label} className="text-center">
                <div className="text-2xl font-bold text-blue-400">{s.value}</div>
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
            const isOpen = expandedSection === section.id;
            return (
              <div
                key={section.id}
                className={`overflow-hidden rounded-xl border transition-all duration-200 ${
                  isOpen
                    ? 'border-blue-200 bg-white shadow-md shadow-blue-500/5'
                    : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm'
                }`}
              >
                <button
                  id={`warranty-section-${section.number}`}
                  onClick={() => toggle(section.id)}
                  className="flex w-full items-center gap-4 px-5 py-4 text-left"
                  aria-expanded={isOpen}
                >
                  <div
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors ${
                      isOpen ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    {section.icon}
                  </div>
                  <div className="flex-1">
                    <div className="mb-0.5">
                      <span className={`text-xs font-bold ${isOpen ? 'text-blue-600' : 'text-slate-400'}`}>
                        Điều {section.number}
                      </span>
                    </div>
                    <div className={`text-sm font-semibold leading-tight ${isOpen ? 'text-blue-700' : 'text-slate-800'}`}>
                      {section.title}
                    </div>
                  </div>
                  <div className={`shrink-0 transition-colors ${isOpen ? 'text-blue-600' : 'text-slate-400'}`}>
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

        {/* Back to about */}
        <div className="mt-10 flex flex-col gap-3 sm:flex-row">
          <Link
            to="/about"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
          >
            ← Về trang giới thiệu công ty
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
