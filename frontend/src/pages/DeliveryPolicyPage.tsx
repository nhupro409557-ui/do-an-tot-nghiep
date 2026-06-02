import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ChevronDown, ChevronUp, Truck, MapPin, Clock, DollarSign, PackageSearch,
  Eye, XOctagon, AlertTriangle, RefreshCcw, Edit, UserCheck, Wrench,
  Users, ShieldCheck, FileText, ArrowRight, PackageX, Database
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
          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-sky-500" />
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

export default function DeliveryPolicyPage() {
  const [expanded, setExpanded] = useState<string | null>('d-1');
  const toggle = (id: string) => setExpanded((p) => (p === id ? null : id));

  const sections: Section[] = [
    {
      id: 'd-1',
      number: '1',
      title: 'Quy định chung',
      icon: <Truck className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>ElectroMart Việt Nam xây dựng chính sách giao hàng, kiểm hàng và nhận hàng nhằm quy định rõ trách nhiệm của hệ thống, khách hàng và đơn vị vận chuyển trong quá trình giao nhận sản phẩm.</p>
          <p>Chính sách này áp dụng đối với các đơn hàng được đặt mua thông qua website, ứng dụng, tổng đài, cửa hàng hoặc các kênh bán hàng chính thức khác của ElectroMart Việt Nam.</p>
          <p>Mục tiêu của chính sách là bảo đảm sản phẩm được giao đến khách hàng đúng thông tin đơn hàng, đúng thời gian dự kiến, đúng tình trạng hàng hóa và hạn chế tối đa các tranh chấp phát sinh trong quá trình giao nhận.</p>
        </div>
      ),
    },
    {
      id: 'd-2',
      number: '2',
      title: 'Phạm vi giao hàng',
      icon: <MapPin className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <div className="mb-4 rounded-xl overflow-hidden border border-slate-100 shadow-sm max-w-md mx-auto bg-slate-50">
            <img src="/images/policies/delivery.png" alt="Giao hàng nhanh chóng" className="w-full h-auto mix-blend-multiply" />
          </div>
          <p>ElectroMart Việt Nam hỗ trợ giao hàng đến địa chỉ khách hàng cung cấp trong quá trình đặt hàng, tùy theo phạm vi hoạt động và khả năng phục vụ của đơn vị vận chuyển.</p>
          <Table
            headers={['Khu vực giao hàng', 'Hình thức hỗ trợ']}
            rows={[
              ['Nội thành các thành phố lớn', 'Giao hàng tiêu chuẩn hoặc giao nhanh nếu có hỗ trợ'],
              ['Ngoại thành, huyện, thị xã', 'Giao hàng thông qua đơn vị vận chuyển liên kết'],
              ['Tỉnh/thành khác', 'Giao hàng toàn quốc tùy theo sản phẩm và khu vực phục vụ'],
              ['Khu vực hạn chế giao hàng', 'ElectroMart sẽ thông báo riêng nếu đơn vị vận chuyển không hỗ trợ'],
            ]}
          />
          <Note>Một số sản phẩm có kích thước lớn, giá trị cao hoặc yêu cầu lắp đặt (như tivi, máy tính bàn, màn hình, máy in...) có thể áp dụng phạm vi giao hàng riêng.</Note>
        </div>
      ),
    },
    {
      id: 'd-3',
      number: '3',
      title: 'Thời gian giao hàng',
      icon: <Clock className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <p>Thời gian giao hàng tính từ lúc đơn hàng được xác nhận hợp lệ và chuyển sang trạng thái xử lý giao hàng.</p>
          <Table
            headers={['Khu vực', 'Thời gian giao hàng dự kiến']}
            rows={[
              ['Nội thành cùng khu vực kho/cửa hàng', '01–02 ngày làm việc'],
              ['Ngoại thành hoặc khu vực lân cận', '02–04 ngày làm việc'],
              ['Các tỉnh/thành khác', '03–07 ngày làm việc'],
              ['Khu vực xa, vùng sâu, vùng xa', 'Có thể kéo dài tùy theo đơn vị vận chuyển'],
              ['Sản phẩm đặt trước/đặt cọc', 'Theo thời gian dự kiến được công bố khi đặt hàng'],
            ]}
          />
          <p className="font-semibold text-slate-800">Thời gian giao hàng có thể thay đổi trong các trường hợp:</p>
          <BulletList items={[
            'Khách hàng cung cấp sai hoặc thiếu thông tin nhận hàng.',
            'Không liên hệ được với khách hàng tại thời điểm giao hàng.',
            'Đơn hàng cần xác minh thanh toán hoặc thông tin người nhận.',
            'Sản phẩm cần điều chuyển từ kho khác.',
            'Điều kiện thời tiết, thiên tai, dịch bệnh, sự cố vận chuyển (bất khả kháng).',
            'Đơn hàng phát sinh trong thời gian cao điểm khuyến mãi, lễ, Tết.',
          ]} />
          <p>Trong trường hợp thay đổi, ElectroMart Việt Nam hoặc đơn vị vận chuyển sẽ thông báo qua điện thoại, tin nhắn, email hoặc trạng thái trên hệ thống.</p>
        </div>
      ),
    },
    {
      id: 'd-4',
      number: '4',
      title: 'Phí giao hàng',
      icon: <DollarSign className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Phí giao hàng được xác định dựa trên địa chỉ nhận, kích thước sản phẩm, khối lượng, phương thức giao và chính sách khuyến mãi. Phí này (nếu có) sẽ hiển thị trước khi khách hàng xác nhận đơn hàng.</p>
          <p className="font-semibold text-slate-800">ElectroMart Việt Nam có thể miễn phí giao hàng nếu:</p>
          <BulletList items={[
            'Đơn hàng đạt giá trị tối thiểu theo chương trình khuyến mãi.',
            'Sản phẩm thuộc chương trình miễn phí vận chuyển.',
            'Khách hàng thuộc hạng thành viên được ưu đãi vận chuyển.',
            'Khu vực giao hàng nằm trong phạm vi hỗ trợ miễn phí của hệ thống.',
          ]} />
          <Note>Nếu phát sinh phí giao hàng đặc biệt (giao gấp, ngoài giờ, hàng cồng kềnh, khu vực hạn chế), hệ thống sẽ thông báo cho khách hàng trước khi giao.</Note>
        </div>
      ),
    },
    {
      id: 'd-5',
      number: '5',
      title: 'Quy định kiểm hàng khi nhận',
      icon: <PackageSearch className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <p>Khi nhận hàng, khách hàng có quyền kiểm tra tình trạng bên ngoài kiện hàng trước khi xác nhận với nhân viên giao hàng.</p>
          <Table
            headers={['Nội dung kiểm tra', 'Mục đích']}
            rows={[
              ['Thông tin người nhận', 'Đối chiếu họ tên, số điện thoại, địa chỉ'],
              ['Mã đơn hàng', 'Đối chiếu đơn hàng với thông tin trên hệ thống'],
              ['Tình trạng bao bì', 'Kiểm tra hộp có móp méo, rách, ướt, bị mở hoặc hư hỏng không'],
              ['Tem niêm phong', 'Kiểm tra tem còn nguyên vẹn nếu sản phẩm có niêm phong'],
              ['Số lượng sản phẩm', 'Đối chiếu số lượng với đơn hàng'],
              ['Phụ kiện/quà tặng', 'Kiểm tra theo thông tin đơn hàng nếu được phép kiểm tra'],
            ]}
          />
          <div className="rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sky-800">
            <p className="font-semibold">Lưu ý quan trọng:</p>
            <p className="mt-1 text-sky-700">Đối với sản phẩm điện tử giá trị cao, khách hàng nên <strong>quay video quá trình mở hộp</strong> làm căn cứ đối chiếu. Việc kiểm hàng không đồng nghĩa với thử nghiệm toàn bộ chức năng kỹ thuật. Các lỗi phát sinh sau đó sẽ xử lý theo chính sách bảo hành, đổi trả.</p>
          </div>
        </div>
      ),
    },
    {
      id: 'd-6',
      number: '6',
      title: 'Quy định đồng kiểm',
      icon: <Eye className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Đồng kiểm là quá trình khách hàng cùng nhân viên giao hàng kiểm tra cơ bản tình trạng hàng hóa tại thời điểm giao nhận.</p>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-xl border border-slate-200 p-4">
              <p className="mb-2 font-bold text-sky-700">Phạm vi đồng kiểm bao gồm:</p>
              <BulletList items={[
                'Đúng sản phẩm, đúng màu sắc, đúng phiên bản.',
                'Số lượng sản phẩm trong đơn hàng.',
                'Phụ kiện, quà tặng đi kèm (nếu có).',
                'Tình trạng ngoại quan của sản phẩm và hộp sản phẩm.',
              ]} />
            </div>
            <div className="rounded-xl border border-slate-200 p-4">
              <p className="mb-2 font-bold text-slate-700">Phạm vi KHÔNG bao gồm:</p>
              <BulletList items={[
                'Cài đặt phần mềm chuyên sâu, đăng nhập tài khoản.',
                'Kiểm tra toàn bộ chức năng kỹ thuật nâng cao.',
                'Tháo lắp linh kiện bên trong sản phẩm.',
                'Can thiệp hệ điều hành, phần mềm hoặc cấu hình.',
              ]} />
            </div>
          </div>
          <Note>Nếu đơn vị vận chuyển không hỗ trợ đồng kiểm, khách hàng cần kiểm tra kỹ tình trạng bên ngoài kiện hàng và liên hệ ElectroMart ngay nếu phát hiện bất thường.</Note>
        </div>
      ),
    },
    {
      id: 'd-7',
      number: '7',
      title: 'Trường hợp khách hàng được từ chối nhận hàng',
      icon: <XOctagon className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Trường hợp', 'Hướng xử lý']}
            rows={[
              ['Kiện hàng có dấu hiệu bị mở, rách, ướt, hư hỏng nghiêm trọng', 'Khách hàng từ chối nhận và thông báo ElectroMart Việt Nam'],
              ['Sản phẩm giao sai mẫu mã, màu sắc, phiên bản', 'Từ chối nhận hoặc lập biên bản với đơn vị giao hàng'],
              ['Số lượng sản phẩm không đúng', 'Từ chối nhận hoặc yêu cầu ghi nhận thiếu hàng'],
              ['Thiếu phụ kiện/quà tặng', 'Ghi nhận tình trạng và liên hệ hỗ trợ'],
              ['Giá trị thu tiền khi nhận hàng không đúng', 'Từ chối thanh toán và liên hệ ElectroMart Việt Nam'],
              ['Nhân viên giao hàng yêu cầu thanh toán ngoài giá trị', 'Từ chối giao dịch và phản ánh ngay với hệ thống'],
            ]}
          />
          <p>Khi từ chối nhận hàng, khách hàng cần thông báo lý do cụ thể cho nhân viên giao hàng và liên hệ ElectroMart Việt Nam sớm nhất để được hỗ trợ.</p>
        </div>
      ),
    },
    {
      id: 'd-8',
      number: '8',
      title: 'Trường hợp giao hàng không thành công',
      icon: <PackageX className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Giao hàng không thành công khi đơn vị vận chuyển không thể bàn giao sản phẩm cho khách hàng. Các nguyên nhân thường gặp:</p>
          <BulletList items={[
            'Không liên hệ được với khách hàng hoặc khách hàng không có mặt tại địa chỉ.',
            'Địa chỉ giao hàng không chính xác hoặc không đầy đủ.',
            'Khách hàng từ chối nhận hàng không có lý do hợp lệ.',
            'Khách hàng yêu cầu thay đổi thời gian giao hàng nhiều lần.',
            'Khu vực giao hàng không thể tiếp cận do điều kiện khách quan.',
          ]} />
          <p>Trong trường hợp này, đơn vị vận chuyển hoặc ElectroMart sẽ liên hệ xác nhận phương án giao lại. Nếu sau số lần quy định vẫn không thành công, đơn hàng sẽ chuyển sang hoàn hàng hoặc hủy đơn. ElectroMart sẽ xử lý hoàn tiền (nếu đã thanh toán trước) sau khi hàng trả về kho an toàn.</p>
        </div>
      ),
    },
    {
      id: 'd-9',
      number: '9',
      title: 'Xử lý giao sai, giao thiếu hoặc sản phẩm hư hỏng',
      icon: <AlertTriangle className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <p>Khách hàng cần liên hệ ElectroMart sớm nhất và cung cấp:</p>
          <BulletList items={[
            'Mã đơn hàng, Hình ảnh/video kiện hàng khi nhận.',
            'Hình ảnh tem niêm phong, hộp sản phẩm, sản phẩm bên trong.',
            'Biên bản giao nhận hoặc ghi chú từ đơn vị vận chuyển.',
            'Mô tả chi tiết vấn đề phát sinh.',
          ]} />
          <Table
            headers={['Tình huống', 'Phương án xử lý']}
            rows={[
              ['Giao sai sản phẩm', 'Thu hồi sản phẩm sai và giao lại sản phẩm đúng'],
              ['Giao thiếu sản phẩm/phụ kiện', 'Giao bổ sung phần còn thiếu nếu đủ căn cứ xác minh'],
              ['Hàng bị hư hỏng do vận chuyển', 'Đổi sản phẩm khác nếu lỗi phát sinh trước khi khách nhận hàng'],
              ['Hộp móp nhẹ nhưng sản phẩm không ảnh hưởng', 'Ghi nhận tình trạng và xử lý theo mức độ thực tế'],
              ['Khách hàng không có bằng chứng đối chiếu', 'ElectroMart kiểm tra dữ liệu nội bộ trước khi quyết định xử lý'],
            ]}
          />
        </div>
      ),
    },
    {
      id: 'd-10',
      number: '10',
      title: 'Quy định thay đổi thông tin giao hàng',
      icon: <Edit className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Khách hàng có thể thay đổi thông tin (Họ tên, SĐT, Địa chỉ, Thời gian, Ghi chú) khi đơn hàng <strong>chưa được bàn giao</strong> cho đơn vị vận chuyển.</p>
          <p>Đối với đơn hàng đã bàn giao, việc thay đổi phụ thuộc vào khả năng hỗ trợ của đơn vị vận chuyển và có thể phát sinh thêm phí.</p>
          <Note>ElectroMart có quyền từ chối thay đổi thông tin nếu có dấu hiệu gian lận, không xác minh được chủ đơn hàng hoặc ảnh hưởng an toàn giao dịch.</Note>
        </div>
      ),
    },
    {
      id: 'd-11',
      number: '11',
      title: 'Quy định nhận hàng thay',
      icon: <UserCheck className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Khách hàng có thể ủy quyền nhận thay. Người nhận thay cần cung cấp thông tin xác minh:</p>
          <BulletList items={[
            'Mã đơn hàng, số điện thoại đặt hàng, thông tin người đặt.',
            'Giấy tờ tùy thân nếu sản phẩm giá trị cao hoặc cần xác minh.',
            'Mã OTP giao hàng (nếu có).',
          ]} />
          <p>Khi người nhận thay ký nhận/xác nhận, đơn hàng xem như đã giao thành công. Khách hàng chịu trách nhiệm đối với việc ủy quyền này.</p>
        </div>
      ),
    },
    {
      id: 'd-12',
      number: '12',
      title: 'Quy định đối với sản phẩm cần lắp đặt',
      icon: <Wrench className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <p>Một số sản phẩm (tivi, PC, màn hình, máy in...) có thể cần lắp đặt hoặc kiểm tra cơ bản. ElectroMart hỗ trợ các hình thức:</p>
          <Table
            headers={['Hình thức hỗ trợ', 'Nội dung']}
            rows={[
              ['Giao hàng không lắp đặt', 'Chỉ bàn giao sản phẩm theo đơn hàng'],
              ['Hỗ trợ lắp đặt cơ bản', 'Kết nối, lắp chân đế, kiểm tra nguồn, hướng dẫn sử dụng cơ bản'],
              ['Hỗ trợ kỹ thuật theo yêu cầu', 'Cài đặt, cấu hình, kết nối thiết bị nếu có dịch vụ đi kèm'],
              ['Lắp đặt bởi hãng', 'Áp dụng với sản phẩm cần kỹ thuật viên của hãng thực hiện'],
            ]}
          />
        </div>
      ),
    },
    {
      id: 'd-13',
      number: '13',
      title: 'Trách nhiệm của khách hàng',
      icon: <Users className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList items={[
            'Cung cấp thông tin giao hàng chính xác, đầy đủ và có thể liên hệ được.',
            'Kiểm tra tình trạng kiện hàng, thông tin sản phẩm và số lượng tại thời điểm nhận hàng.',
            'Thanh toán đúng số tiền thể hiện trên đơn hàng (nếu thanh toán COD).',
            'Thông báo kịp thời cho ElectroMart nếu phát hiện giao sai, giao thiếu, hư hỏng, sai giá trị thu tiền.',
            'Chịu trách nhiệm do cung cấp sai địa chỉ, SĐT, không nhận hàng đúng hẹn hoặc ủy quyền không phù hợp.',
          ]} />
        </div>
      ),
    },
    {
      id: 'd-14',
      number: '14',
      title: 'Trách nhiệm của ElectroMart Việt Nam',
      icon: <ShieldCheck className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList items={[
            'Xử lý đơn hàng đúng thông tin đã xác nhận với khách hàng.',
            'Đóng gói sản phẩm phù hợp nhằm hạn chế hư hỏng khi vận chuyển.',
            'Cung cấp thông tin, trạng thái giao hàng và hỗ trợ khách hàng khi có sự cố.',
            'Phối hợp với đơn vị vận chuyển xác minh và xử lý các trường hợp sai sót, hư hỏng, thất lạc.',
            'Áp dụng phương án khắc phục bảo đảm quyền lợi khách hàng nếu lỗi từ ElectroMart hoặc đối tác vận chuyển.',
          ]} />
        </div>
      ),
    },
    {
      id: 'd-15',
      number: '15',
      title: 'Trách nhiệm của đơn vị vận chuyển',
      icon: <Truck className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList items={[
            'Giao hàng đúng địa chỉ, đúng người nhận hoặc người được ủy quyền.',
            'Bảo quản hàng hóa trong quá trình vận chuyển theo đúng tiêu chuẩn.',
            'Cập nhật trạng thái đơn hàng trung thực, đầy đủ và kịp thời trên hệ thống.',
            'Phối hợp với ElectroMart Việt Nam xử lý khi có sự cố giao chậm, thất lạc, hư hỏng hoặc giao nhầm.',
          ]} />
        </div>
      ),
    },
    {
      id: 'd-16',
      number: '16',
      title: 'Lưu trữ dữ liệu giao nhận trên hệ thống',
      icon: <Database className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Trường dữ liệu', 'Nội dung']}
            rows={[
              ['Mã đơn hàng / Mã vận đơn', 'Mã định danh đơn hàng và mã giao hàng từ ĐVVC'],
              ['Thông tin người nhận', 'Họ tên, số điện thoại, địa chỉ'],
              ['Đơn vị vận chuyển', 'Tên đơn vị hoặc nhân viên giao hàng'],
              ['Phí giao hàng', 'Chi phí vận chuyển nếu có'],
              ['Trạng thái giao hàng', 'Chờ giao, đang giao, giao thành công, thất bại, hoàn hàng'],
              ['Thời gian bàn giao / thành công', 'Thời điểm chuyển cho ĐVVC và thời điểm khách xác nhận nhận hàng'],
              ['Lý do giao thất bại', 'Không liên hệ được, sai địa chỉ, khách từ chối, lý do khác'],
              ['Bằng chứng giao nhận', 'Chữ ký, hình ảnh, OTP, biên bản xác nhận...'],
            ]}
          />
          <p>Việc lưu trữ giúp ElectroMart kiểm soát quy trình vận chuyển, xác minh khiếu nại và nâng cao chất lượng dịch vụ.</p>
        </div>
      ),
    },
    {
      id: 'd-17',
      number: '17',
      title: 'Điều khoản áp dụng',
      icon: <FileText className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Chính sách này có thể được điều chỉnh, bổ sung tùy theo điều kiện vận hành, đối tác vận chuyển hoặc thay đổi quy định pháp luật.</p>
          <p>Mọi thay đổi quan trọng sẽ được công bố trên website. Việc tiếp tục sử dụng dịch vụ được hiểu là khách hàng đã đồng ý với nội dung sửa đổi.</p>
        </div>
      ),
    },
    {
      id: 'd-18',
      number: '18',
      title: 'Kết luận',
      icon: <ShieldCheck className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>Chính sách giao hàng, kiểm hàng và nhận hàng được xây dựng nhằm chuẩn hóa quá trình giao nhận sản phẩm từ lúc đơn hàng được xác nhận đến khi khách hàng nhận hàng thành công.</p>
          <div className="rounded-lg border border-sky-200 bg-sky-50 px-4 py-3">
            <p className="text-sm font-semibold text-sky-800">
              Việc quy định rõ phạm vi, thời gian, phí vận chuyển, quyền kiểm hàng và trách nhiệm các bên giúp hệ thống vận hành minh bạch, hạn chế tranh chấp và nâng cao trải nghiệm mua sắm trực tuyến.
            </p>
          </div>
        </div>
      ),
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Banner */}
      <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-sky-900/60">
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage:
              'radial-gradient(circle at 20% 60%, #0ea5e9 0%, transparent 50%), radial-gradient(circle at 80% 20%, #38bdf8 0%, transparent 40%)',
          }}
        />
        <div className="relative mx-auto max-w-5xl px-4 py-12 lg:px-6">
          {/* Breadcrumb */}
          <nav className="mb-5 flex items-center gap-1.5 text-xs text-slate-400">
            <Link to="/" className="transition hover:text-white">Trang chủ</Link>
            <span>/</span>
            <Link to="/about" className="transition hover:text-white">Giới thiệu công ty</Link>
            <span>/</span>
            <span className="text-slate-200">Giao nhận &amp; Kiểm hàng</span>
          </nav>

          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-sky-500 shadow-lg shadow-sky-500/30">
              <Truck className="h-6 w-6 text-white" />
            </div>
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-sky-400">Chính sách</p>
              <h1 className="text-2xl font-bold font-display leading-tight text-white lg:text-3xl">
                Chính sách giao nhận &amp; kiểm hàng
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-300">
                Quy định minh bạch về thời gian, phí vận chuyển, quyền đồng kiểm và trách nhiệm các bên nhằm đảm bảo đơn hàng được giao đến tay bạn an toàn, nhanh chóng nhất.
              </p>
            </div>
          </div>

          {/* Quick stats */}
          <div className="mt-8 grid grid-cols-3 gap-4 border-t border-white/10 pt-6">
            {[
              { label: 'Giao hàng nội thành', value: '1-2 ngày' },
              { label: 'Quyền đồng kiểm', value: 'Hỗ trợ' },
              { label: 'Điều khoản', value: '18' },
            ].map((s) => (
              <div key={s.label} className="text-center">
                <div className="text-2xl font-bold text-sky-400">{s.value}</div>
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
                    ? 'border-sky-200 bg-white shadow-md shadow-sky-500/5'
                    : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm'
                }`}
              >
                <button
                  id={`delivery-section-${section.number}`}
                  onClick={() => toggle(section.id)}
                  className="flex w-full items-center gap-4 px-5 py-4 text-left"
                  aria-expanded={isOpen}
                >
                  <div
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors ${
                      isOpen ? 'bg-sky-500 text-white' : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    {section.icon}
                  </div>
                  <div className="flex-1">
                    <div className="mb-0.5">
                      <span className={`text-xs font-bold ${isOpen ? 'text-sky-600' : 'text-slate-400'}`}>
                        Điều {section.number}
                      </span>
                    </div>
                    <div className={`text-sm font-semibold leading-tight ${isOpen ? 'text-sky-700' : 'text-slate-800'}`}>
                      {section.title}
                    </div>
                  </div>
                  <div className={`shrink-0 transition-colors ${isOpen ? 'text-sky-600' : 'text-slate-400'}`}>
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
