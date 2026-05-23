<div className="mb-4 mt-2 rounded-xl overflow-hidden border border-slate-100 shadow-sm max-w-md mx-auto bg-slate-50">
            <img src="/images/policies/reward.png" alt="Quyền lợi thành viên VIP" className="w-full h-auto mix-blend-multiply" />
          </div>

import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ChevronDown, ChevronUp, Award, User, Star, Gift, Ticket, TrendingUp,
  XCircle, RefreshCw, MessageSquare, ShieldAlert, Database, FileText, CheckCircle,
  AlertTriangle, ShieldCheck, HelpCircle, ArrowRight
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
    <div className="flex items-start gap-2 rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-3 text-sm text-indigo-800">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-indigo-500" />
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

interface Section {
  id: string;
  number: string;
  title: string;
  icon: React.ReactNode;
  content: React.ReactNode;
}

export default function MemberPolicyPage() {
  const [expanded, setExpanded] = useState<string | null>('m-1');
  const toggle = (id: string) => setExpanded((p) => (p === id ? null : id));

  const sections: Section[] = [
    {
      id: 'm-1',
      number: '1',
      title: 'Quy định chung',
      icon: <Award className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Chính sách thành viên, khuyến mãi và đánh giá sản phẩm của ElectroMart Việt Nam quy định rõ quyền lợi của khách hàng khi tham gia hệ thống thành viên, sử dụng điểm thưởng, mã giảm giá, và chức năng đánh giá sản phẩm.</p>
          <p>Chính sách áp dụng cho khách hàng có tài khoản hợp lệ, phát sinh hoạt động mua hàng, tích điểm, tham gia ưu đãi hoặc gửi phản hồi.</p>
          <Note>Việc tham gia hệ thống và sử dụng ưu đãi được hiểu là khách hàng đã đọc, hiểu và đồng ý tuân thủ các nội dung được quy định trong chính sách này.</Note>
        </div>
      ),
    },
    {
      id: 'm-2',
      number: '2',
      title: 'Chính sách tài khoản thành viên',
      icon: <User className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Đăng ký tài khoản thành viên giúp khách hàng quản lý đơn hàng, lưu địa chỉ, tích điểm, nhận voucher và gửi yêu cầu hỗ trợ dễ dàng hơn.</p>
          <p>Mỗi khách hàng chỉ nên sử dụng <strong>một tài khoản chính</strong>. Hệ thống có quyền kiểm tra, hợp nhất hoặc khóa các tài khoản có dấu hiệu tạo lập nhiều tài khoản nhằm trục lợi khuyến mãi, gian lận điểm thưởng.</p>
        </div>
      ),
    },
    {
      id: 'm-3',
      number: '3',
      title: 'Hạng thành viên',
      icon: <Star className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <p>Hệ thống có thể phân hạng thành viên dựa trên tổng giá trị mua hàng, số lượng giao dịch hoặc lịch sử sử dụng dịch vụ.</p>
          <Table
            headers={['Hạng thành viên', 'Điều kiện tham khảo', 'Quyền lợi tham khảo']}
            rows={[
              ['Thành viên cơ bản', 'Đăng ký tài khoản thành công', 'Theo dõi đơn hàng, lưu địa chỉ, nhận thông báo'],
              ['Thành viên bạc', 'Có phát sinh giao dịch hợp lệ', 'Ưu đãi định kỳ, tích điểm mua hàng'],
              ['Thành viên vàng', 'Đạt mức chi tiêu nhất định', 'Tỷ lệ tích điểm cao hơn, ưu tiên hỗ trợ'],
              ['Thành viên kim cương', 'Giá trị giao dịch cao', 'Ưu đãi đặc biệt, ưu tiên bảo hành, vận chuyển'],
            ]}
          />
        </div>
      ),
    },
    {
      id: 'm-4',
      number: '4',
      title: 'Chính sách tích điểm',
      icon: <TrendingUp className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <div className="mb-4 rounded-xl overflow-hidden border border-slate-100 shadow-sm max-w-md mx-auto bg-slate-50">
            <img src="/images/policies/member.png" alt="Tích điểm và hạng thành viên" className="w-full h-auto mix-blend-multiply" />
          </div>
          <p>Điểm thưởng được ghi nhận khi đơn hàng:</p>
          <BulletList items={[
            'Đặt bằng tài khoản thành viên hợp lệ.',
            'Đã thanh toán thành công và giao hàng hoàn tất.',
            'Không bị hủy, hoàn tiền hoặc xác định gian lận.',
          ]} />
          <div className="rounded border border-indigo-200 bg-indigo-50 p-3 text-indigo-800 font-semibold">
            Điểm thưởng = Giá trị thanh toán hợp lệ × Tỷ lệ tích điểm
          </div>
          <p>Ví dụ: Tỷ lệ tích điểm 1%, đơn hàng thanh toán 10.000.000đ → Nhận 100.000 điểm tương ứng.</p>
        </div>
      ),
    },
    {
      id: 'm-5',
      number: '5',
      title: 'Quy định sử dụng điểm thưởng',
      icon: <Gift className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Nội dung', 'Quy định']}
            rows={[
              ['Điều kiện sử dụng', 'Tài khoản hoạt động và có điểm khả dụng'],
              ['Phạm vi áp dụng', 'Cho sản phẩm hoặc đơn hàng đủ điều kiện'],
              ['Giới hạn sử dụng', 'Có thể bị giới hạn theo % giá trị đơn hàng'],
              ['Kết hợp ưu đãi', 'Tùy chương trình (có thể không áp dụng chung voucher)'],
              ['Hoàn lại điểm', 'Chỉ hoàn lại khi đơn hàng hủy/hoàn tiền hợp lệ'],
            ]}
          />
          <p className="font-semibold text-amber-600">Lưu ý: Điểm thưởng không có giá trị quy đổi thành tiền mặt và không được chuyển nhượng.</p>
        </div>
      ),
    },
    {
      id: 'm-6',
      number: '6',
      title: 'Thời hạn điểm thưởng',
      icon: <Database className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Điểm thưởng có thể có thời hạn sử dụng. Khi hết hạn, hệ thống sẽ tự động thu hồi điểm và không được khôi phục.</p>
          <p>Nếu tài khoản bị khóa do vi phạm, điểm thưởng có thể bị tạm ngưng sử dụng hoặc thu hồi vĩnh viễn tùy mức độ vi phạm.</p>
        </div>
      ),
    },
    {
      id: 'm-7',
      number: '7',
      title: 'Chính sách voucher và mã giảm giá',
      icon: <Ticket className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Điều kiện', 'Nội dung']}
            rows={[
              ['Thời gian hiệu lực', 'Ngày bắt đầu và kết thúc'],
              ['Giá trị ưu đãi', 'Số tiền cố định hoặc phần trăm đơn hàng'],
              ['Đơn hàng tối thiểu', 'Mức giá trị yêu cầu để sử dụng mã'],
              ['Nhóm SP áp dụng', 'Toàn bộ hoặc danh mục/sản phẩm cụ thể'],
              ['Số lần sử dụng', 'Giới hạn theo user hoặc toàn hệ thống'],
              ['Đối tượng', 'Thành viên mới/cũ, hạng thành viên'],
            ]}
          />
          <p>ElectroMart có quyền từ chối áp dụng voucher nếu phát hiện sử dụng sai điều kiện hoặc gian lận.</p>
        </div>
      ),
    },
    {
      id: 'm-8',
      number: '8',
      title: 'Chính sách chương trình khuyến mãi',
      icon: <Gift className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>ElectroMart triển khai nhiều CTKM (giảm giá, tặng quà, freeship, tích điểm nhân hệ số...).</p>
          <p>Chương trình có thể bị giới hạn bởi: thời gian, số lượng tồn kho, khu vực, hạng thành viên. Trong trường hợp lỗi kỹ thuật hiển thị sai thông tin khuyến mãi, ElectroMart có quyền điều chỉnh lại và thông báo cho khách hàng.</p>
        </div>
      ),
    },
    {
      id: 'm-9',
      number: '9',
      title: 'Xử lý ưu đãi khi hủy đơn',
      icon: <XCircle className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Tình huống hủy đơn', 'Hướng xử lý']}
            rows={[
              ['Chưa thanh toán & hủy', 'Voucher được hoàn lại nếu còn hiệu lực/lượt'],
              ['Đã thanh toán, hủy hợp lệ', 'Điểm đã dùng được hoàn lại sau khi xử lý'],
              ['Voucher đã hết hạn', 'Không mặc định cấp lại'],
              ['Hủy do lỗi hệ thống', 'Xem xét cấp lại voucher hoặc ưu đãi thay thế'],
              ['Hủy do gian lận', 'Thu hồi toàn bộ ưu đãi/điểm'],
            ]}
          />
        </div>
      ),
    },
    {
      id: 'm-10',
      number: '10',
      title: 'Xử lý ưu đãi khi đổi trả',
      icon: <RefreshCw className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <p>Khi đổi trả, nhập lại, hoàn tiền, hệ thống xử lý dựa trên <strong>giá trị giao dịch thực tế</strong> sau điều chỉnh.</p>
          <Table
            headers={['Trường hợp', 'Hướng xử lý']}
            rows={[
              ['Trả toàn bộ đơn', 'Thu hồi toàn bộ điểm đã tích'],
              ['Trả một phần', 'Điều chỉnh điểm theo giá trị thực tế còn lại'],
              ['Đổi sản phẩm đắt hơn', 'Tích điểm bổ sung cho phần chênh lệch'],
              ['Đổi sản phẩm rẻ hơn', 'Thu hồi điểm tương ứng giá trị giảm'],
              ['Đơn có quà tặng', 'Hoàn trả quà tặng hoặc khấu trừ giá trị'],
            ]}
          />
        </div>
      ),
    },
    {
      id: 'm-11',
      number: '11',
      title: 'Chính sách đánh giá sản phẩm',
      icon: <MessageSquare className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Khách hàng được khuyến khích đánh giá sản phẩm trung thực, khách quan sau khi mua hàng. Hệ thống ưu tiên hiển thị đánh giá từ khách hàng đã mua thành công ("Đã mua tại ElectroMart").</p>
          <BulletList items={[
            'Nội dung bao gồm: Số sao, nhận xét SP, dịch vụ, giao hàng.',
            'Có thể đính kèm hình ảnh/video thực tế.',
          ]} />
        </div>
      ),
    },
    {
      id: 'm-12',
      number: '12',
      title: 'Quy định nội dung bình luận / đánh giá',
      icon: <ShieldAlert className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p className="font-semibold text-slate-800">Các nội dung NGHIÊM CẤM:</p>
          <BulletList items={[
            'Sai sự thật, gây hiểu nhầm, không liên quan đến sản phẩm.',
            'Ngôn từ xúc phạm, đe dọa, kích động bạo lực.',
            'Tiết lộ thông tin cá nhân trái phép.',
            'Chèn link quảng cáo, bán hàng bên ngoài.',
            'Đánh giá giả mạo, thuê người đánh giá.',
          ]} />
          <p>ElectroMart có quyền ẩn, xóa nội dung vi phạm mà không cần báo trước, hạn chế tính năng đối với tài khoản vi phạm nhiều lần.</p>
        </div>
      ),
    },
    {
      id: 'm-13',
      number: '13',
      title: 'Phản hồi của ElectroMart đối với đánh giá',
      icon: <HelpCircle className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>ElectroMart có quyền phản hồi đánh giá để làm rõ thông tin, hỗ trợ khách hàng. Nếu đánh giá phản ánh lỗi SP/dịch vụ nghiêm trọng, ElectroMart sẽ liên hệ trực tiếp để xử lý qua quy trình Khiếu nại/Bảo hành.</p>
          <Note>Phản hồi tại phần đánh giá không thay thế cho quy trình bảo hành/đổi trả chính thức. Khách hàng cần liên hệ CSKH khi gặp sự cố.</Note>
        </div>
      ),
    },
    {
      id: 'm-14',
      number: '14',
      title: 'Các hành vi bị hạn chế hoặc bị cấm',
      icon: <XCircle className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList items={[
            'Tạo nhiều tài khoản trục lợi ưu đãi khách hàng mới.',
            'Dùng voucher, mã giảm giá trái điều kiện.',
            'Mua bán, chuyển nhượng voucher trái phép.',
            'Lợi dụng lỗi hệ thống, đặt hàng ảo nhằm tích điểm/quà tặng.',
            'Hoàn trả sản phẩm liên tục nhằm trục lợi.',
          ]} />
          <p>Hệ thống có quyền thu hồi ưu đãi, khóa tài khoản nếu phát hiện gian lận.</p>
        </div>
      ),
    },
    {
      id: 'm-15',
      number: '15',
      title: 'Trách nhiệm của khách hàng',
      icon: <User className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList items={[
            'Sử dụng tài khoản, điểm thưởng, voucher đúng mục đích, quy định.',
            'Kiểm tra kỹ điều kiện khuyến mãi trước khi đặt hàng.',
            'Cung cấp đánh giá, bình luận trung thực, không vi phạm pháp luật.',
            'Tự chịu trách nhiệm đối với nội dung đánh giá mình đăng tải.',
          ]} />
        </div>
      ),
    },
    {
      id: 'm-16',
      number: '16',
      title: 'Trách nhiệm của ElectroMart Việt Nam',
      icon: <ShieldCheck className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList items={[
            'Công bố rõ điều kiện CTKM, tích điểm, voucher.',
            'Ghi nhận điểm và xử lý ưu đãi minh bạch, chính xác.',
            'Hỗ trợ khách hàng khắc phục nếu có lỗi hệ thống.',
            'Kiểm duyệt, ẩn, xóa bình luận vi phạm chính sách.',
          ]} />
        </div>
      ),
    },
    {
      id: 'm-17',
      number: '17',
      title: 'Lưu trữ dữ liệu thành viên, khuyến mãi',
      icon: <Database className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Trường dữ liệu', 'Nội dung']}
            rows={[
              ['Thông tin hạng', 'Hạng thành viên, tổng giá trị mua hàng'],
              ['Điểm thưởng', 'Khả dụng, đã dùng, bị thu hồi'],
              ['Mã Voucher', 'Mã đã nhận, đã sử dụng'],
              ['Lịch sử KM', 'Các chương trình khách hàng đã tham gia'],
              ['Đánh giá SP', 'Nội dung, số sao, hình ảnh, trạng thái hiển thị'],
              ['Trạng thái vi phạm', 'Cảnh báo, hạn chế hoặc khóa tài khoản'],
            ]}
          />
        </div>
      ),
    },
    {
      id: 'm-18',
      number: '18',
      title: 'Điều khoản áp dụng',
      icon: <FileText className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Chính sách này có thể được cập nhật, bổ sung theo yêu cầu vận hành hoặc CTKM mới. Khách hàng tiếp tục sử dụng hệ thống đồng nghĩa với việc đồng ý với những thay đổi được công bố trên website.</p>
        </div>
      ),
    },
    {
      id: 'm-19',
      number: '19',
      title: 'Kết luận',
      icon: <CheckCircle className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Chính sách được xây dựng để quản lý minh bạch các quyền lợi, từ điểm thưởng, voucher đến tính năng đánh giá sản phẩm.</p>
          <div className="rounded-lg border border-indigo-200 bg-indigo-50 px-4 py-3 text-indigo-800">
            <p className="text-sm font-semibold">
              Việc tuân thủ chính sách giúp xây dựng cộng đồng mua sắm minh bạch, hạn chế gian lận và tối ưu quyền lợi tốt nhất cho mọi khách hàng.
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
              'radial-gradient(circle at 20% 60%, #6366f1 0%, transparent 50%), radial-gradient(circle at 80% 20%, #818cf8 0%, transparent 40%)',
          }}
        />
        <div className="relative mx-auto max-w-5xl px-4 py-12 lg:px-6">
          {/* Breadcrumb */}
          <nav className="mb-5 flex items-center gap-1.5 text-xs text-slate-400">
            <Link to="/" className="transition hover:text-white">Trang chủ</Link>
            <span>/</span>
            <Link to="/about" className="transition hover:text-white">Giới thiệu công ty</Link>
            <span>/</span>
            <span className="text-slate-200">Thành viên &amp; Khuyến mãi</span>
          </nav>

          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-indigo-500 shadow-lg shadow-indigo-500/30">
              <Award className="h-6 w-6 text-white" />
            </div>
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-indigo-400">Chính sách</p>
              <h1 className="text-2xl font-bold font-display leading-tight text-white lg:text-3xl">
                Thành viên, Khuyến mãi &amp; Đánh giá
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-300">
                Thông tin toàn diện về hạng thành viên, quyền lợi tích điểm, quy định sử dụng voucher ưu đãi và nguyên tắc đánh giá sản phẩm.
              </p>
            </div>
          </div>

          {/* Quick stats */}
          <div className="mt-8 grid grid-cols-3 gap-4 border-t border-white/10 pt-6">
            {[
              { label: 'Hạng thành viên', value: '4 Hạng' },
              { label: 'Tích điểm mua hàng', value: 'Có' },
              { label: 'Điều khoản chi tiết', value: '19' },
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
                  id={`member-section-${section.number}`}
                  onClick={() => toggle(section.id)}
                  className="flex w-full items-center gap-4 px-5 py-4 text-left"
                  aria-expanded={isOpen}
                >
                  <div
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors ${
                      isOpen ? 'bg-indigo-500 text-white' : 'bg-slate-100 text-slate-500'
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
            to="/purchase-policy"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
          >
            Mua hàng & Thanh toán
          </Link>
          <Link
            to="/terms"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
          >
            Quy chế hoạt động
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
