import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ChevronDown, ChevronUp, Receipt, Calendar, User, Send,
  RefreshCw, AlertTriangle, ArrowRight, Phone, BadgeCheck, FileText,
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
                    j === 0 ? 'whitespace-nowrap font-semibold text-slate-700' : ''
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
          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-orange-500" />
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

export default function InvoicePage() {
  const [expanded, setExpanded] = useState<string | null>('i-1');
  const toggle = (id: string) => setExpanded((p) => (p === id ? null : id));

  const sections: Section[] = [
    {
      id: 'i-1',
      number: '1',
      title: 'Quy định chung',
      icon: <Receipt className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>
            ElectroMart Việt Nam trân trọng cảm ơn Quý khách hàng đã tin tưởng và mua sắm tại hệ thống.
          </p>
          <p>
            Khi khách hàng mua hàng hóa hoặc sử dụng dịch vụ tại ElectroMart Việt Nam, hệ thống sẽ hỗ trợ phát hành hóa đơn giá trị gia tăng (hóa đơn VAT / hóa đơn điện tử) theo đúng quy định của pháp luật hiện hành.
          </p>
          <p>
            Việc xuất hóa đơn được thực hiện nhằm bảo đảm tính minh bạch trong giao dịch, phục vụ nhu cầu kê khai chi phí, hạch toán kế toán, bảo hành sản phẩm, đổi trả hàng hóa và các thủ tục liên quan đến quyền lợi của khách hàng.
          </p>
        </div>
      ),
    },
    {
      id: 'i-2',
      number: '2',
      title: 'Thời điểm phát hành hóa đơn',
      icon: <Calendar className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <div className="space-y-2">
            <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
              <p className="font-semibold text-slate-700">Mua trực tiếp tại cửa hàng</p>
              <p className="mt-1">Hóa đơn được phát hành từ thời điểm khách hàng hoàn tất thanh toán và hệ thống ghi nhận giao dịch thành công.</p>
            </div>
            <div className="rounded-lg border border-slate-100 bg-slate-50 p-3">
              <p className="font-semibold text-slate-700">Mua trực tuyến</p>
              <p className="mt-1">Hóa đơn được phát hành sau khi đơn hàng được xác nhận thanh toán thành công hoặc sau khi trạng thái cập nhật là <span className="rounded bg-orange-100 px-1.5 py-0.5 text-xs font-bold text-orange-700">"Giao hàng thành công"</span>, tùy theo phương thức thanh toán và quy trình xử lý đơn hàng.</p>
            </div>
          </div>
          <Note>
            Nếu khách hàng chưa nhận được hóa đơn sau khi giao dịch đã hoàn tất, vui lòng liên hệ bộ phận Chăm sóc khách hàng của ElectroMart Việt Nam để được kiểm tra và hỗ trợ xử lý.
          </Note>
        </div>
      ),
    },
    {
      id: 'i-3',
      number: '3',
      title: 'Thông tin cần cung cấp để xuất hóa đơn',
      icon: <User className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Đối tượng khách hàng', 'Thông tin cần cung cấp']}
            rows={[
              ['Khách hàng cá nhân', 'Họ tên người mua, số điện thoại, email nhận hóa đơn, địa chỉ liên hệ nếu cần'],
              ['Cá nhân kinh doanh / hộ kinh doanh', 'Họ tên, số điện thoại, email, số CCCD hoặc mã định danh cá nhân, mã số thuế nếu có, địa chỉ kinh doanh'],
              ['Doanh nghiệp / tổ chức', 'Tên đơn vị, mã số thuế, địa chỉ đơn vị, email nhận hóa đơn, số điện thoại, người đại diện hoặc người nhận hóa đơn'],
            ]}
          />
          <Note>
            Khách hàng có trách nhiệm cung cấp thông tin chính xác, đầy đủ và hợp pháp. ElectroMart Việt Nam không chịu trách nhiệm đối với các sai sót phát sinh do khách hàng cung cấp thông tin không đúng tại thời điểm yêu cầu xuất hóa đơn.
          </Note>
        </div>
      ),
    },
    {
      id: 'i-4',
      number: '4',
      title: 'Trường hợp không cung cấp thông tin xuất hóa đơn',
      icon: <FileText className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>
            Trường hợp khách hàng không cung cấp thông tin xuất hóa đơn riêng, ElectroMart Việt Nam có thể mặc định phát hành hóa đơn theo thông tin đã được ghi nhận trên đơn đặt hàng, phiếu bán hàng hoặc tài khoản khách hàng trên hệ thống.
          </p>
          <p>
            Các thông tin mặc định có thể bao gồm họ tên người mua, số điện thoại, email, địa chỉ nhận hàng và các thông tin liên quan đến giao dịch.
          </p>
          <Note>
            Khách hàng cần kiểm tra kỹ thông tin đơn hàng trước khi xác nhận mua hàng để hạn chế sai sót trong quá trình phát hành hóa đơn.
          </Note>
        </div>
      ),
    },
    {
      id: 'i-5',
      number: '5',
      title: 'Hình thức nhận hóa đơn',
      icon: <Send className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <p>Hóa đơn VAT của ElectroMart Việt Nam được phát hành dưới hình thức <strong>hóa đơn điện tử</strong> và gửi đến khách hàng qua một trong các phương thức:</p>
          <Table
            headers={['Phương thức nhận hóa đơn', 'Mô tả']}
            rows={[
              ['Email', 'Gửi hóa đơn đến địa chỉ email khách hàng đã cung cấp'],
              ['Tài khoản người dùng', 'Tra cứu hóa đơn trong mục đơn hàng nếu hệ thống hỗ trợ'],
              ['Tin nhắn / Zalo', 'Gửi đường dẫn tra cứu hóa đơn nếu ElectroMart Việt Nam có tích hợp'],
              ['Bộ phận hỗ trợ', 'Liên hệ chăm sóc khách hàng để được hỗ trợ tra cứu lại hóa đơn'],
            ]}
          />
          <div className="flex items-center gap-2 rounded-lg border border-orange-200 bg-orange-50 px-4 py-3">
            <BadgeCheck className="h-4 w-4 shrink-0 text-orange-600" />
            <p className="text-sm text-orange-800">
              Thời gian gửi bản thể hiện hóa đơn dự kiến <strong>trong vòng 24 giờ</strong> kể từ thời điểm hóa đơn được phát hành thành công.
            </p>
          </div>
        </div>
      ),
    },
    {
      id: 'i-6',
      number: '6',
      title: 'Điều chỉnh hoặc thay thế hóa đơn sai sót',
      icon: <RefreshCw className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <p>
            Hóa đơn VAT sau khi đã phát hành không được tự ý hủy hoặc xóa bỏ nếu không có căn cứ hợp lệ. Trường hợp có sai sót, ElectroMart Việt Nam sẽ thực hiện điều chỉnh hoặc thay thế hóa đơn theo quy định pháp luật về hóa đơn điện tử.
          </p>
          <Table
            headers={['Trường hợp sai sót', 'Hướng xử lý']}
            rows={[
              ['Sai tên người mua hàng', 'Điều chỉnh thông tin hóa đơn nếu đủ điều kiện'],
              ['Sai email nhận hóa đơn', 'Cập nhật và gửi lại bản thể hiện hóa đơn'],
              ['Sai mã số thuế', 'Lập hóa đơn điều chỉnh hoặc thay thế theo quy định'],
              ['Sai địa chỉ đơn vị', 'Điều chỉnh hoặc thay thế hóa đơn tùy mức độ sai sót'],
              ['Sai giá trị, thuế suất, số lượng', 'Lập hóa đơn điều chỉnh/thay thế sau khi đối soát giao dịch'],
              ['Đổi trả hoặc hoàn tiền', 'Điều chỉnh hóa đơn theo giá trị giao dịch thực tế'],
            ]}
          />
          <Note>
            Khách hàng cần kiểm tra và xác nhận toàn bộ thông tin sau khi nhận được hóa đơn. Nếu phát hiện sai sót, vui lòng thông báo cho ElectroMart Việt Nam trong thời gian sớm nhất để được hỗ trợ xử lý.
          </Note>
        </div>
      ),
    },
    {
      id: 'i-7',
      number: '7',
      title: 'Hóa đơn khi đổi trả, nhập lại hoặc hoàn tiền',
      icon: <Receipt className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>
            Đối với các giao dịch phát sinh đổi trả, nhập lại sản phẩm hoặc hoàn tiền, ElectroMart Việt Nam chỉ thực hiện xử lý sau khi hoàn tất việc đối soát hóa đơn và chứng từ liên quan.
          </p>
          <BulletList
            items={[
              'Trường hợp hóa đơn đã được phát hành, khách hàng cần cung cấp thông tin hóa đơn, mã tra cứu hóa đơn điện tử hoặc các chứng từ cần thiết để ElectroMart Việt Nam thực hiện thủ tục điều chỉnh, thay thế hoặc thu hồi hóa đơn.',
              'Đối với khách hàng doanh nghiệp, hộ kinh doanh hoặc cá nhân kinh doanh, khi trả lại hàng hoặc điều chỉnh giá trị giao dịch, cần cung cấp biên bản trả hàng, biên bản điều chỉnh giảm giá trị hóa đơn hoặc tài liệu liên quan nếu được yêu cầu.',
            ]}
          />
          <Note>
            Trường hợp khách hàng không cung cấp đủ chứng từ cần thiết, ElectroMart Việt Nam có quyền tạm hoãn việc hoàn tiền hoặc nhập lại sản phẩm cho đến khi hồ sơ hóa đơn được hoàn tất.
          </Note>
        </div>
      ),
    },
    {
      id: 'i-8',
      number: '8',
      title: 'Trách nhiệm của khách hàng',
      icon: <User className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList
            items={[
              'Cung cấp thông tin xuất hóa đơn chính xác, hợp lệ và đúng thời điểm.',
              'Kiểm tra kỹ thông tin hóa đơn sau khi nhận được bản thể hiện hóa đơn điện tử.',
              'Thông báo kịp thời cho ElectroMart Việt Nam nếu phát hiện sai sót về thông tin người mua, mã số thuế, địa chỉ, giá trị hàng hóa hoặc các nội dung khác trên hóa đơn.',
              'Chịu trách nhiệm đối với các chậm trễ hoặc phát sinh liên quan đến việc cung cấp sai thông tin, thiếu thông tin hoặc không phối hợp trong quá trình điều chỉnh hóa đơn.',
            ]}
          />
        </div>
      ),
    },
    {
      id: 'i-9',
      number: '9',
      title: 'Trách nhiệm của ElectroMart Việt Nam',
      icon: <BadgeCheck className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <div className="grid gap-2 sm:grid-cols-2">
            {[
              'Phát hành hóa đơn VAT cho các giao dịch hợp lệ theo đúng quy định pháp luật.',
              'Bảo mật thông tin hóa đơn, thông tin giao dịch và thông tin khách hàng trong quá trình phát hành, lưu trữ và tra cứu.',
              'Hỗ trợ khách hàng tra cứu, nhận lại, điều chỉnh hoặc thay thế hóa đơn trong trường hợp phát sinh sai sót hợp lệ.',
              'Lưu trữ thông tin hóa đơn, chứng từ kế toán và giao dịch mua hàng để phục vụ đối soát, bảo hành, đổi trả, giải quyết khiếu nại và tuân thủ quy định pháp luật.',
            ].map((item) => (
              <div key={item} className="flex items-start gap-2 rounded-lg border border-orange-100 bg-orange-50 px-3 py-2">
                <BadgeCheck className="mt-0.5 h-4 w-4 shrink-0 text-orange-600" />
                <span className="text-sm text-orange-800">{item}</span>
              </div>
            ))}
          </div>
        </div>
      ),
    },
    {
      id: 'i-10',
      number: '10',
      title: 'Kênh hỗ trợ hóa đơn',
      icon: <Phone className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Kênh hỗ trợ', 'Thông tin']}
            rows={[
              ['Tổng đài chăm sóc khách hàng', '1900 xxxx'],
              ['Email hỗ trợ', 'cskh@electromart.vn'],
              ['Website', 'Mục "Tra cứu hóa đơn" hoặc "Trung tâm hỗ trợ"'],
              ['Tài khoản người dùng', 'Mục "Đơn hàng của tôi" nếu hệ thống hỗ trợ'],
              ['Điểm bán / điểm tiếp nhận', 'Áp dụng khi ElectroMart Việt Nam có cửa hàng hoặc văn phòng hỗ trợ'],
            ]}
          />
        </div>
      ),
    },
    {
      id: 'i-11',
      number: '11',
      title: 'Kết luận',
      icon: <BadgeCheck className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>
            Chính sách xuất hóa đơn VAT của ElectroMart Việt Nam được xây dựng nhằm bảo đảm tính minh bạch, hợp pháp và thuận tiện trong quá trình mua bán hàng hóa, dịch vụ trên hệ thống.
          </p>
          <div className="rounded-lg border border-orange-200 bg-orange-50 px-4 py-3">
            <p className="text-sm font-semibold text-orange-800">
              Việc chuẩn hóa quy trình phát hành, gửi, điều chỉnh và lưu trữ hóa đơn giúp bảo vệ quyền lợi của khách hàng, đồng thời hỗ trợ công tác kế toán, quản trị và vận hành thương mại điện tử một cách chính xác, nhất quán.
            </p>
          </div>
        </div>
      ),
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Banner */}
      <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-orange-900/50">
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage:
              'radial-gradient(circle at 20% 60%, #f97316 0%, transparent 50%), radial-gradient(circle at 80% 20%, #fbbf24 0%, transparent 40%)',
          }}
        />
        <div className="relative mx-auto max-w-5xl px-4 py-12 lg:px-6">
          {/* Breadcrumb */}
          <nav className="mb-5 flex items-center gap-1.5 text-xs text-slate-400">
            <Link to="/" className="transition hover:text-white">Trang chủ</Link>
            <span>/</span>
            <Link to="/about" className="transition hover:text-white">Giới thiệu công ty</Link>
            <span>/</span>
            <span className="text-slate-200">Chính sách xuất hóa đơn VAT</span>
          </nav>

          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-orange-600 shadow-lg shadow-orange-500/30">
              <Receipt className="h-6 w-6 text-white" />
            </div>
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-orange-400">Chính sách</p>
              <h1 className="text-2xl font-bold font-display leading-tight text-white lg:text-3xl">
                Chính sách xuất hóa đơn VAT
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-300">
                Quy định về thời điểm phát hành, hình thức nhận, điều chỉnh hóa đơn và trách nhiệm các bên — đảm bảo mọi giao dịch tại ElectroMart Việt Nam đều được lập hóa đơn đúng quy định pháp luật.
              </p>
            </div>
          </div>

          {/* Quick stats */}
          <div className="mt-8 grid grid-cols-3 gap-4 border-t border-white/10 pt-6">
            {[
              { label: 'Đối tượng xuất hóa đơn', value: '3' },
              { label: 'Hình thức nhận', value: '4' },
              { label: 'Thời gian gửi hóa đơn', value: '24h' },
            ].map((s) => (
              <div key={s.label} className="text-center">
                <div className="text-2xl font-bold text-orange-400">{s.value}</div>
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
                    ? 'border-orange-200 bg-white shadow-md shadow-orange-500/5'
                    : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm'
                }`}
              >
                <button
                  id={`invoice-section-${section.number}`}
                  onClick={() => toggle(section.id)}
                  className="flex w-full items-center gap-4 px-5 py-4 text-left"
                  aria-expanded={isOpen}
                >
                  <div
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors ${
                      isOpen ? 'bg-orange-600 text-white' : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    {section.icon}
                  </div>
                  <div className="flex-1">
                    <div className="mb-0.5">
                      <span className={`text-xs font-bold ${isOpen ? 'text-orange-600' : 'text-slate-400'}`}>
                        Điều {section.number}
                      </span>
                    </div>
                    <div className={`text-sm font-semibold leading-tight ${isOpen ? 'text-orange-700' : 'text-slate-800'}`}>
                      {section.title}
                    </div>
                  </div>
                  <div className={`shrink-0 transition-colors ${isOpen ? 'text-orange-600' : 'text-slate-400'}`}>
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
            Chính sách bảo hành
          </Link>
          <Link
            to="/dispute"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
          >
            Giải quyết khiếu nại
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
