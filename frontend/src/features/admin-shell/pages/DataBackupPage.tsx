import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ChevronDown, ChevronUp, HardDrive, Smartphone, Laptop, ArrowRight,
  AlertTriangle, BadgeCheck, Users, Archive, ShieldAlert, FileText, UserCheck,
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
          <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-500" />
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
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-teal-600 text-xs font-bold text-white shadow-sm">
          {number}
        </div>
        <div className="mt-1 w-0.5 flex-1 bg-teal-100" />
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

export default function DataBackupPage() {
  const [expanded, setExpanded] = useState<string | null>('b-1');
  const toggle = (id: string) => setExpanded((p) => (p === id ? null : id));

  const sections: Section[] = [
    {
      id: 'b-1',
      number: '1',
      title: 'Quy định chung',
      icon: <HardDrive className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>
            ElectroMart Việt Nam nhận thức rõ dữ liệu cá nhân trên các thiết bị điện tử có vai trò quan trọng đối với khách hàng — bao gồm hình ảnh, video, danh bạ, tài liệu, tài khoản cá nhân, ứng dụng, dữ liệu học tập, công việc và các thông tin riêng tư khác.
          </p>
          <p>
            Chính sách này quy định rõ phạm vi hỗ trợ, trách nhiệm của khách hàng, trách nhiệm của nhân viên và giới hạn trách nhiệm của ElectroMart Việt Nam trong quá trình sao lưu, chuyển dữ liệu, cài đặt, sửa chữa, bảo hành hoặc hỗ trợ kỹ thuật đối với thiết bị của khách hàng.
          </p>
          <Note>
            <strong>Nguyên tắc cốt lõi:</strong> Khách hàng là chủ thể sở hữu và quản lý dữ liệu cá nhân trên thiết bị. Do đó, khách hàng có trách nhiệm <strong>chủ động sao lưu, kiểm tra và bảo vệ dữ liệu</strong> của mình trước khi bàn giao thiết bị cho ElectroMart Việt Nam.
          </Note>
        </div>
      ),
    },
    {
      id: 'b-2',
      number: '2',
      title: 'Các trường hợp được hướng dẫn sao lưu và chuyển dữ liệu',
      icon: <FileText className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Trường hợp', 'Nội dung hỗ trợ']}
            rows={[
              ['Mua điện thoại mới', 'Hướng dẫn sao lưu dữ liệu từ thiết bị cũ và chuyển sang thiết bị mới'],
              ['Mua laptop hoặc PC', 'Hướng dẫn sao lưu tài liệu, hình ảnh, dữ liệu cá nhân sang thiết bị lưu trữ riêng'],
              ['Mua thiết bị lưu trữ', 'Hướng dẫn sử dụng USB, thẻ nhớ, ổ cứng di động hoặc SSD để lưu trữ dữ liệu'],
              ['Gửi máy bảo hành / sửa chữa', 'Hướng dẫn khách hàng tự sao lưu dữ liệu trước khi bàn giao thiết bị'],
              ['Yêu cầu cài đặt phần mềm', 'Tư vấn rủi ro mất dữ liệu trong quá trình cài đặt, khôi phục hoặc thiết lập lại thiết bị'],
              ['Đổi trả hoặc nhập lại sản phẩm', 'Hướng dẫn đăng xuất tài khoản, xóa dữ liệu cá nhân và sao lưu dữ liệu cần thiết'],
            ]}
          />
          <div className="flex items-start gap-2 rounded-lg border border-teal-200 bg-teal-50 px-4 py-3">
            <BadgeCheck className="mt-0.5 h-4 w-4 shrink-0 text-teal-600" />
            <p className="text-sm text-teal-800">
              Việc hỗ trợ của ElectroMart Việt Nam chủ yếu mang tính chất <strong>hướng dẫn và tư vấn kỹ thuật</strong>. Khách hàng được khuyến nghị tự thực hiện sao lưu, chuyển dữ liệu bằng tài khoản, thiết bị lưu trữ hoặc máy tính cá nhân thuộc quyền sở hữu của mình.
            </p>
          </div>
        </div>
      ),
    },
    {
      id: 'b-3',
      number: '3',
      title: 'Quy định thực hiện sao lưu dữ liệu',
      icon: <Smartphone className="h-5 w-5" />,
      content: (
        <div className="space-y-5 text-sm text-slate-600 leading-relaxed">
          {/* 3.1 */}
          <div className="space-y-3">
            <h4 className="text-sm font-bold text-slate-800">3.1. iPhone, iPad và sản phẩm Apple</h4>
            <BulletList
              items={[
                'Sao lưu dữ liệu lên iCloud bằng tài khoản Apple ID của khách hàng.',
                'Sao lưu dữ liệu vào máy tính cá nhân thông qua Finder hoặc iTunes.',
                'Chuyển dữ liệu trực tiếp từ thiết bị Apple cũ sang thiết bị Apple mới bằng công cụ chuyển dữ liệu của hãng.',
              ]}
            />
            <Note>
              Khách hàng tự bảo mật Apple ID, mật khẩu, mã xác thực hai lớp. Nhân viên ElectroMart Việt Nam <strong>không được</strong> yêu cầu khách hàng cung cấp mật khẩu Apple ID, mã OTP hoặc thông tin xác thực riêng tư.
            </Note>
          </div>
          {/* 3.2 */}
          <div className="space-y-3">
            <h4 className="text-sm font-bold text-slate-800">3.2. Thiết bị Android</h4>
            <BulletList
              items={[
                'Sao lưu danh bạ, hình ảnh, ứng dụng và dữ liệu lên tài khoản Google.',
                'Sử dụng công cụ chuyển dữ liệu chính thức của hãng: Samsung Smart Switch, Xiaomi, OPPO, vivo hoặc công cụ tương đương.',
                'Sao lưu vào máy tính cá nhân, USB, thẻ nhớ hoặc ổ cứng thuộc quyền sở hữu của khách hàng.',
              ]}
            />
          </div>
          {/* 3.3 */}
          <div className="space-y-3">
            <h4 className="text-sm font-bold text-slate-800">3.3. Laptop, PC và thiết bị lưu trữ</h4>
            <p>
              Khách hàng tự thực hiện sao lưu dữ liệu sang thiết bị lưu trữ cá nhân. Nhân viên ElectroMart Việt Nam có thể hướng dẫn các thao tác cơ bản như sao chép thư mục, chuyển dữ liệu sang ổ cứng ngoài, kiểm tra dung lượng lưu trữ hoặc khuyến nghị phương án sao lưu phù hợp.
            </p>
            <Note>
              ElectroMart Việt Nam không khuyến khích lưu trữ dữ liệu cá nhân của khách hàng trên thiết bị thuộc quyền sở hữu của cửa hàng, trừ trường hợp thật sự cần thiết và được khách hàng đồng ý bằng văn bản hoặc xác nhận trên hệ thống.
            </Note>
          </div>
        </div>
      ),
    },
    {
      id: 'b-4',
      number: '4',
      title: 'Quy định về chuyển dữ liệu giữa các thiết bị',
      icon: <Laptop className="h-5 w-5" />,
      content: (
        <div className="space-y-5 text-sm text-slate-600 leading-relaxed">
          <div className="space-y-3">
            <h4 className="text-sm font-bold text-slate-800">4.1. Chuyển dữ liệu cùng hệ điều hành (iPhone → iPhone / Android → Android)</h4>
            <p>
              Khách hàng được hướng dẫn sử dụng công cụ chuyển dữ liệu trực tiếp do nhà sản xuất cung cấp. Dữ liệu có thể bao gồm danh bạ, hình ảnh, video, tin nhắn, ứng dụng và một số dữ liệu hệ thống tùy theo khả năng hỗ trợ của từng hãng.
            </p>
            <Note>
              ElectroMart Việt Nam không cam kết toàn bộ dữ liệu sẽ được chuyển đầy đủ trong mọi trường hợp, do còn phụ thuộc vào hệ điều hành, dung lượng bộ nhớ, phiên bản phần mềm, tài khoản đăng nhập và chính sách của nhà sản xuất.
            </Note>
          </div>
          <div className="space-y-3">
            <h4 className="text-sm font-bold text-slate-800">4.2. Chuyển dữ liệu khác hệ điều hành (Android ↔ iPhone)</h4>
            <p>
              Khách hàng tự thực hiện theo công cụ chính thức của hãng hoặc hướng dẫn kỹ thuật phù hợp. Trường hợp không thể tự thực hiện, nhân viên ElectroMart Việt Nam chỉ hỗ trợ trong phạm vi cơ bản:
            </p>
            <Table
              headers={['Nhóm dữ liệu', 'Hướng hỗ trợ']}
              rows={[
                ['Danh bạ', 'Ưu tiên đồng bộ qua tài khoản Google hoặc iCloud của khách hàng'],
                ['Hình ảnh / video', 'Sao lưu qua máy tính cá nhân, thiết bị lưu trữ cá nhân hoặc công cụ chuyển dữ liệu chính thức'],
                ['Tài liệu cá nhân', 'Sao chép sang thiết bị lưu trữ thuộc quyền sở hữu của khách hàng'],
                ['Ứng dụng', 'Hướng dẫn cài đặt lại từ kho ứng dụng chính thức'],
                ['Tin nhắn, dữ liệu ứng dụng', 'Chỉ hỗ trợ nếu công cụ chính thức của hãng cho phép'],
              ]}
            />
            <Note>
              ElectroMart Việt Nam không cam kết chuyển được dữ liệu ứng dụng, lịch sử trò chuyện, dữ liệu đăng nhập, dữ liệu ngân hàng, ví điện tử hoặc dữ liệu được mã hóa bởi bên thứ ba.
            </Note>
          </div>
        </div>
      ),
    },
    {
      id: 'b-5',
      number: '5',
      title: 'Trường hợp nhân viên hỗ trợ trực tiếp',
      icon: <UserCheck className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <p>
            Khi khách hàng không thể tự sao lưu/chuyển dữ liệu và đề nghị nhân viên hỗ trợ trực tiếp, việc hỗ trợ chỉ được thực hiện khi đáp ứng <strong>đầy đủ</strong> các điều kiện sau:
          </p>
          <BulletList
            items={[
              'Khách hàng đã được thông báo về rủi ro mất dữ liệu, lỗi dữ liệu, thiếu dữ liệu hoặc không thể khôi phục dữ liệu.',
              'Khách hàng đồng ý để nhân viên hỗ trợ thao tác trên thiết bị.',
              'Khách hàng ký xác nhận vào Cam kết miễn trừ trách nhiệm về dữ liệu hoặc xác nhận đồng ý trên hệ thống.',
              'Khách hàng trực tiếp có mặt trong quá trình nhân viên thực hiện thao tác, trừ trường hợp có thỏa thuận khác được ghi nhận.',
              'Dữ liệu chỉ được chuyển sang thiết bị, tài khoản hoặc phương tiện lưu trữ thuộc quyền sở hữu của khách hàng.',
            ]}
          />
          <Note>
            Nhân viên ElectroMart Việt Nam <strong>không được</strong> tự ý sao chép, lưu giữ, chia sẻ, phát tán hoặc truy cập vào các dữ liệu không liên quan đến yêu cầu hỗ trợ của khách hàng.
          </Note>
        </div>
      ),
    },
    {
      id: 'b-6',
      number: '6',
      title: 'Quy định khi dùng thiết bị lưu trữ của ElectroMart',
      icon: <HardDrive className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <p>
            Trong trường hợp đặc biệt, nếu việc chuyển dữ liệu bắt buộc phải thông qua thiết bị lưu trữ tạm thời của ElectroMart Việt Nam, nhân viên chỉ được thực hiện khi có sự đồng ý rõ ràng của khách hàng.
          </p>
          <div className="space-y-0">
            {[
              { title: 'Thông báo lý do', desc: 'Nhân viên thông báo cho khách hàng lý do cần sử dụng thiết bị lưu trữ tạm thời của ElectroMart Việt Nam.' },
              { title: 'Xác nhận đồng ý', desc: 'Khách hàng xác nhận đồng ý và ký cam kết miễn trừ trách nhiệm về dữ liệu.' },
              { title: 'Thực hiện chuyển dữ liệu', desc: 'Nhân viên thực hiện chuyển dữ liệu trong phạm vi khách hàng yêu cầu.' },
              { title: 'Khách hàng kiểm tra', desc: 'Khách hàng kiểm tra lại dữ liệu trên thiết bị nhận.' },
              { title: 'Xóa dữ liệu tạm thời', desc: 'Sau khi khách hàng xác nhận, nhân viên phải xóa ngay dữ liệu tạm thời trên thiết bị của ElectroMart Việt Nam trước sự chứng kiến của khách hàng.' },
              { title: 'Ghi nhận hệ thống', desc: 'Việc xóa dữ liệu được ghi nhận trên hệ thống hoặc biên bản hỗ trợ nếu cần.' },
            ].map((step, i) => (
              <ProcessStep key={i} number={i + 1} title={step.title}>
                {step.desc}
              </ProcessStep>
            ))}
          </div>
          <Note>
            ElectroMart Việt Nam không lưu trữ lâu dài dữ liệu cá nhân của khách hàng trên thiết bị nội bộ, trừ trường hợp pháp luật có yêu cầu hoặc khách hàng có văn bản đồng ý riêng.
          </Note>
        </div>
      ),
    },
    {
      id: 'b-7',
      number: '7',
      title: 'Giới hạn trách nhiệm của ElectroMart Việt Nam',
      icon: <ShieldAlert className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>ElectroMart Việt Nam và nhân viên hỗ trợ <strong>không chịu trách nhiệm</strong> đối với các trường hợp sau:</p>
          <BulletList
            items={[
              'Dữ liệu bị mất, thiếu, lỗi, hỏng, không thể mở hoặc không thể khôi phục trong quá trình sao lưu, chuyển dữ liệu, cài đặt, sửa chữa, bảo hành hoặc khôi phục thiết bị.',
              'Dữ liệu không thể chuyển do giới hạn hệ điều hành, chính sách bảo mật nhà sản xuất, lỗi tài khoản, lỗi mật khẩu, mã hóa dữ liệu hoặc ứng dụng bên thứ ba.',
              'Khách hàng quên mật khẩu, mất quyền truy cập tài khoản, mất mã xác thực, mất Apple ID, Google Account hoặc tài khoản ứng dụng liên quan.',
              'Dữ liệu ứng dụng không thể khôi phục do ứng dụng không hỗ trợ đồng bộ hoặc không cho phép sao lưu độc lập.',
              'Thiết bị bị lỗi phần cứng, lỗi bộ nhớ, lỗi ổ cứng, lỗi mainboard hoặc lỗi hệ điều hành trước thời điểm tiếp nhận hỗ trợ.',
              'Khách hàng không kiểm tra lại dữ liệu sau khi hoàn tất việc chuyển dữ liệu.',
              'Khách hàng tự ý thực hiện thao tác sai trong quá trình sao lưu hoặc chuyển dữ liệu dù đã được hướng dẫn.',
            ]}
          />
        </div>
      ),
    },
    {
      id: 'b-8',
      number: '8',
      title: 'Cam kết miễn trừ trách nhiệm về dữ liệu',
      icon: <FileText className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>
            Bằng việc yêu cầu nhân viên ElectroMart Việt Nam hỗ trợ và bàn giao thiết bị, khách hàng xác nhận rằng:
          </p>
          <BulletList
            items={[
              'Đã được thông báo về tầm quan trọng của dữ liệu cá nhân trên thiết bị.',
              'Đã được tư vấn về các rủi ro có thể phát sinh: mất dữ liệu, thiếu dữ liệu, lỗi dữ liệu, không thể khôi phục hoặc không thể chuyển toàn bộ dữ liệu.',
              'Đồng ý để nhân viên ElectroMart Việt Nam thực hiện thao tác hỗ trợ trong phạm vi yêu cầu.',
              'Tự chịu mọi rủi ro phát sinh đối với dữ liệu trong quá trình sao lưu, chuyển dữ liệu, cài đặt, sửa chữa, bảo hành hoặc hỗ trợ kỹ thuật.',
            ]}
          />
          <Note>
            Khách hàng đồng ý miễn trừ trách nhiệm pháp lý cho ElectroMart Việt Nam, nhân viên và đối tác kỹ thuật đối với mọi rủi ro liên quan đến dữ liệu, <strong>trừ trường hợp</strong> có căn cứ chứng minh nhân viên cố ý sao chép, tiết lộ, sử dụng trái phép hoặc phát tán dữ liệu cá nhân của khách hàng.
          </Note>
        </div>
      ),
    },
    {
      id: 'b-9',
      number: '9',
      title: 'Trách nhiệm của khách hàng',
      icon: <Users className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <BulletList
            items={[
              'Tự sao lưu dữ liệu quan trọng trước khi gửi thiết bị bảo hành, sửa chữa, đổi trả hoặc yêu cầu hỗ trợ kỹ thuật.',
              'Kiểm tra tình trạng dữ liệu trước và sau khi quá trình hỗ trợ hoàn tất.',
              'Tự quản lý tài khoản, mật khẩu, mã OTP, khóa bảo mật, dữ liệu ngân hàng, ví điện tử và các thông tin cá nhân quan trọng.',
              'Không lưu trữ các dữ liệu nhạy cảm trên thiết bị khi bàn giao cho nhân viên nếu dữ liệu đó không liên quan đến yêu cầu kỹ thuật.',
              'Đăng xuất tài khoản cá nhân, tắt khóa bảo mật hoặc cung cấp quyền truy cập cần thiết trong phạm vi hỗ trợ — nhưng không cung cấp mật khẩu, mã OTP hoặc thông tin xác thực riêng tư cho nhân viên.',
            ]}
          />
        </div>
      ),
    },
    {
      id: 'b-10',
      number: '10',
      title: 'Trách nhiệm của nhân viên ElectroMart Việt Nam',
      icon: <UserCheck className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <div className="grid gap-2 sm:grid-cols-2">
            {[
              'Hướng dẫn khách hàng sao lưu và chuyển dữ liệu theo đúng quy trình.',
              'Không yêu cầu khách hàng cung cấp mật khẩu tài khoản, mã OTP, thông tin thẻ ngân hàng, ví điện tử hoặc dữ liệu riêng tư không cần thiết.',
              'Chỉ thao tác trên các dữ liệu nằm trong phạm vi khách hàng yêu cầu hỗ trợ.',
              'Không sao chép, lưu trữ, chia sẻ, chụp ảnh, quay video hoặc phát tán dữ liệu của khách hàng dưới bất kỳ hình thức nào.',
              'Thông báo rõ cho khách hàng về rủi ro trước khi thực hiện thao tác có khả năng ảnh hưởng đến dữ liệu.',
              'Yêu cầu khách hàng ký xác nhận miễn trừ trách nhiệm hoặc xác nhận trên hệ thống trước khi hỗ trợ trực tiếp đối với dữ liệu.',
            ].map((item) => (
              <div key={item} className="flex items-start gap-2 rounded-lg border border-teal-100 bg-teal-50 px-3 py-2">
                <BadgeCheck className="mt-0.5 h-4 w-4 shrink-0 text-teal-600" />
                <span className="text-sm text-teal-800">{item}</span>
              </div>
            ))}
          </div>
        </div>
      ),
    },
    {
      id: 'b-11',
      number: '11',
      title: 'Lưu trữ hồ sơ hỗ trợ dữ liệu trên hệ thống',
      icon: <Archive className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-sm text-slate-600 leading-relaxed">
          <Table
            headers={['Trường dữ liệu', 'Nội dung']}
            rows={[
              ['Mã yêu cầu hỗ trợ', 'Mã định danh của yêu cầu hỗ trợ dữ liệu'],
              ['Mã khách hàng', 'Thông tin tài khoản hoặc khách hàng yêu cầu hỗ trợ'],
              ['Mã đơn hàng / sản phẩm', 'Sản phẩm liên quan đến yêu cầu hỗ trợ'],
              ['Loại thiết bị', 'iPhone, Android, laptop, PC, USB, ổ cứng hoặc thiết bị khác'],
              ['Loại hỗ trợ', 'Sao lưu dữ liệu, chuyển dữ liệu, cài đặt, bảo hành, sửa chữa'],
              ['Phạm vi dữ liệu', 'Danh bạ, hình ảnh, tài liệu hoặc dữ liệu khác'],
              ['Người thực hiện', 'Nhân viên tiếp nhận hoặc nhân viên kỹ thuật'],
              ['Hình thức xác nhận', 'Khách hàng ký giấy, xác nhận điện tử hoặc xác nhận trên hệ thống'],
              ['Trạng thái xử lý', 'Đã tiếp nhận / Đang hỗ trợ / Hoàn tất / Từ chối hỗ trợ'],
              ['Ghi chú rủi ro', 'Các rủi ro đã thông báo cho khách hàng'],
              ['Xác nhận hoàn tất', 'Khách hàng xác nhận đã kiểm tra dữ liệu sau hỗ trợ'],
            ]}
          />
          <p>
            Việc ghi nhận hồ sơ giúp ElectroMart Việt Nam hạn chế tranh chấp, nâng cao trách nhiệm của nhân viên và đảm bảo tính minh bạch trong quá trình hỗ trợ khách hàng.
          </p>
        </div>
      ),
    },
    {
      id: 'b-12',
      number: '12',
      title: 'Kết luận',
      icon: <BadgeCheck className="h-5 w-5" />,
      content: (
        <div className="space-y-3 text-sm text-slate-600 leading-relaxed">
          <p>
            Quy định về hỗ trợ sao lưu và chuyển dữ liệu của ElectroMart Việt Nam được xây dựng nhằm bảo vệ quyền lợi của khách hàng, đồng thời xác định rõ giới hạn trách nhiệm của hệ thống trong quá trình hỗ trợ kỹ thuật.
          </p>
          <div className="rounded-lg border border-teal-200 bg-teal-50 px-4 py-3">
            <p className="text-sm font-semibold text-teal-800">
              Thông qua việc khuyến nghị khách hàng tự sao lưu dữ liệu, yêu cầu xác nhận miễn trừ trách nhiệm khi nhân viên hỗ trợ trực tiếp và quy định rõ nguyên tắc xử lý dữ liệu tạm thời, ElectroMart Việt Nam hướng đến xây dựng quy trình hỗ trợ minh bạch, an toàn và phù hợp với thực tiễn vận hành của hệ thống thương mại điện tử trong lĩnh vực thiết bị công nghệ.
            </p>
          </div>
        </div>
      ),
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Banner */}
      <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-teal-900/60">
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage:
              'radial-gradient(circle at 20% 60%, #0d9488 0%, transparent 50%), radial-gradient(circle at 80% 20%, #06b6d4 0%, transparent 40%)',
          }}
        />
        <div className="relative mx-auto max-w-5xl px-4 py-12 lg:px-6">
          {/* Breadcrumb */}
          <nav className="mb-5 flex items-center gap-1.5 text-xs text-slate-400">
            <Link to="/" className="transition hover:text-white">Trang chủ</Link>
            <span>/</span>
            <Link to="/about" className="transition hover:text-white">Giới thiệu công ty</Link>
            <span>/</span>
            <span className="text-slate-200">Hỗ trợ sao lưu &amp; chuyển dữ liệu</span>
          </nav>

          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-teal-600 shadow-lg shadow-teal-500/30">
              <HardDrive className="h-6 w-6 text-white" />
            </div>
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-teal-400">Chính sách</p>
              <h1 className="text-2xl font-bold font-display leading-tight text-white lg:text-3xl">
                Quy định hỗ trợ sao lưu &amp; chuyển dữ liệu
              </h1>
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-slate-300">
                Quy định rõ phạm vi hỗ trợ, trách nhiệm các bên và giới hạn trách nhiệm của ElectroMart Việt Nam trong quá trình sao lưu, chuyển dữ liệu và hỗ trợ kỹ thuật đối với thiết bị của khách hàng.
              </p>
            </div>
          </div>

          {/* Quick stats */}
          <div className="mt-8 grid grid-cols-3 gap-4 border-t border-white/10 pt-6">
            {[
              { label: 'Trường hợp được hỗ trợ', value: '6' },
              { label: 'Nền tảng thiết bị', value: '3' },
              { label: 'Điều khoản', value: '12' },
            ].map((s) => (
              <div key={s.label} className="text-center">
                <div className="text-2xl font-bold text-teal-400">{s.value}</div>
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
                    ? 'border-teal-200 bg-white shadow-md shadow-teal-500/5'
                    : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm'
                }`}
              >
                <button
                  id={`databackup-section-${section.number}`}
                  onClick={() => toggle(section.id)}
                  className="flex w-full items-center gap-4 px-5 py-4 text-left"
                  aria-expanded={isOpen}
                >
                  <div
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors ${
                      isOpen ? 'bg-teal-600 text-white' : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    {section.icon}
                  </div>
                  <div className="flex-1">
                    <div className="mb-0.5">
                      <span className={`text-xs font-bold ${isOpen ? 'text-teal-600' : 'text-slate-400'}`}>
                        Điều {section.number}
                      </span>
                    </div>
                    <div className={`text-sm font-semibold leading-tight ${isOpen ? 'text-teal-700' : 'text-slate-800'}`}>
                      {section.title}
                    </div>
                  </div>
                  <div className={`shrink-0 transition-colors ${isOpen ? 'text-teal-600' : 'text-slate-400'}`}>
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
            to="/privacy"
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
          >
            Chính sách bảo mật
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
