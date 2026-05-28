import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ChevronDown, ChevronUp, Scale, AlertTriangle, PhoneCall, ListChecks,
  Clock, ShieldCheck, UserCheck, Handshake, Landmark, DollarSign,
  XOctagon, Database, FileText, Settings, Flag, ArrowRight
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
    <div className="flex items-start gap-2 rounded-lg border border-violet-200 bg-violet-50 px-4 py-3 text-sm text-violet-800">
      <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-violet-500" />
      <div className="leading-relaxed">{children}</div>
    </div>
  );
}

function BulletList({ items }: { items: string[] }) {
  return (
    <ul className="space-y-1.5 text-sm text-slate-600">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2 leading-relaxed">
          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-violet-500" />
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

export default function DisputePage() {
  const [expanded, setExpanded] = useState<string | null>('d-1');
  const toggle = (id: string) => setExpanded((p) => (p === id ? null : id));

  const sections: Section[] = [
    {
      id: 'd-1',
      number: '1',
      title: 'Quy định chung',
      icon: <Scale className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>ElectroMart Việt Nam có trách nhiệm tiếp nhận, xác minh và xử lý các khiếu nại của khách hàng phát sinh trong quá trình mua sắm, thanh toán, giao nhận, bảo hành và sử dụng dịch vụ trên hệ thống.</p>
          <p>Quy trình được xây dựng nhằm bảo vệ quyền lợi hợp pháp của khách hàng, đảm bảo sự minh bạch, khách quan. Mọi tranh chấp được ưu tiên giải quyết thông qua thương lượng và thỏa thuận trên tinh thần thiện chí.</p>
        </div>
      ),
    },
    {
      id: 'd-2',
      number: '2',
      title: 'Phạm vi khiếu nại được tiếp nhận',
      icon: <AlertTriangle className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Nhóm khiếu nại', 'Nội dung tiếp nhận']}
            rows={[
              ['Sản phẩm', 'Lỗi, sai mẫu mã, màu sắc, cấu hình, không đúng mô tả, thiếu phụ kiện'],
              ['Đơn hàng', 'Hủy sai, giao thiếu, giao nhầm, chậm, sai địa chỉ người nhận'],
              ['Thanh toán', 'Chưa ghi nhận, thanh toán trùng, hoàn tiền chậm, sai số tiền'],
              ['Hóa đơn', 'Sai thông tin, chưa nhận được, cần điều chỉnh/thay thế'],
              ['Giao hàng', 'Hư hỏng, rách móp ướt kiện hàng, thất lạc, không thành công'],
              ['Bảo hành, đổi trả', 'Không được tiếp nhận, sai chính sách, sai mức khấu trừ'],
              ['Tài khoản, dữ liệu', 'Không đăng nhập được, nghi ngờ truy cập trái phép, rò rỉ dữ liệu'],
              ['Khuyến mãi', 'Không áp dụng được voucher, điểm thưởng, ưu đãi'],
              ['Thái độ phục vụ', 'Nhân viên hỗ trợ chưa phù hợp, phản hồi chậm, sai thông tin'],
            ]}
          />
          <p>Những khiếu nại không thuộc phạm vi giao dịch hoặc không đủ căn cứ xác minh có thể bị từ chối tiếp nhận.</p>
        </div>
      ),
    },
    {
      id: 'd-3',
      number: '3',
      title: 'Kênh tiếp nhận khiếu nại',
      icon: <PhoneCall className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Kênh tiếp nhận', 'Thông tin']}
            rows={[
              ['Website', 'Biểu mẫu liên hệ / Trung tâm hỗ trợ'],
              ['Tài khoản', 'Mục "Đơn hàng của tôi" / "Yêu cầu hỗ trợ"'],
              ['Email CSKH', 'cskh@electromart.vn'],
              ['Tổng đài', '1900 xxxx'],
              ['Trực tiếp', 'Tại cửa hàng hoặc điểm tiếp nhận bảo hành'],
            ]}
          />
          <Note>Khi gửi khiếu nại, khách hàng cần cung cấp: Họ tên, SĐT, mã đơn hàng/giao dịch, nội dung, hình ảnh/video sản phẩm để có cơ sở xác minh.</Note>
        </div>
      ),
    },
    {
      id: 'd-4',
      number: '4',
      title: 'Quy trình giải quyết khiếu nại',
      icon: <ListChecks className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <ol className="list-decimal pl-5 space-y-3">
            <li>
              <strong className="text-violet-700">Tiếp nhận khiếu nại:</strong>
              <p className="mt-1 text-slate-500">CSKH tiếp nhận thông tin, ghi nhận mã khiếu nại, thời gian, mã đơn hàng và trạng thái ban đầu lên hệ thống.</p>
            </li>
            <li>
              <strong className="text-violet-700">Xác minh thông tin:</strong>
              <p className="mt-1 text-slate-500">Liên hệ khách hàng để làm rõ vấn đề. Có thể yêu cầu bổ sung hình ảnh, video mở hộp, chứng từ, sao kê...</p>
            </li>
            <li>
              <strong className="text-violet-700">Chuyển bộ phận chuyên trách xử lý:</strong>
              <p className="mt-1 text-slate-500">Giao việc cho Kho vận, Kế toán, Kỹ thuật, Marketing hoặc Đơn vị vận chuyển để điều tra dữ liệu hệ thống.</p>
            </li>
            <li>
              <strong className="text-violet-700">Đề xuất phương án giải quyết:</strong>
              <p className="mt-1 text-slate-500">Dựa trên chính sách, có thể: giao bổ sung, thu hồi, đổi mới, bảo hành, hoàn tiền, điều chỉnh hóa đơn, hoặc từ chối nếu không hợp lệ.</p>
            </li>
            <li>
              <strong className="text-violet-700">Thông báo kết quả:</strong>
              <p className="mt-1 text-slate-500">Thông báo cho khách hàng qua điện thoại/email về nguyên nhân, trách nhiệm, phương án xử lý và thời hạn thực hiện.</p>
            </li>
            <li>
              <strong className="text-violet-700">Thực hiện và đóng khiếu nại:</strong>
              <p className="mt-1 text-slate-500">Tiến hành thực thi (hoàn tiền, giao hàng...). Cập nhật trạng thái "Đã giải quyết" trên hệ thống sau khi hoàn tất.</p>
            </li>
          </ol>
        </div>
      ),
    },
    {
      id: 'd-5',
      number: '5',
      title: 'Thời hạn xử lý khiếu nại',
      icon: <Clock className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Nhóm khiếu nại', 'Phản hồi ban đầu', 'Thời gian xử lý dự kiến']}
            rows={[
              ['Khiếu nại thông thường', 'Trong 24h', '03–05 ngày làm việc'],
              ['Liên quan giao hàng', 'Trong 24h', '03–07 ngày làm việc'],
              ['Thanh toán / Hoàn tiền', 'Trong 24h', '05–10 ngày làm việc'],
              ['Hóa đơn VAT', 'Trong 24h', '03–07 ngày làm việc'],
              ['Bảo hành kỹ thuật', 'Trong 24h', '07–14 ngày làm việc'],
              ['Dữ liệu cá nhân / Tài khoản', 'Trong 24h', '03–10 ngày làm việc'],
              ['Phức tạp cần bên thứ 3', 'Trong 24h', 'Tùy phản hồi của bên thứ 3'],
            ]}
          />
          <p>Trong quá trình xử lý, ElectroMart sẽ cập nhật tiến độ cho khách hàng.</p>
        </div>
      ),
    },
    {
      id: 'd-6',
      number: '6',
      title: 'Trách nhiệm của ElectroMart Việt Nam',
      icon: <ShieldCheck className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList items={[
            'Tiếp nhận và xử lý khiếu nại một cách nghiêm túc, khách quan, đúng quy trình.',
            'Cung cấp/đối chiếu tài liệu, chứng từ để làm rõ sự việc (không vi phạm bảo mật).',
            'Trường hợp lỗi thuộc về ElectroMart: Có biện pháp khắc phục, đổi SP, hoàn tiền, hoặc bồi hoàn thiệt hại hợp lý.',
            'KHÔNG chịu trách nhiệm nếu khách hàng cung cấp sai thông tin, lộ OTP, sử dụng sai HDSD, không kiểm hàng, hoặc không cung cấp đủ chứng cứ xác minh.',
          ]} />
        </div>
      ),
    },
    {
      id: 'd-7',
      number: '7',
      title: 'Trách nhiệm của khách hàng',
      icon: <UserCheck className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList items={[
            'Cung cấp thông tin khiếu nại trung thực, chính xác.',
            'Phối hợp cung cấp hình ảnh, video mở hộp, hóa đơn, biên bản giao nhận.',
            'Bảo quản sản phẩm, hộp, phụ kiện trong thời gian chờ xử lý.',
            'Không trục lợi, không cung cấp sai sự thật, đe dọa hoặc cản trở quá trình làm việc của nhân viên.',
          ]} />
        </div>
      ),
    },
    {
      id: 'd-8',
      number: '8',
      title: 'Cơ chế thương lượng và giải quyết tranh chấp',
      icon: <Handshake className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Mọi tranh chấp trước hết được giải quyết thông qua thương lượng, trao đổi và thỏa thuận trên tinh thần tôn trọng quyền lợi hợp pháp.</p>
          <p>Quá trình này thực hiện qua điện thoại, email hoặc gặp trực tiếp. Các bên có trách nhiệm cung cấp chứng cứ làm rõ. Nếu lỗi do ElectroMart, sẽ áp dụng phương án khắc phục/bồi hoàn tương xứng.</p>
        </div>
      ),
    },
    {
      id: 'd-9',
      number: '9',
      title: 'Chuyển tranh chấp đến cơ quan có thẩm quyền',
      icon: <Landmark className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Nếu không đạt được thỏa thuận thương lượng, một trong hai bên có quyền đưa vụ việc đến cơ quan có thẩm quyền, bao gồm:</p>
          <BulletList items={[
            'Cơ quan bảo vệ quyền lợi người tiêu dùng.',
            'Cơ quan quản lý nhà nước về TMĐT.',
            'Trọng tài thương mại.',
            'Tòa án có thẩm quyền.',
          ]} />
          <p>Quyết định của cơ quan thẩm quyền là căn cứ cuối cùng.</p>
        </div>
      ),
    },
    {
      id: 'd-10',
      number: '10',
      title: 'Quy định về bồi hoàn thiệt hại',
      icon: <DollarSign className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Trường hợp', 'Phương án bồi hoàn']}
            rows={[
              ['Giao sai sản phẩm', 'Đổi đúng SP hoặc hoàn tiền'],
              ['Giao thiếu sản phẩm/phụ kiện', 'Giao bổ sung hoặc hoàn lại phần thiếu'],
              ['Thanh toán lỗi do hệ thống', 'Hoàn tiền hoặc ghi nhận lại giao dịch'],
              ['Hoàn tiền chậm do lỗi nội bộ', 'Ưu tiên xử lý và thông báo tiến độ'],
              ['Hủy đơn do lỗi tồn kho', 'Hoàn tiền + hỗ trợ ưu đãi thay thế'],
              ['Sai hóa đơn do lỗi hệ thống', 'Điều chỉnh / thay thế hóa đơn'],
              ['Lỗi bảo hành do tiếp nhận sai', 'Tiếp nhận lại, xử lý theo đúng chính sách'],
            ]}
          />
          <p>ElectroMart không bồi hoàn thiệt hại gián tiếp hoặc lỗi từ bên thứ ba (bất khả kháng).</p>
        </div>
      ),
    },
    {
      id: 'd-11',
      number: '11',
      title: 'Các trường hợp khiếu nại bị từ chối',
      icon: <XOctagon className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList items={[
            'Không liên quan đến giao dịch tại ElectroMart.',
            'Không có mã đơn hàng, hóa đơn, chứng cứ xác minh hợp lệ.',
            'Nội dung sai sự thật, mâu thuẫn dữ liệu hoặc có dấu hiệu gian lận.',
            'Sản phẩm đã bị tự ý can thiệp, sửa chữa trước khi tiếp nhận.',
            'Khách hàng không phối hợp cung cấp tài liệu xác minh.',
            'Sử dụng sai hướng dẫn hoặc hư hỏng do khách hàng tự gây ra.',
            'Đã giải quyết xong và không có tình tiết mới.',
          ]} />
        </div>
      ),
    },
    {
      id: 'd-12',
      number: '12',
      title: 'Lưu trữ hồ sơ khiếu nại',
      icon: <Database className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <p>Hệ thống lưu trữ hồ sơ để đối soát và nâng cao chất lượng:</p>
          <Table
            headers={['Trường dữ liệu', 'Nội dung']}
            rows={[
              ['Mã khiếu nại & Khách hàng', 'Định danh duy nhất và tài khoản gửi khiếu nại'],
              ['Thông tin sự việc', 'Loại khiếu nại, mã đơn hàng, mô tả chi tiết, hình ảnh'],
              ['Tiến độ xử lý', 'Bộ phận phụ trách, trạng thái, thời gian tiếp nhận/đóng'],
              ['Kết quả', 'Phương án cuối cùng, ghi chú nội bộ'],
            ]}
          />
        </div>
      ),
    },
    {
      id: 'd-13',
      number: '13',
      title: 'Điều khoản áp dụng',
      icon: <FileText className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Quy trình này là một phần của hệ thống chính sách (Mua hàng, Giao nhận, Bảo hành, Bảo mật...). Trong trường hợp có sự khác biệt, ElectroMart sẽ căn cứ vào bản chất vụ việc để áp dụng chính sách phù hợp nhất nhằm bảo vệ quyền lợi hợp pháp của các bên.</p>
        </div>
      ),
    },
    {
      id: 'd-14',
      number: '14',
      title: 'Thay đổi quy trình',
      icon: <Settings className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>ElectroMart có thể cập nhật quy trình. Thay đổi quan trọng sẽ được công bố trên website. Việc tiếp tục sử dụng dịch vụ đồng nghĩa với việc đồng ý với những thay đổi đó.</p>
        </div>
      ),
    },
    {
      id: 'd-15',
      number: '15',
      title: 'Kết luận',
      icon: <Flag className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Quy trình được xây dựng để tạo ra một hệ thống xử lý minh bạch, rõ ràng từ lúc tiếp nhận đến khi đóng khiếu nại.</p>
          <div className="rounded-lg border border-violet-200 bg-violet-50 px-4 py-3 text-violet-800">
            <p className="text-sm font-semibold">
              Sự phối hợp chặt chẽ giữa các bộ phận chuyên trách và khách hàng sẽ giúp ElectroMart Việt Nam giải quyết triệt để mọi vướng mắc, bảo vệ uy tín và xây dựng môi trường mua sắm an toàn.
            </p>
          </div>
        </div>
      ),
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Banner */}
      <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-violet-900/60">
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage:
              'radial-gradient(circle at 20% 60%, #8b5cf6 0%, transparent 50%), radial-gradient(circle at 80% 20%, #a78bfa 0%, transparent 40%)',
          }}
        />
        <div className="relative mx-auto max-w-5xl px-4 py-12 lg:px-6">
          {/* Breadcrumb */}
          <nav className="mb-5 flex items-center gap-1.5 text-xs text-slate-400">
            <Link to="/" className="transition hover:text-white">Trang chủ</Link>
            <span>/</span>
            <Link to="/about" className="transition hover:text-white">Giới thiệu công ty</Link>
            <span>/</span>
            <span className="text-slate-200">Khiếu nại &amp; Tranh chấp</span>
          </nav>

          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-violet-500 shadow-lg shadow-violet-500/30">
              <Scale className="h-6 w-6 text-white" />
            </div>
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-violet-400">Chính sách</p>
              <h1 className="text-2xl font-bold font-display leading-tight text-white lg:text-3xl">
                Quy trình Giải quyết Khiếu nại & Tranh chấp
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-300">
                Cam kết xử lý minh bạch, khách quan mọi vướng mắc của khách hàng trong quá trình mua sắm, với thời gian tiếp nhận và xử lý rõ ràng.
              </p>
            </div>
          </div>

          {/* Quick stats */}
          <div className="mt-8 grid grid-cols-3 gap-4 border-t border-white/10 pt-6">
            {[
              { label: 'Kênh tiếp nhận', value: 'Đa kênh' },
              { label: 'Phản hồi ban đầu', value: 'Trong 24h' },
              { label: 'Quy trình xử lý', value: '6 Bước' },
            ].map((s) => (
              <div key={s.label} className="text-center">
                <div className="text-2xl font-bold text-violet-400">{s.value}</div>
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
                    ? 'border-violet-200 bg-white shadow-md shadow-violet-500/5'
                    : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm'
                }`}
              >
                <button
                  id={`dispute-section-${section.number}`}
                  onClick={() => toggle(section.id)}
                  className="flex w-full items-center gap-4 px-5 py-4 text-left"
                  aria-expanded={isOpen}
                >
                  <div
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors ${
                      isOpen ? 'bg-violet-500 text-white' : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    {section.icon}
                  </div>
                  <div className="flex-1">
                    <div className="mb-0.5">
                      <span className={`text-xs font-bold ${isOpen ? 'text-violet-600' : 'text-slate-400'}`}>
                        Điều {section.number}
                      </span>
                    </div>
                    <div className={`text-sm font-semibold leading-tight ${isOpen ? 'text-violet-700' : 'text-slate-800'}`}>
                      {section.title}
                    </div>
                  </div>
                  <div className={`shrink-0 transition-colors ${isOpen ? 'text-violet-600' : 'text-slate-400'}`}>
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
            to="/return-warranty-policy"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
          >
            Bảo hành, Đổi trả & Kỹ thuật
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
