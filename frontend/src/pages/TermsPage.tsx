import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ChevronDown, ChevronUp, Scale, Settings, CheckCircle, ShoppingCart, 
  Tag, CreditCard, User, Users, ShieldCheck, XOctagon, AlertTriangle, 
  MessageSquare, BookOpen, Database, FileText, Repeat, LayoutDashboard,
  ArrowRight
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
          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500" />
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

export default function TermsPage() {
  const [expanded, setExpanded] = useState<string | null>('t-1');
  const toggle = (id: string) => setExpanded((p) => (p === id ? null : id));

  const sections: Section[] = [
    {
      id: 't-1',
      number: '1',
      title: 'Quy định chung',
      icon: <Scale className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Quy chế hoạt động website ElectroMart Việt Nam được xây dựng nhằm quy định nguyên tắc vận hành, quy trình giao dịch, quyền và nghĩa vụ của khách hàng, quyền và trách nhiệm của Ban quản trị hệ thống, cũng như các quy định liên quan đến việc sử dụng website.</p>
          <p>Website là nền tảng thương mại điện tử chuyên cung cấp sản phẩm điện tử, thiết bị công nghệ, phụ kiện và dịch vụ hỗ trợ. Hệ thống phục vụ nhu cầu tìm kiếm, đặt hàng, thanh toán, theo dõi đơn hàng, bảo hành, đổi trả và CSKH.</p>
          <Note>Khi truy cập, đăng ký tài khoản hoặc sử dụng chức năng trên website, khách hàng được hiểu là đã đọc, hiểu và đồng ý tuân thủ các nội dung được quy định trong Quy chế này.</Note>
        </div>
      ),
    },
    {
      id: 't-2',
      number: '2',
      title: 'Nguyên tắc hoạt động',
      icon: <Settings className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <div className="mb-4 rounded-xl overflow-hidden border border-slate-100 shadow-sm max-w-md mx-auto bg-slate-50">
            <img src="/images/policies/terms.png" alt="Nguyên tắc hoạt động" className="w-full h-auto mix-blend-multiply" />
          </div>
          <BulletList items={[
            'Hoạt động dựa trên nguyên tắc công khai, minh bạch, trung thực và tuân thủ pháp luật.',
            'Các thông tin về sản phẩm, giá bán, khuyến mãi, chính sách được công bố rõ ràng nhằm hỗ trợ khách hàng quyết định.',
            'ElectroMart có trách nhiệm duy trì hoạt động trong khả năng kỹ thuật. Trong trường hợp bảo trì/sự cố, có thể gián đoạn chức năng và sẽ thông báo nếu cần.',
            'Khách hàng có trách nhiệm cung cấp thông tin chính xác, sử dụng đúng mục đích, không gian lận, phá hoại hay xâm nhập trái phép.',
          ]} />
        </div>
      ),
    },
    {
      id: 't-3',
      number: '3',
      title: 'Phạm vi cung cấp dịch vụ',
      icon: <LayoutDashboard className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Nhóm chức năng', 'Nội dung']}
            rows={[
              ['Tra cứu sản phẩm', 'Tìm kiếm, lọc, xem chi tiết, so sánh sản phẩm'],
              ['Tài khoản người dùng', 'Đăng ký, đăng nhập, cập nhật thông tin, quản lý địa chỉ'],
              ['Giỏ hàng và đặt hàng', 'Thêm sản phẩm, đặt hàng, áp dụng mã giảm giá'],
              ['Thanh toán', 'Hỗ trợ các phương thức thanh toán được công bố'],
              ['Quản lý đơn hàng', 'Theo dõi trạng thái, hủy đơn nếu đủ điều kiện'],
              ['Giao nhận', 'Cập nhật trạng thái vận chuyển, xác nhận giao hàng'],
              ['Bảo hành, đổi trả', 'Gửi yêu cầu bảo hành, đổi trả, hỗ trợ kỹ thuật'],
              ['Đánh giá sản phẩm', 'Đánh giá, bình luận và phản hồi (nếu hỗ trợ)'],
              ['Chăm sóc khách hàng', 'Gửi yêu cầu hỗ trợ, khiếu nại, góp ý, tư vấn'],
            ]}
          />
        </div>
      ),
    },
    {
      id: 't-4',
      number: '4',
      title: 'Quy trình giao dịch trên website',
      icon: <ShoppingCart className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <ol className="list-decimal pl-5 space-y-2">
            <li><strong className="text-slate-800">Tìm kiếm và lựa chọn:</strong> Xem thông tin, giá, bảo hành, khuyến mãi.</li>
            <li><strong className="text-slate-800">Thêm vào giỏ:</strong> Kiểm tra số lượng, giá, phí ship.</li>
            <li><strong className="text-slate-800">Cung cấp thông tin:</strong> Tên, SĐT, địa chỉ, phương thức thanh toán, ghi chú.</li>
            <li><strong className="text-slate-800">Xác nhận đơn hàng:</strong> Nhận thông báo xác nhận qua email/SMS.</li>
            <li><strong className="text-slate-800">Xử lý đơn hàng:</strong> Kiểm tra, đóng gói, bàn giao ĐVVC.</li>
            <li><strong className="text-slate-800">Giao hàng:</strong> Nhận hàng và cập nhật trạng thái thành công.</li>
            <li><strong className="text-slate-800">Hỗ trợ sau bán:</strong> Đổi trả, bảo hành, khiếu nại nếu có.</li>
          </ol>
        </div>
      ),
    },
    {
      id: 't-5',
      number: '5',
      title: 'Chính sách hàng chính hãng & nguồn gốc',
      icon: <CheckCircle className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <p>ElectroMart cam kết cung cấp sản phẩm nguồn gốc rõ ràng, minh bạch:</p>
          <Table
            headers={['Loại sản phẩm', 'Mô tả']}
            rows={[
              ['Hàng mới', 'Chưa qua sử dụng, đầy đủ hộp, phụ kiện, bảo hành'],
              ['Hàng đã kích hoạt', 'Đã kích hoạt bảo hành hãng nhưng còn hạn bảo hành'],
              ['Hàng đã qua sử dụng', 'Sản phẩm cũ, đã được kiểm tra tình trạng trước khi bán'],
              ['Hàng trưng bày', 'Dùng trưng bày, có thể có tình trạng ngoại quan riêng'],
              ['Phụ kiện, linh kiện', 'Sản phẩm đi kèm hoặc linh kiện công nghệ'],
            ]}
          />
          <p className="font-semibold text-amber-800">Cam kết: Không kinh doanh hàng giả, không rõ nguồn gốc, vi phạm sở hữu trí tuệ hoặc hàng cấm kinh doanh.</p>
        </div>
      ),
    },
    {
      id: 't-6',
      number: '6',
      title: 'Thông tin sản phẩm, giá bán, khuyến mãi',
      icon: <Tag className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList items={[
            'Giá bán niêm yết bằng VNĐ, có thể thay đổi theo thời điểm, CTKM.',
            'Nếu có lỗi kỹ thuật dẫn đến hiển thị sai giá/khuyến mãi, ElectroMart có quyền điều chỉnh và thông báo cho khách trước khi xác nhận giao dịch.',
            'Khuyến mãi/Voucher chỉ áp dụng khi đủ điều kiện. Có quyền từ chối nếu phát hiện lợi dụng lỗi hoặc gian lận.',
          ]} />
        </div>
      ),
    },
    {
      id: 't-7',
      number: '7',
      title: 'Quy định đăng ký & quản lý tài khoản',
      icon: <User className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Khách hàng cần cung cấp thông tin chính xác, hợp pháp và tự bảo mật tài khoản/mật khẩu/OTP.</p>
          <Table
            headers={['Trường hợp vi phạm', 'Hướng xử lý']}
            rows={[
              ['Cung cấp thông tin giả mạo', 'Tạm khóa / yêu cầu xác minh bổ sung'],
              ['Dấu hiệu gian lận giao dịch', 'Hạn chế chức năng đặt hàng / khóa tài khoản'],
              ['Lạm dụng voucher, chính sách', 'Từ chối giao dịch / ghi nhận vi phạm'],
              ['Tấn công hệ thống', 'Khóa tài khoản / chuyển cơ quan thẩm quyền'],
              ['Phát tán nội dung vi phạm', 'Xóa nội dung / hạn chế quyền sử dụng'],
            ]}
          />
        </div>
      ),
    },
    {
      id: 't-8',
      number: '8',
      title: 'Quyền và nghĩa vụ của khách hàng',
      icon: <Users className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p className="font-bold text-slate-800">Quyền của khách hàng:</p>
          <BulletList items={[
            'Tham khảo, mua sản phẩm, cập nhật thông tin rõ ràng.',
            'Lựa chọn thanh toán, kiểm tra đơn hàng, bảo hành đổi trả.',
            'Được bảo vệ thông tin cá nhân và khiếu nại dịch vụ.',
          ]} />
          <p className="font-bold text-slate-800 mt-3">Nghĩa vụ của khách hàng:</p>
          <BulletList items={[
            'Cung cấp thông tin chính xác, thanh toán đầy đủ.',
            'Kiểm tra kỹ thông tin trước khi xác nhận đơn.',
            'Bảo mật tài khoản, không phá hoại hệ thống hay trục lợi.',
            'Phối hợp trong quá trình xác minh, xử lý khiếu nại/bảo hành.',
          ]} />
        </div>
      ),
    },
    {
      id: 't-9',
      number: '9',
      title: 'Quyền và trách nhiệm của ElectroMart',
      icon: <ShieldCheck className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p className="font-bold text-slate-800">Quyền của ElectroMart:</p>
          <BulletList items={[
            'Từ chối đơn hàng (hết hàng, sai thông tin, gian lận).',
            'Điều chỉnh thông tin sai sót.',
            'Khóa/hạn chế tài khoản vi phạm, từ chối phục vụ khách hàng gây rối.',
            'Cập nhật Quy chế theo yêu cầu vận hành.',
          ]} />
          <p className="font-bold text-slate-800 mt-3">Trách nhiệm:</p>
          <BulletList items={[
            'Công bố rõ chính sách, minh bạch thông tin.',
            'Tiếp nhận, xử lý đơn hàng, bảo mật dữ liệu.',
            'Phối hợp đối tác xử lý vấn đề, giải quyết khiếu nại thiện chí.',
            'Khắc phục lỗi hệ thống trong khả năng kỹ thuật.',
          ]} />
        </div>
      ),
    },
    {
      id: 't-10',
      number: '10',
      title: 'Quy định về hành vi bị cấm',
      icon: <XOctagon className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList items={[
            'Cung cấp thông tin giả mạo, dùng tài khoản trái phép.',
            'Tạo nhiều tài khoản trục lợi khuyến mãi.',
            'Đặt hàng ảo, bùng hàng nhiều lần.',
            'Tấn công, dò quét, sao chép trái phép dữ liệu/giao diện website.',
            'Đăng bình luận xúc phạm, đe dọa, quảng cáo spam.',
            'Lợi dụng bảo hành, hoàn tiền để trục lợi.',
          ]} />
        </div>
      ),
    },
    {
      id: 't-11',
      number: '11',
      title: 'Hạn chế hoặc từ chối phục vụ',
      icon: <AlertTriangle className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Trường hợp', 'Hướng xử lý']}
            rows={[
              ['Đe dọa, xúc phạm, gây rối', 'Từ chối phục vụ, ghi nhận vi phạm'],
              ['Lợi dụng chính sách trục lợi', 'Hạn chế quyền đổi trả, đặt hàng'],
              ['Bùng hàng nhiều lần', 'Hạn chế đặt hàng online'],
              ['Cung cấp thông tin giả mạo', 'Khóa tài khoản / xác minh'],
              ['Tấn công phá hoại', 'Khóa tài khoản / xử lý pháp luật'],
              ['Yêu cầu ngoài phạm vi KD', 'Từ chối yêu cầu không phù hợp'],
            ]}
          />
        </div>
      ),
    },
    {
      id: 't-12',
      number: '12',
      title: 'Trách nhiệm khi phát sinh lỗi kỹ thuật',
      icon: <Settings className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Hệ thống có thể phát sinh sự cố do phần mềm, máy chủ, bảo trì, mạng. ElectroMart sẽ nỗ lực khắc phục. Nếu lỗi từ bên thứ 3 (cổng thanh toán, ngân hàng, vận chuyển), sẽ phối hợp xử lý.</p>
          <Note>ElectroMart KHÔNG chịu trách nhiệm nếu lỗi từ thiết bị cá nhân, mạng của khách hàng, phần mềm độc hại hoặc hành vi tự ý can thiệp.</Note>
        </div>
      ),
    },
    {
      id: 't-13',
      number: '13',
      title: 'Đánh giá, bình luận và nội dung do khách hàng cung cấp',
      icon: <MessageSquare className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <div className="mb-4 rounded-xl overflow-hidden border border-slate-100 shadow-sm max-w-md mx-auto bg-slate-50">
            <img src="/images/policies/customer_review.png" alt="Đánh giá từ khách hàng" className="w-full h-auto mix-blend-multiply" />
          </div>
          <p>Nội dung đăng tải phải trung thực, không vi phạm pháp luật. Cấm các nội dung:</p>
          <BulletList items={[
            'Xúc phạm, đe dọa, vu khống, phân biệt đối xử.',
            'Quảng cáo, spam, link ngoài.',
            'Sai sự thật, gây hiểu nhầm.',
            'Tiết lộ thông tin cá nhân của người khác, vi phạm SHTT.',
          ]} />
          <p>ElectroMart có quyền ẩn/xóa nội dung vi phạm mà không cần báo trước và hạn chế tính năng bình luận của tài khoản vi phạm.</p>
        </div>
      ),
    },
    {
      id: 't-14',
      number: '14',
      title: 'Quyền sở hữu trí tuệ',
      icon: <BookOpen className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Toàn bộ giao diện, hình ảnh, văn bản, logo, mã nguồn thuộc quyền sở hữu/sử dụng hợp pháp của ElectroMart Việt Nam.</p>
          <p>Nghiêm cấm sao chép, phân phối, thương mại hóa nếu chưa được sự đồng ý bằng văn bản.</p>
        </div>
      ),
    },
    {
      id: 't-15',
      number: '15',
      title: 'Lưu trữ dữ liệu vận hành website',
      icon: <Database className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Trường dữ liệu', 'Nội dung']}
            rows={[
              ['Mã tài khoản / Đăng nhập', 'Mã định danh, IP, thiết bị, thời gian'],
              ['Lịch sử thao tác', 'Tìm kiếm, xem, thêm giỏ, đặt hàng'],
              ['Lịch sử đơn hàng / TT', 'Đơn hàng, mã giao dịch, trạng thái TT'],
              ['Lịch sử bảo hành / khiếu nại', 'Yêu cầu hậu mãi, phản ánh, kết quả xử lý'],
              ['Lịch sử vi phạm', 'Cảnh báo, khóa tài khoản, hạn chế'],
            ]}
          />
        </div>
      ),
    },
    {
      id: 't-16',
      number: '16',
      title: 'Điều khoản áp dụng',
      icon: <FileText className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Quy chế này là một phần trong hệ thống chính sách của ElectroMart, bao gồm các chính sách Mua hàng, Giao nhận, Bảo hành, Bảo mật, Khiếu nại...</p>
          <p>Nếu có sự khác biệt giữa Quy chế này và chính sách chuyên biệt, sẽ căn cứ vào bản chất sự việc để áp dụng chính sách phù hợp nhất.</p>
        </div>
      ),
    },
    {
      id: 't-17',
      number: '17',
      title: 'Thay đổi quy chế',
      icon: <Repeat className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>ElectroMart Việt Nam có quyền điều chỉnh, cập nhật Quy chế. Mọi thay đổi quan trọng sẽ được công bố trên website. Tiếp tục sử dụng đồng nghĩa với việc đồng ý với quy chế mới.</p>
        </div>
      ),
    },
    {
      id: 't-18',
      number: '18',
      title: 'Kết luận',
      icon: <ShieldCheck className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Quy chế tạo cơ sở vận hành thống nhất, xác định rõ quyền và trách nhiệm của các bên.</p>
          <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
            <p className="text-sm font-semibold text-amber-800">
              ElectroMart hướng đến việc xây dựng môi trường mua sắm trực tuyến minh bạch, an toàn, chuyên nghiệp và phù hợp với thực tiễn kinh doanh.
            </p>
          </div>
        </div>
      ),
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Banner */}
      <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-amber-900/60">
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage:
              'radial-gradient(circle at 20% 60%, #f59e0b 0%, transparent 50%), radial-gradient(circle at 80% 20%, #fbbf24 0%, transparent 40%)',
          }}
        />
        <div className="relative mx-auto max-w-5xl px-4 py-12 lg:px-6">
          {/* Breadcrumb */}
          <nav className="mb-5 flex items-center gap-1.5 text-xs text-slate-400">
            <Link to="/" className="transition hover:text-white">Trang chủ</Link>
            <span>/</span>
            <Link to="/about" className="transition hover:text-white">Giới thiệu công ty</Link>
            <span>/</span>
            <span className="text-slate-200">Quy chế hoạt động</span>
          </nav>

          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-amber-500 shadow-lg shadow-amber-500/30">
              <Scale className="h-6 w-6 text-white" />
            </div>
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-amber-400">Chính sách</p>
              <h1 className="text-2xl font-bold font-display leading-tight text-white lg:text-3xl">
                Quy chế hoạt động website
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-300">
                Các nguyên tắc, quy trình và điều khoản sử dụng nền tảng thương mại điện tử ElectroMart nhằm đảm bảo môi trường giao dịch an toàn, minh bạch và chuyên nghiệp.
              </p>
            </div>
          </div>

          {/* Quick stats */}
          <div className="mt-8 grid grid-cols-3 gap-4 border-t border-white/10 pt-6">
            {[
              { label: 'Quy trình giao dịch', value: '7 Bước' },
              { label: 'Cam kết nguồn gốc', value: 'Chính hãng' },
              { label: 'Điều khoản chi tiết', value: '18' },
            ].map((s) => (
              <div key={s.label} className="text-center">
                <div className="text-2xl font-bold text-amber-400">{s.value}</div>
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
                    ? 'border-amber-200 bg-white shadow-md shadow-amber-500/5'
                    : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm'
                }`}
              >
                <button
                  id={`terms-section-${section.number}`}
                  onClick={() => toggle(section.id)}
                  className="flex w-full items-center gap-4 px-5 py-4 text-left"
                  aria-expanded={isOpen}
                >
                  <div
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors ${
                      isOpen ? 'bg-amber-500 text-white' : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    {section.icon}
                  </div>
                  <div className="flex-1">
                    <div className="mb-0.5">
                      <span className={`text-xs font-bold ${isOpen ? 'text-amber-600' : 'text-slate-400'}`}>
                        Điều {section.number}
                      </span>
                    </div>
                    <div className={`text-sm font-semibold leading-tight ${isOpen ? 'text-amber-700' : 'text-slate-800'}`}>
                      {section.title}
                    </div>
                  </div>
                  <div className={`shrink-0 transition-colors ${isOpen ? 'text-amber-600' : 'text-slate-400'}`}>
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
            Mua hàng & Thanh toán
          </Link>
          <Link
            to="/privacy"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
          >
            Bảo mật & Dữ liệu
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
