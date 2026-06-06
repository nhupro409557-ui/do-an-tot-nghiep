import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ChevronDown, ChevronUp, Shield, Database, Lock, EyeOff, UserCheck, 
  CreditCard, Clock, FileText, AlertTriangle, UserX, Activity, Share2, 
  Server, Key, HelpCircle, FileCheck, ShieldAlert, ArrowRight
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
    <div className="flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
      <div className="leading-relaxed">{children}</div>
    </div>
  );
}

function BulletList({ items }: { items: string[] }) {
  return (
    <ul className="space-y-1.5 text-sm text-slate-600">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2 leading-relaxed">
          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" />
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

export default function PrivacyPage() {
  const [expanded, setExpanded] = useState<string | null>('pr-1');
  const toggle = (id: string) => setExpanded((p) => (p === id ? null : id));

  const sections: Section[] = [
    {
      id: 'pr-1',
      number: '1',
      title: 'Quy định chung',
      icon: <Shield className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>ElectroMart Việt Nam cam kết tôn trọng và bảo vệ quyền riêng tư của khách hàng trong quá trình truy cập, đăng ký tài khoản, đặt hàng, thanh toán, bảo hành, đổi trả và sử dụng các dịch vụ trên hệ thống.</p>
          <p>Chính sách bảo mật, tài khoản và xử lý dữ liệu cá nhân được xây dựng nhằm quy định rõ phạm vi dữ liệu được thu thập, mục đích sử dụng, thời gian lưu trữ, các bên có thể tiếp cận dữ liệu, quyền của khách hàng, trách nhiệm bảo mật và nguyên tắc bảo vệ thông tin.</p>
          <Note>Khi truy cập website và sử dụng dịch vụ, khách hàng được hiểu là đã đọc, hiểu và đồng ý với các nội dung được quy định trong chính sách này. Nếu không đồng ý cung cấp một số thông tin cần thiết, hệ thống có thể không đáp ứng đầy đủ các chức năng dịch vụ.</Note>
        </div>
      ),
    },
    {
      id: 'pr-2',
      number: '2',
      title: 'Phạm vi dữ liệu cá nhân được thu thập',
      icon: <Database className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Nhóm dữ liệu', 'Nội dung dữ liệu']}
            rows={[
              ['Thông tin định danh', 'Họ tên, số điện thoại, email, ngày sinh, giới tính'],
              ['Thông tin tài khoản', 'Tên đăng nhập, mật khẩu (mã hóa), lịch sử đăng nhập'],
              ['Thông tin giao hàng', 'Địa chỉ, người nhận, số điện thoại, ghi chú'],
              ['Thông tin giao dịch', 'Mã đơn hàng, sản phẩm, số lượng, giá trị, lịch sử mua'],
              ['Thông tin bảo hành', 'IMEI, Serial, thời hạn, lịch sử yêu cầu bảo hành'],
              ['Thông tin hóa đơn', 'Tên người mua, MST, địa chỉ, email nhận hóa đơn'],
              ['Thông tin thanh toán', 'Phương thức thanh toán, mã giao dịch (không lưu số thẻ)'],
              ['Thông tin kỹ thuật', 'IP, trình duyệt, thiết bị, thời gian, lịch sử truy cập'],
              ['Thông tin CSKH', 'Nội dung phản hồi, khiếu nại, đánh giá, lịch sử hỗ trợ'],
            ]}
          />
          <p>ElectroMart Việt Nam không chủ động yêu cầu khách hàng cung cấp dữ liệu cá nhân nhạy cảm nếu không thật sự cần thiết.</p>
        </div>
      ),
    },
    {
      id: 'pr-3',
      number: '3',
      title: 'Hình thức thu thập dữ liệu',
      icon: <Server className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList items={[
            'Dữ liệu do khách hàng trực tiếp cung cấp: Đăng ký tài khoản, đặt hàng, liên hệ hỗ trợ.',
            'Dữ liệu phát sinh trong quá trình giao dịch: Lịch sử đơn hàng, thanh toán, bảo hành, sử dụng điểm thưởng.',
            'Dữ liệu kỹ thuật do hệ thống tự động ghi nhận: IP, thiết bị, cookies, thao tác trên website.',
            'Dữ liệu từ đối tác liên kết: ĐVVC, cổng thanh toán, ngân hàng xác nhận trạng thái giao dịch.',
          ]} />
        </div>
      ),
    },
    {
      id: 'pr-4',
      number: '4',
      title: 'Mục đích sử dụng dữ liệu',
      icon: <Activity className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Mục đích sử dụng', 'Nội dung thực hiện']}
            rows={[
              ['Xử lý đơn hàng', 'Xác nhận, chuẩn bị, giao hàng, đổi trả'],
              ['Quản lý tài khoản', 'Tạo, duy trì, xác thực và bảo vệ tài khoản'],
              ['Thanh toán & Hoàn tiền', 'Ghi nhận giao dịch, đối soát, xử lý hoàn tiền'],
              ['Xuất hóa đơn', 'Phát hành, gửi, tra cứu, điều chỉnh hóa đơn'],
              ['Giao nhận hàng hóa', 'Cung cấp thông tin cho đơn vị vận chuyển'],
              ['Bảo hành & Hậu mãi', 'Xác minh sản phẩm, đổi trả, hỗ trợ kỹ thuật'],
              ['Chăm sóc khách hàng', 'Phản hồi, xử lý khiếu nại, khảo sát'],
              ['Cá nhân hóa', 'Gợi ý sản phẩm, ghi nhớ giỏ hàng'],
              ['An toàn hệ thống', 'Phòng gian lận, chống truy cập trái phép'],
              ['Tuân thủ pháp luật', 'Cung cấp thông tin theo yêu cầu cơ quan NN'],
            ]}
          />
        </div>
      ),
    },
    {
      id: 'pr-5',
      number: '5',
      title: 'Thời gian lưu trữ dữ liệu',
      icon: <Clock className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Dữ liệu được lưu trữ trong thời gian cần thiết để phục vụ mục đích thu thập, xử lý giao dịch, kế toán, kiểm toán và tuân thủ pháp lý.</p>
          <BulletList items={[
            'Tài khoản người dùng: Lưu trữ đến khi khách hàng yêu cầu xóa hoặc hệ thống chấm dứt dịch vụ.',
            'Đơn hàng, hóa đơn, bảo hành: Tiếp tục lưu trữ để đối soát, phòng chống gian lận, giải quyết tranh chấp.',
            'Trường hợp yêu cầu xóa: Hệ thống sẽ thực hiện, tuy nhiên một số dữ liệu có thể phải giữ lại theo quy định pháp luật (kế toán, thuế).',
          ]} />
        </div>
      ),
    },
    {
      id: 'pr-6',
      number: '6',
      title: 'Các bên có thể tiếp cận dữ liệu',
      icon: <Share2 className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <p>ElectroMart cam kết không bán, trao đổi trái phép dữ liệu. Các bên tiếp cận trong phạm vi cần thiết:</p>
          <Table
            headers={['Đơn vị tiếp nhận', 'Mục đích tiếp nhận']}
            rows={[
              ['Đơn vị vận chuyển', 'Giao hàng, cập nhật vận đơn'],
              ['Ngân hàng, cổng thanh toán', 'Xác nhận thanh toán, hoàn tiền'],
              ['Công ty tài chính', 'Xét duyệt hồ sơ trả góp'],
              ['Hãng sản xuất / TTBH', 'Sửa chữa, đổi mới, xác nhận lỗi'],
              ['Hạ tầng kỹ thuật', 'Lưu trữ, bảo trì, bảo mật máy chủ'],
              ['Cơ quan nhà nước', 'Tuân thủ pháp luật khi có yêu cầu hợp pháp'],
            ]}
          />
        </div>
      ),
    },
    {
      id: 'pr-7',
      number: '7',
      title: 'Quyền của khách hàng đối với dữ liệu',
      icon: <UserCheck className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList items={[
            'Quyền được biết về việc thu thập và sử dụng dữ liệu.',
            'Quyền truy cập, kiểm tra thông tin cá nhân của mình.',
            'Quyền yêu cầu chỉnh sửa thông tin không chính xác/chưa đầy đủ.',
            'Quyền yêu cầu xóa dữ liệu (nếu không vi phạm nghĩa vụ pháp lý).',
            'Quyền rút lại sự đồng ý (như từ chối nhận email quảng cáo).',
            'Quyền khiếu nại nếu cho rằng dữ liệu bị xử lý sai mục đích.',
          ]} />
        </div>
      ),
    },
    {
      id: 'pr-8',
      number: '8',
      title: 'Phương thức tiếp cận, chỉnh sửa, xóa dữ liệu',
      icon: <FileText className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Khách hàng có thể tự cập nhật họ tên, SĐT, địa chỉ trên tài khoản. Đối với thông tin quan trọng (SĐT đăng nhập, email chính), cần liên hệ CSKH.</p>
          <div className="rounded-xl border border-slate-200 p-4">
            <p className="mb-2 font-bold text-emerald-700">Quy trình xử lý yêu cầu (chỉnh sửa/xóa):</p>
            <ol className="list-decimal pl-5 space-y-1">
              <li>Khách hàng gửi yêu cầu qua website/email/tổng đài.</li>
              <li>ElectroMart xác minh danh tính.</li>
              <li>Hệ thống kiểm tra nghĩa vụ liên quan (đơn hàng đang giao, bảo hành, công nợ).</li>
              <li>Thông báo khả năng xử lý và thực hiện yêu cầu hợp lệ.</li>
            </ol>
          </div>
        </div>
      ),
    },
    {
      id: 'pr-9',
      number: '9',
      title: 'Bảo mật tài khoản người dùng',
      icon: <Key className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Khách hàng tự chịu trách nhiệm bảo mật tài khoản, mật khẩu, mã OTP. Khuyến nghị:</p>
          <BulletList items={[
            'Không chia sẻ mật khẩu/OTP cho bất kỳ ai.',
            'Sử dụng mật khẩu mạnh, thay đổi định kỳ.',
            'Đăng xuất trên thiết bị công cộng.',
            'Thông báo ngay cho ElectroMart nếu nghi ngờ bị truy cập trái phép.',
          ]} />
          <Note>ElectroMart có quyền tạm khóa tài khoản nếu phát hiện dấu hiệu bất thường, đăng nhập trái phép, gian lận.</Note>
        </div>
      ),
    },
    {
      id: 'pr-10',
      number: '10',
      title: 'Bảo mật thông tin thanh toán',
      icon: <CreditCard className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Thông tin thẻ thanh toán KHÔNG được lưu trực tiếp trên hệ thống ElectroMart. Xử lý qua cổng thanh toán/ngân hàng. Hệ thống chỉ lưu:</p>
          <BulletList items={[
            'Mã đơn hàng, Mã giao dịch (để đối soát).',
            'Phương thức thanh toán, Trạng thái thanh toán.',
            'Thời gian giao dịch.',
          ]} />
          <p>Khách hàng tự bảo mật thẻ ngân hàng, ví điện tử, mã OTP. ElectroMart không chịu trách nhiệm do khách tự ý làm lộ thông tin.</p>
        </div>
      ),
    },
    {
      id: 'pr-11',
      number: '11',
      title: 'Cam kết bảo mật dữ liệu cá nhân',
      icon: <ShieldAlert className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList items={[
            'Mã hóa mật khẩu người dùng.',
            'Phân quyền truy cập dữ liệu nội bộ chặt chẽ.',
            'Bảo vệ dữ liệu trong môi trường máy chủ an toàn.',
            'Theo dõi/ngăn chặn hành vi đăng nhập bất thường, tấn công mạng.',
          ]} />
          <p>Nếu xảy ra sự cố rò rỉ dữ liệu do lỗi hệ thống/tấn công mạng, ElectroMart sẽ khắc phục và thông báo cho các bên theo quy định pháp luật.</p>
        </div>
      ),
    },
    {
      id: 'pr-12',
      number: '12',
      title: 'Trách nhiệm của khách hàng',
      icon: <UserCheck className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList items={[
            'Cung cấp thông tin chính xác, hợp pháp.',
            'Bảo mật tài khoản, mật khẩu, OTP.',
            'Không sử dụng website cho mục đích gian lận, phá hoại, spam.',
            'Thông báo kịp thời nếu bị lộ thông tin tài khoản.',
          ]} />
        </div>
      ),
    },
    {
      id: 'pr-13',
      number: '13',
      title: 'Trách nhiệm của ElectroMart Việt Nam',
      icon: <Shield className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList items={[
            'Thu thập, xử lý dữ liệu đúng mục đích.',
            'Áp dụng biện pháp kỹ thuật bảo vệ an toàn hệ thống.',
            'Xử lý yêu cầu chỉnh sửa/xóa dữ liệu hợp lệ.',
            'Khắc phục sự cố và hỗ trợ khách hàng nếu phát sinh lỗi hệ thống.',
          ]} />
        </div>
      ),
    },
    {
      id: 'pr-14',
      number: '14',
      title: 'Trách nhiệm khi phát sinh lỗi kỹ thuật',
      icon: <AlertTriangle className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Nếu hệ thống bị lỗi (phần mềm, đường truyền, bảo trì), ElectroMart sẽ cố gắng khắc phục nhanh nhất.</p>
          <p>Tuy nhiên, ElectroMart không chịu trách nhiệm nếu khách hàng không thể sử dụng dịch vụ do: lỗi thiết bị cá nhân, đường truyền cá nhân, phần mềm độc hại của khách, hoặc sự cố từ bên thứ 3 (ngân hàng, cổng thanh toán).</p>
        </div>
      ),
    },
    {
      id: 'pr-15',
      number: '15',
      title: 'Quy định hạn chế hoặc từ chối phục vụ',
      icon: <UserX className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Trường hợp vi phạm', 'Hướng xử lý']}
            rows={[
              ['Thông tin sai lệch, giả mạo', 'Từ chối giao dịch / yêu cầu xác minh'],
              ['Lợi dụng chính sách đổi trả, khuyến mãi', 'Khóa quyền sử dụng dịch vụ'],
              ['Đe dọa, xúc phạm, gây rối', 'Từ chối phục vụ, ghi nhận vi phạm'],
              ['Tấn công hệ thống, dò quét dữ liệu', 'Khóa tài khoản, báo cơ quan chức năng'],
              ['Đặt ảo, bùng hàng nhiều lần', 'Hạn chế đặt hàng online'],
              ['Phát tán nội dung vi phạm pháp luật', 'Khóa tài khoản, xóa nội dung'],
            ]}
          />
        </div>
      ),
    },
    {
      id: 'pr-16',
      number: '16',
      title: 'Tiếp nhận khiếu nại về dữ liệu và tài khoản',
      icon: <HelpCircle className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Quy trình xử lý khiếu nại về tài khoản, bảo mật:</p>
          <ol className="list-decimal pl-5 space-y-1">
            <li>Tiếp nhận khiếu nại & tài liệu liên quan.</li>
            <li>Xác minh danh tính, lịch sử đăng nhập/giao dịch.</li>
            <li>Xác định nguyên nhân (từ khách hàng, hệ thống hay bên thứ 3).</li>
            <li>Đề xuất phương án (khôi phục, hoàn tiền, khóa bảo mật).</li>
            <li>Phản hồi kết quả cho khách hàng.</li>
          </ol>
        </div>
      ),
    },
    {
      id: 'pr-17',
      number: '17',
      title: 'Lưu trữ dữ liệu bảo mật, tài khoản',
      icon: <Database className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Trường dữ liệu', 'Nội dung']}
            rows={[
              ['Mã khách hàng', 'Mã định danh tài khoản'],
              ['Thông tin tài khoản', 'Email, SĐT, trạng thái'],
              ['Lịch sử đăng nhập', 'Thời gian, IP, thiết bị'],
              ['Lịch sử giao dịch', 'Đơn hàng, bảo hành, thanh toán'],
              ['Cảnh báo bảo mật', 'Đăng nhập bất thường, nghi ngờ gian lận'],
            ]}
          />
        </div>
      ),
    },
    {
      id: 'pr-18',
      number: '18',
      title: 'Thay đổi chính sách',
      icon: <FileCheck className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>ElectroMart Việt Nam có quyền cập nhật, bổ sung chính sách nhằm phù hợp với hệ thống hoặc pháp luật. Thay đổi quan trọng sẽ được công bố trên website. Tiếp tục sử dụng dịch vụ đồng nghĩa với việc đồng ý với chính sách mới.</p>
        </div>
      ),
    },
    {
      id: 'pr-19',
      number: '19',
      title: 'Điều khoản áp dụng',
      icon: <FileText className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Nếu có sự khác biệt giữa chính sách này và các chính sách khác (thanh toán, đổi trả, giao hàng), ElectroMart sẽ căn cứ vào bản chất sự việc để áp dụng chính sách phù hợp, bảo vệ quyền lợi hợp pháp của khách hàng và an toàn hệ thống.</p>
        </div>
      ),
    },
    {
      id: 'pr-20',
      number: '20',
      title: 'Kết luận',
      icon: <ShieldAlert className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Chính sách được xây dựng nhằm bảo vệ quyền riêng tư, thông tin tài khoản, dữ liệu giao dịch và thanh toán của khách hàng.</p>
          <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-emerald-800">
            <p className="text-sm font-semibold">
              Quy định rõ ràng về phạm vi, quyền hạn và trách nhiệm giúp ElectroMart vận hành minh bạch, an toàn và chuyên nghiệp.
            </p>
          </div>
        </div>
      ),
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Banner */}
      <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-emerald-900/60">
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage:
              'radial-gradient(circle at 20% 60%, #10b981 0%, transparent 50%), radial-gradient(circle at 80% 20%, #34d399 0%, transparent 40%)',
          }}
        />
        <div className="relative mx-auto max-w-5xl px-4 py-12 lg:px-6">
          {/* Breadcrumb */}
          <nav className="mb-5 flex items-center gap-1.5 text-xs text-slate-400">
            <Link to="/" className="transition hover:text-white">Trang chủ</Link>
            <span>/</span>
            <Link to="/about" className="transition hover:text-white">Giới thiệu công ty</Link>
            <span>/</span>
            <span className="text-slate-200">Bảo mật &amp; Dữ liệu cá nhân</span>
          </nav>

          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-emerald-500 shadow-lg shadow-emerald-500/30">
              <Shield className="h-6 w-6 text-white" />
            </div>
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-emerald-400">Chính sách</p>
              <h1 className="text-2xl font-bold font-display leading-tight text-white lg:text-3xl">
                Bảo mật, Tài khoản &amp; Dữ liệu cá nhân
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-300">
                Cam kết của chúng tôi trong việc bảo vệ quyền riêng tư, an toàn dữ liệu thanh toán, quản lý tài khoản và xử lý minh bạch mọi thông tin trong hệ thống.
              </p>
            </div>
          </div>

          {/* Quick stats */}
          <div className="mt-8 grid grid-cols-3 gap-4 border-t border-white/10 pt-6">
            {[
              { label: 'Lưu thẻ thanh toán', value: 'Không' },
              { label: 'Quyền xóa dữ liệu', value: 'Hỗ trợ' },
              { label: 'Điều khoản bảo mật', value: '20' },
            ].map((s) => (
              <div key={s.label} className="text-center">
                <div className="text-2xl font-bold text-emerald-400">{s.value}</div>
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
                    ? 'border-emerald-200 bg-white shadow-md shadow-emerald-500/5'
                    : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm'
                }`}
              >
                <button
                  id={`pr-section-${section.number}`}
                  onClick={() => toggle(section.id)}
                  className="flex w-full items-center gap-4 px-5 py-4 text-left"
                  aria-expanded={isOpen}
                >
                  <div
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors ${
                      isOpen ? 'bg-emerald-500 text-white' : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    {section.icon}
                  </div>
                  <div className="flex-1">
                    <div className="mb-0.5">
                      <span className={`text-xs font-bold ${isOpen ? 'text-emerald-600' : 'text-slate-400'}`}>
                        Điều {section.number}
                      </span>
                    </div>
                    <div className={`text-sm font-semibold leading-tight ${isOpen ? 'text-emerald-700' : 'text-slate-800'}`}>
                      {section.title}
                    </div>
                  </div>
                  <div className={`shrink-0 transition-colors ${isOpen ? 'text-emerald-600' : 'text-slate-400'}`}>
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
            to="/return-warranty-policy"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
          >
            Bảo hành, Đổi trả & Kỹ thuật
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
