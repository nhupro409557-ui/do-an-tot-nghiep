import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ChevronDown, ChevronUp, ShoppingCart, CreditCard, Receipt, AlertTriangle,
  BadgeCheck, Clock, FileText, ArrowRight, ShieldCheck, Box, RotateCcw,
  RefreshCcw, Database, Scale, PackageCheck, ListOrdered
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
          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-rose-500" />
          {item}
        </li>
      ))}
    </ul>
  );
}

function ProcessStep({ number, title, children }: { number: number; title: string; children: React.ReactNode }) {
  return (
    <div className="flex gap-4">
      <div className="flex flex-col items-center">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-rose-600 text-xs font-bold text-white shadow-sm">
          {number}
        </div>
        <div className="mt-1 w-0.5 flex-1 bg-rose-100" />
      </div>
      <div className="pb-5 flex-1">
        <p className="mb-1 text-sm font-semibold text-slate-800">{title}</p>
        <div className="text-sm text-slate-600 leading-relaxed">{children}</div>
      </div>
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

export default function PurchasePolicyPage() {
  const [expanded, setExpanded] = useState<string | null>('p-1');
  const toggle = (id: string) => setExpanded((p) => (p === id ? null : id));

  const sections: Section[] = [
    {
      id: 'p-1',
      number: '1',
      title: 'Quy định chung',
      icon: <ShoppingCart className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>ElectroMart Việt Nam trân trọng cảm ơn Quý khách hàng đã tin tưởng và lựa chọn mua sắm tại hệ thống.</p>
          <p>Chính sách mua hàng, thanh toán và hóa đơn được xây dựng nhằm quy định rõ quy trình đặt hàng, xác nhận đơn hàng, phương thức thanh toán, hủy đơn, hoàn tiền và phát hành hóa đơn điện tử đối với các giao dịch phát sinh trên website ElectroMart Việt Nam.</p>
          <p>Chính sách này áp dụng cho tất cả khách hàng thực hiện giao dịch mua sản phẩm hoặc sử dụng dịch vụ tại ElectroMart Việt Nam thông qua website, ứng dụng, tổng đài, cửa hàng hoặc các kênh bán hàng chính thức khác.</p>
          <Note>Khi thực hiện đặt hàng và thanh toán, khách hàng được hiểu là đã đọc, hiểu và đồng ý với các nội dung được quy định trong chính sách này.</Note>
        </div>
      ),
    },
    {
      id: 'p-2',
      number: '2',
      title: 'Quy trình đặt hàng',
      icon: <ListOrdered className="h-5 w-5" />,
      content: (
        <div className="space-y-0 text-sm text-slate-600 leading-relaxed">
          <ProcessStep number={1} title="Tìm kiếm và lựa chọn sản phẩm">
            Khách hàng truy cập website, tìm kiếm sản phẩm và xem thông tin chi tiết: tên, hình ảnh, cấu hình, giá bán, tình trạng hàng hóa, chính sách bảo hành, ưu đãi.
          </ProcessStep>
          <ProcessStep number={2} title="Thêm sản phẩm vào giỏ hàng">
            Thêm sản phẩm vào giỏ hàng, kiểm tra lại số lượng, giá bán, khuyến mãi, mã giảm giá, điểm thưởng.
          </ProcessStep>
          <ProcessStep number={3} title="Cung cấp thông tin nhận hàng">
            Điền họ tên người nhận, số điện thoại, địa chỉ giao hàng, email, ghi chú và yêu cầu xuất hóa đơn (nếu có).
          </ProcessStep>
          <ProcessStep number={4} title="Lựa chọn phương thức thanh toán">
            Chọn phương thức thanh toán phù hợp được ElectroMart Việt Nam hỗ trợ.
          </ProcessStep>
          <ProcessStep number={5} title="Xác nhận đơn hàng">
            Hệ thống ghi nhận đơn hàng và gửi thông báo xác nhận qua website, email, tin nhắn hoặc tài khoản người dùng.
          </ProcessStep>
          <ProcessStep number={6} title="Xử lý và giao hàng">
            ElectroMart Việt Nam kiểm tra thông tin, xác nhận tình trạng, xử lý thanh toán và chuyển đơn sang bộ phận đóng gói/giao hàng.
          </ProcessStep>
        </div>
      ),
    },
    {
      id: 'p-3',
      number: '3',
      title: 'Xác nhận đơn hàng',
      icon: <PackageCheck className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <p>Đơn hàng chỉ được xem là hợp lệ khi đáp ứng đầy đủ các điều kiện:</p>
          <BulletList items={[
            'Thông tin khách hàng được cung cấp đầy đủ và có thể liên hệ xác minh.',
            'Sản phẩm còn hàng hoặc có thể cung ứng theo thời gian dự kiến.',
            'Giá bán, chương trình khuyến mãi và hình thức thanh toán được hệ thống ghi nhận hợp lệ.',
            'Đơn hàng không có dấu hiệu gian lận, đặt ảo, lợi dụng mã giảm giá hoặc vi phạm chính sách.'
          ]} />
          <div className="mt-4">
            <h4 className="mb-2 font-bold text-slate-800">Các trường hợp từ chối/hủy đơn hàng:</h4>
            <Table
              headers={['Trường hợp', 'Hướng xử lý']}
              rows={[
                ['Sản phẩm hết hàng', 'Thông báo khách hàng và hoàn tiền nếu đã thanh toán'],
                ['Giá bán hiển thị sai do lỗi hệ thống', 'Thông báo lại giá đúng để khách hàng xác nhận hoặc hủy đơn'],
                ['Thông tin khách hàng không chính xác', 'Tạm giữ hoặc hủy đơn nếu không xác minh được'],
                ['Đơn hàng có dấu hiệu gian lận', 'Từ chối xử lý và ghi nhận trên hệ thống'],
                ['Vi phạm chính sách mua hàng', 'Từ chối hoặc hạn chế giao dịch theo quy định'],
              ]}
            />
          </div>
        </div>
      ),
    },
    {
      id: 'p-4',
      number: '4',
      title: 'Phương thức thanh toán',
      icon: <CreditCard className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <div className="mb-4 rounded-xl overflow-hidden border border-slate-100 shadow-sm max-w-md mx-auto bg-slate-50">
            <img src="/images/policies/purchase.png" alt="Phương thức thanh toán an toàn" className="w-full h-auto mix-blend-multiply" />
          </div>
          <p>ElectroMart cung cấp đa dạng phương thức thanh toán nhằm mang lại sự tiện lợi tối đa cho khách hàng:</p>
          <Table
            headers={['Phương thức thanh toán', 'Mô tả']}
            rows={[
              ['Thanh toán khi nhận hàng (COD)', 'Khách hàng thanh toán trực tiếp cho nhân viên giao hàng khi nhận sản phẩm'],
              ['Thanh toán chuyển khoản', 'Chuyển khoản đến tài khoản ngân hàng được ElectroMart Việt Nam công bố'],
              ['Thẻ ATM nội địa', 'Áp dụng đối với thẻ ngân hàng có hỗ trợ thanh toán trực tuyến'],
              ['Thẻ quốc tế', 'Áp dụng đối với thẻ Visa, Mastercard hoặc các loại thẻ quốc tế được hỗ trợ'],
              ['Ví điện tử', 'Tích hợp ví điện tử như MoMo, ZaloPay, VNPay...'],
              ['Cổng thanh toán', 'Giao dịch xử lý qua đơn vị trung gian thanh toán hợp pháp'],
              ['Thanh toán trả góp', 'Áp dụng với sản phẩm đủ điều kiện qua công ty tài chính/ngân hàng liên kết'],
            ]}
          />
        </div>
      ),
    },
    {
      id: 'p-5',
      number: '5',
      title: 'Quy định về thanh toán trực tuyến',
      icon: <ShieldCheck className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Đơn hàng thanh toán trực tuyến chỉ được xử lý sau khi hệ thống ghi nhận trạng thái thanh toán thành công hoặc có xác nhận hợp lệ từ cổng thanh toán, ngân hàng, ví điện tử.</p>
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3">
            <p className="font-semibold text-rose-800">Trường hợp đã thanh toán nhưng chưa cập nhật:</p>
            <p className="mt-1 text-rose-700">Khách hàng cần liên hệ CSKH và cung cấp: Mã đơn hàng, Số tiền, Thời gian, Phương thức thanh toán, Mã giao dịch/Ảnh chụp chứng từ.</p>
          </div>
          <p>Thông tin thẻ thanh toán <strong>không được lưu trực tiếp</strong> trên hệ thống ElectroMart Việt Nam. Hệ thống chỉ lưu các thông tin phục vụ đối soát (mã đơn, mã giao dịch, thời gian, trạng thái).</p>
        </div>
      ),
    },
    {
      id: 'p-6',
      number: '6',
      title: 'Quy định về thanh toán trả góp',
      icon: <BadgeCheck className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Thanh toán trả góp áp dụng cho các sản phẩm đủ điều kiện theo quy định của ElectroMart Việt Nam và đơn vị tài chính/ngân hàng liên kết.</p>
          <BulletList items={[
            'Khách hàng cung cấp hồ sơ theo yêu cầu của đơn vị xét duyệt. Việc phê duyệt do công ty tài chính/ngân hàng thực hiện.',
            'ElectroMart Việt Nam không cam kết hồ sơ trả góp chắc chắn được duyệt.',
            'Đơn hàng chỉ được xác nhận sau khi hồ sơ được chấp thuận và ghi nhận hợp lệ.',
            'Trường hợp hủy đơn, hoàn trả: Việc xử lý khoản vay, phí, lãi suất, hoàn tiền được thực hiện theo quy định của đơn vị tài chính liên kết.',
          ]} />
        </div>
      ),
    },
    {
      id: 'p-7',
      number: '7',
      title: 'Chính sách hủy đơn hàng',
      icon: <Box className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Trạng thái đơn hàng', 'Quy định hủy đơn']}
            rows={[
              ['Chờ xác nhận', 'Có thể hủy trực tiếp trên hệ thống hoặc liên hệ CSKH'],
              ['Đã xác nhận, chưa đóng gói', 'Yêu cầu hủy, ElectroMart kiểm tra và xác nhận'],
              ['Đã đóng gói, chưa giao', 'Có thể hủy nếu chưa phát sinh chi phí vận hành đặc biệt'],
              ['Đang giao hàng', 'Hủy theo quy trình từ chối nhận hàng hoặc hoàn hàng'],
              ['Đã giao thành công', 'Không áp dụng hủy đơn; thực hiện theo chính sách đổi trả'],
              ['Đơn hàng trả góp', 'Hủy theo quy định của hệ thống và đơn vị tài chính'],
              ['Đơn hàng đặt cọc/đặt trước', 'Hủy theo điều kiện đã công bố tại thời điểm mua'],
            ]}
          />
          <p className="font-semibold text-slate-800">ElectroMart Việt Nam có quyền hủy đơn hàng trong các trường hợp:</p>
          <BulletList items={[
            'Sản phẩm hết hàng hoặc không thể cung ứng.',
            'Cung cấp thông tin sai hoặc không thể liên hệ xác nhận.',
            'Lỗi giá, lỗi khuyến mãi hoặc lỗi kỹ thuật nghiêm trọng trên hệ thống.',
            'Đơn hàng có dấu hiệu gian lận, trục lợi mã giảm giá.',
            'Khách hàng không nhận hàng nhiều lần hoặc lịch sử giao dịch không phù hợp.',
          ]} />
        </div>
      ),
    },
    {
      id: 'p-8',
      number: '8',
      title: 'Chính sách hoàn tiền',
      icon: <RotateCcw className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <div className="mb-4 rounded-xl overflow-hidden border border-slate-100 shadow-sm max-w-md mx-auto bg-slate-50">
            <img src="/images/policies/payment.png" alt="Hoàn tiền nhanh chóng" className="w-full h-auto mix-blend-multiply" />
          </div>
          <p>Việc hoàn tiền được thực hiện trong các trường hợp: đơn hàng bị hủy hợp lệ, hết hàng, thanh toán trùng, lỗi hệ thống, đủ điều kiện đổi trả...</p>
          <Table
            headers={['Phương thức thanh toán ban đầu', 'Hình thức hoàn tiền']}
            rows={[
              ['Tiền mặt', 'Hoàn tiền mặt hoặc chuyển khoản'],
              ['Chuyển khoản ngân hàng', 'Hoàn về tài khoản ngân hàng của người mua'],
              ['Thẻ ATM/thẻ quốc tế', 'Hoàn qua cổng thanh toán hoặc tài khoản liên kết'],
              ['Ví điện tử', 'Hoàn về ví điện tử đã thanh toán'],
              ['Cổng thanh toán trực tuyến', 'Hoàn qua cổng thanh toán/quy trình đối soát'],
              ['Trả góp', 'Xử lý theo quy định công ty tài chính/ngân hàng'],
            ]}
          />
          <div className="flex items-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-rose-800">
            <Clock className="h-5 w-5 shrink-0 text-rose-600" />
            <span>Thời gian hoàn tiền dự kiến từ <strong>03 đến 10 ngày làm việc</strong>, tùy thuộc vào phương thức và đối tác liên kết.</span>
          </div>
        </div>
      ),
    },
    {
      id: 'p-9',
      number: '9',
      title: 'Chính sách đặt cọc và đặt trước',
      icon: <Clock className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <p>Áp dụng cho sản phẩm mới ra mắt, giới hạn số lượng hoặc cần đặt trước. Khách hàng thanh toán trước khoản tiền để xác nhận nhu cầu và ưu tiên giữ hàng.</p>
          <Table
            headers={['Trường thông tin', 'Nội dung']}
            rows={[
              ['Mã đơn đặt cọc', 'Mã định danh giao dịch đặt cọc'],
              ['Sản phẩm đặt trước', 'Tên sản phẩm, phiên bản, màu sắc, dung lượng'],
              ['Số tiền đặt cọc', 'Khoản tiền khách hàng đã thanh toán'],
              ['Thời gian giữ hàng', 'Thời hạn hoàn tất thanh toán'],
              ['Điều kiện hoàn/mất cọc', 'Trường hợp được hoàn hoặc mất cọc'],
            ]}
          />
          <Note>Nếu ElectroMart không thể cung cấp sản phẩm đúng cam kết (hết hàng, chậm hàng), khách hàng được hoàn cọc. Nếu khách hàng tự ý hủy sau thời hạn hoặc không thanh toán đúng hạn, khoản cọc có thể không được hoàn lại tùy điều kiện đã công bố.</Note>
        </div>
      ),
    },
    {
      id: 'p-10',
      number: '10',
      title: 'Chính sách xuất hóa đơn VAT',
      icon: <Receipt className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>ElectroMart Việt Nam hỗ trợ phát hành hóa đơn giá trị gia tăng (VAT/hóa đơn điện tử) cho giao dịch hợp lệ theo quy định pháp luật.</p>
          <BulletList items={[
            'Mua trực tiếp: Phát hành từ thời điểm hoàn tất thanh toán và hệ thống ghi nhận thành công.',
            'Mua trực tuyến: Phát hành sau khi xác nhận thanh toán hoặc trạng thái cập nhật "Giao hàng thành công".',
          ]} />
        </div>
      ),
    },
    {
      id: 'p-11',
      number: '11',
      title: 'Thông tin cung cấp xuất hóa đơn',
      icon: <FileText className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Đối tượng', 'Thông tin cần cung cấp']}
            rows={[
              ['Cá nhân', 'Họ tên, số điện thoại, email, địa chỉ liên hệ'],
              ['Hộ kinh doanh', 'Họ tên, SĐT, email, CCCD/mã định danh, MST, địa chỉ KD'],
              ['Doanh nghiệp', 'Tên đơn vị, MST, địa chỉ, email, SĐT, người đại diện'],
            ]}
          />
          <p>Nếu khách hàng không cung cấp thông tin xuất hóa đơn riêng, hệ thống có thể mặc định phát hành hóa đơn theo thông tin trên đơn đặt hàng hoặc tài khoản.</p>
        </div>
      ),
    },
    {
      id: 'p-12',
      number: '12',
      title: 'Hình thức nhận hóa đơn',
      icon: <ArrowRight className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Hóa đơn điện tử được gửi qua:</p>
          <BulletList items={[
            'Email đã đăng ký',
            'Tài khoản người dùng (mục Đơn hàng)',
            'Tin nhắn/Zalo (nếu có tích hợp)',
            'Liên hệ CSKH để được hỗ trợ tra cứu',
          ]} />
          <p className="font-semibold text-slate-800">Thời gian gửi bản thể hiện hóa đơn dự kiến trong vòng 24 giờ sau khi phát hành thành công.</p>
        </div>
      ),
    },
    {
      id: 'p-13',
      number: '13',
      title: 'Điều chỉnh/Thay thế hóa đơn',
      icon: <RefreshCcw className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Trường hợp sai sót', 'Hướng xử lý']}
            rows={[
              ['Sai tên người mua', 'Điều chỉnh thông tin nếu đủ điều kiện'],
              ['Sai email', 'Cập nhật và gửi lại bản thể hiện'],
              ['Sai mã số thuế', 'Lập hóa đơn điều chỉnh/thay thế'],
              ['Sai địa chỉ đơn vị', 'Điều chỉnh/thay thế tùy mức độ'],
              ['Sai giá trị, thuế, số lượng', 'Lập hóa đơn điều chỉnh/thay thế sau đối soát'],
              ['Đổi trả, hoàn tiền', 'Điều chỉnh hóa đơn theo giá trị thực tế'],
            ]}
          />
        </div>
      ),
    },
    {
      id: 'p-14',
      number: '14',
      title: 'Hóa đơn khi đổi trả/hoàn tiền',
      icon: <RotateCcw className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Giao dịch đổi trả/nhập lại chỉ được xử lý sau khi hoàn tất đối soát hóa đơn và chứng từ liên quan.</p>
          <p>Khách hàng cần phối hợp cung cấp mã tra cứu hóa đơn, biên bản trả hàng, biên bản điều chỉnh giảm giá trị (đối với doanh nghiệp/hộ kinh doanh).</p>
          <Note>Nếu không cung cấp đủ chứng từ, ElectroMart có quyền tạm hoãn hoàn tiền/nhập lại sản phẩm cho đến khi hồ sơ hoàn tất.</Note>
        </div>
      ),
    },
    {
      id: 'p-15',
      number: '15',
      title: 'Trách nhiệm khách hàng',
      icon: <AlertTriangle className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList items={[
            'Cung cấp thông tin đặt hàng, thanh toán và xuất hóa đơn chính xác, hợp pháp.',
            'Kiểm tra kỹ thông tin sản phẩm, giá bán, số lượng, mã giảm giá, phương thức thanh toán trước khi xác nhận đơn.',
            'Bảo mật tài khoản, mật khẩu, OTP, thông tin thẻ/ví điện tử.',
            'Phối hợp với ElectroMart trong xác minh giao dịch, xử lý thanh toán, hoàn tiền, điều chỉnh hóa đơn.',
          ]} />
        </div>
      ),
    },
    {
      id: 'p-16',
      number: '16',
      title: 'Trách nhiệm của ElectroMart Việt Nam',
      icon: <BadgeCheck className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList items={[
            'Cung cấp thông tin sản phẩm, giá bán, thanh toán, điều kiện giao dịch minh bạch.',
            'Tiếp nhận, xác nhận và xử lý đơn hàng theo đúng quy trình đã công bố.',
            'Bảo mật thông tin giao dịch, thanh toán, hóa đơn và dữ liệu cá nhân theo chính sách bảo mật.',
            'Hỗ trợ khách hàng trong các trường hợp thanh toán lỗi, hoàn tiền, hủy đơn, xuất/điều chỉnh hóa đơn.',
            'Kiểm tra, khắc phục và đưa ra phương án xử lý bảo đảm quyền lợi khách hàng nếu lỗi phát sinh từ hệ thống.',
          ]} />
        </div>
      ),
    },
    {
      id: 'p-17',
      number: '17',
      title: 'Lưu trữ dữ liệu giao dịch',
      icon: <Database className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Trường dữ liệu', 'Nội dung']}
            rows={[
              ['Mã đơn hàng / KH', 'Mã định danh giao dịch và thông tin khách hàng'],
              ['Thông tin sản phẩm', 'Tên, số lượng, giá bán, phiên bản'],
              ['Thanh toán', 'Phương thức, trạng thái, mã giao dịch từ NH/Cổng TT'],
              ['Trạng thái đơn hàng', 'Chờ xác nhận, đang giao, thành công, đã hủy...'],
              ['Thông tin hóa đơn', 'Mã hóa đơn, trạng thái phát hành/điều chỉnh'],
              ['Lịch sử xử lý', 'Cập nhật, hủy đơn, hoàn tiền, người phụ trách'],
            ]}
          />
          <p>Lưu trữ dữ liệu giúp đảm bảo tính minh bạch, hỗ trợ quản trị đơn hàng, kiểm soát rủi ro, xử lý hoàn tiền và giải quyết khiếu nại.</p>
        </div>
      ),
    },
    {
      id: 'p-18',
      number: '18',
      title: 'Điều khoản áp dụng',
      icon: <Scale className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Chính sách này có thể được điều chỉnh, bổ sung tùy theo yêu cầu vận hành, thay đổi của hệ thống đối tác thanh toán hoặc quy định pháp luật.</p>
          <p>Mọi thay đổi quan trọng sẽ được công bố trên website. Việc khách hàng tiếp tục sử dụng dịch vụ được hiểu là đã đọc, hiểu và đồng ý với nội dung sửa đổi.</p>
        </div>
      ),
    },
    {
      id: 'p-19',
      number: '19',
      title: 'Kết luận',
      icon: <ShieldCheck className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Chính sách mua hàng, thanh toán và hóa đơn được xây dựng nhằm chuẩn hóa toàn bộ quá trình giao dịch từ khi đặt hàng đến khi hoàn tất thanh toán, phát hành hóa đơn hoặc hoàn tiền.</p>
          <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3">
            <p className="text-sm font-semibold text-rose-800">
              Việc quy định rõ các quy trình này giúp hệ thống vận hành minh bạch, hạn chế tranh chấp và nâng cao trải nghiệm mua sắm trên nền tảng ElectroMart Việt Nam.
            </p>
          </div>
        </div>
      ),
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Banner */}
      <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-rose-900/60">
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage:
              'radial-gradient(circle at 20% 60%, #f43f5e 0%, transparent 50%), radial-gradient(circle at 80% 20%, #e11d48 0%, transparent 40%)',
          }}
        />
        <div className="relative mx-auto max-w-5xl px-4 py-12 lg:px-6">
          {/* Breadcrumb */}
          <nav className="mb-5 flex items-center gap-1.5 text-xs text-slate-400">
            <Link to="/" className="transition hover:text-white">Trang chủ</Link>
            <span>/</span>
            <Link to="/about" className="transition hover:text-white">Giới thiệu công ty</Link>
            <span>/</span>
            <span className="text-slate-200">Mua hàng &amp; Thanh toán</span>
          </nav>

          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-rose-600 shadow-lg shadow-rose-500/30">
              <ShoppingCart className="h-6 w-6 text-white" />
            </div>
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-rose-400">Chính sách</p>
              <h1 className="text-2xl font-bold font-display leading-tight text-white lg:text-3xl">
                Chính sách mua hàng &amp; thanh toán
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-300">
                Quy trình rõ ràng và an toàn từ lúc đặt hàng, xác nhận, thanh toán cho đến khi phát hành hóa đơn VAT, đảm bảo quyền lợi tối đa cho mọi giao dịch tại ElectroMart Việt Nam.
              </p>
            </div>
          </div>

          {/* Quick stats */}
          <div className="mt-8 grid grid-cols-3 gap-4 border-t border-white/10 pt-6">
            {[
              { label: 'Bước đặt hàng', value: '6' },
              { label: 'Phương thức thanh toán', value: '7' },
              { label: 'Hoàn tiền dự kiến', value: '3-10 ngày' },
            ].map((s) => (
              <div key={s.label} className="text-center">
                <div className="text-2xl font-bold text-rose-400">{s.value}</div>
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
                    ? 'border-rose-200 bg-white shadow-md shadow-rose-500/5'
                    : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm'
                }`}
              >
                <button
                  id={`purchase-section-${section.number}`}
                  onClick={() => toggle(section.id)}
                  className="flex w-full items-center gap-4 px-5 py-4 text-left"
                  aria-expanded={isOpen}
                >
                  <div
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors ${
                      isOpen ? 'bg-rose-600 text-white' : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    {section.icon}
                  </div>
                  <div className="flex-1">
                    <div className="mb-0.5">
                      <span className={`text-xs font-bold ${isOpen ? 'text-rose-600' : 'text-slate-400'}`}>
                        Điều {section.number}
                      </span>
                    </div>
                    <div className={`text-sm font-semibold leading-tight ${isOpen ? 'text-rose-700' : 'text-slate-800'}`}>
                      {section.title}
                    </div>
                  </div>
                  <div className={`shrink-0 transition-colors ${isOpen ? 'text-rose-600' : 'text-slate-400'}`}>
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
            to="/invoice"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
          >
            Chính sách hóa đơn VAT
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
