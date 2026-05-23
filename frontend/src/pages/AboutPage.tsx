import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { ChevronDown, ChevronUp, Building2, Target, Eye, Rocket, Heart, Star, ArrowRight, Shield } from 'lucide-react';

interface Section {
  id: string;
  number: string;
  title: string;
  icon: React.ReactNode;
  content: React.ReactNode;
}

export default function AboutPage() {
  const [expandedSection, setExpandedSection] = useState<string | null>('section-1');

  const toggleSection = (id: string) => {
    setExpandedSection((prev) => (prev === id ? null : id));
  };

  const sections: Section[] = [
    {
      id: 'section-1',
      number: '1',
      title: 'Giới thiệu chung',
      icon: <Building2 className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-slate-600 leading-relaxed text-sm">
          <p>
            ElectroMart Việt Nam là hệ thống thương mại điện tử được xây dựng với định hướng trở thành một nền tảng mua sắm
            trực tuyến chuyên cung cấp các sản phẩm điện tử, thiết bị công nghệ và phụ kiện chính hãng tại thị trường Việt
            Nam. Trong bối cảnh chuyển đổi số diễn ra mạnh mẽ, nhu cầu mua sắm trực tuyến của người tiêu dùng ngày càng
            gia tăng, ElectroMart Việt Nam được phát triển nhằm đáp ứng yêu cầu về sự tiện lợi, minh bạch, nhanh chóng và
            an toàn trong quá trình lựa chọn, đặt mua và thanh toán sản phẩm.
          </p>
          <p>
            Hệ thống ElectroMart Việt Nam tập trung vào các nhóm sản phẩm công nghệ phổ biến như điện thoại di động, máy
            tính xách tay, máy tính bảng, thiết bị âm thanh, phụ kiện điện tử và các sản phẩm liên quan đến đời sống số.
            Thông qua nền tảng trực tuyến, người dùng có thể dễ dàng tra cứu thông tin sản phẩm, so sánh cấu hình, tham
            khảo giá bán, quản lý giỏ hàng, đặt hàng và theo dõi trạng thái đơn hàng một cách thuận tiện.
          </p>
          <p>
            Không chỉ hướng đến chức năng mua bán thông thường, ElectroMart Việt Nam còn được xây dựng với mục tiêu nâng
            cao trải nghiệm người dùng thông qua giao diện thân thiện, quy trình thao tác rõ ràng, hệ thống quản lý dữ liệu
            chặt chẽ và các chức năng hỗ trợ người dùng trong quá trình mua sắm. Đây là cơ sở quan trọng để hệ thống có thể
            đáp ứng tốt hơn nhu cầu thực tế của khách hàng cũng như yêu cầu quản trị của doanh nghiệp trong môi trường kinh
            doanh hiện đại.
          </p>
        </div>
      ),
    },
    {
      id: 'section-2',
      number: '2',
      title: 'Định hướng phát triển',
      icon: <Rocket className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-slate-600 leading-relaxed text-sm">
          <p>
            ElectroMart Việt Nam được phát triển theo định hướng kết hợp giữa hoạt động thương mại điện tử và quản lý bán
            lẻ sản phẩm công nghệ. Hệ thống không chỉ phục vụ khách hàng trong việc mua sắm trực tuyến mà còn hỗ trợ doanh
            nghiệp trong công tác quản lý sản phẩm, đơn hàng, tài khoản người dùng, chương trình khuyến mãi và các hoạt
            động chăm sóc khách hàng.
          </p>
          <p>
            Trong phạm vi đồ án, ElectroMart Việt Nam được xem là một mô hình hệ thống thương mại điện tử có khả năng mở
            rộng. Các chức năng được thiết kế nhằm mô phỏng quy trình vận hành của một website bán hàng công nghệ trong
            thực tế, từ khâu hiển thị sản phẩm, tiếp nhận đơn hàng, xử lý thanh toán, quản lý tồn kho cho đến hỗ trợ
            người dùng sau mua hàng.
          </p>
          <p>
            Việc xây dựng hệ thống ElectroMart Việt Nam góp phần thể hiện khả năng ứng dụng công nghệ thông tin vào lĩnh
            vực kinh doanh trực tuyến, đồng thời tạo nền tảng để nghiên cứu, phát triển và hoàn thiện các chức năng nâng
            cao trong tương lai.
          </p>
        </div>
      ),
    },
    {
      id: 'section-3',
      number: '3',
      title: 'Tôn chỉ hoạt động',
      icon: <Shield className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-slate-600 leading-relaxed text-sm">
          <p>
            ElectroMart Việt Nam lấy người dùng làm trung tâm trong quá trình thiết kế và vận hành hệ thống. Mọi chức
            năng được xây dựng đều hướng đến mục tiêu hỗ trợ khách hàng tiếp cận thông tin sản phẩm một cách đầy đủ,
            chính xác và thuận tiện.
          </p>
          <p>
            Đối với khách hàng, ElectroMart Việt Nam chú trọng tính minh bạch trong thông tin sản phẩm, sự thuận tiện
            trong thao tác mua hàng và sự an toàn trong quá trình thanh toán. Hệ thống hướng đến việc tạo ra một môi
            trường mua sắm trực tuyến đáng tin cậy, giúp người dùng tiết kiệm thời gian nhưng vẫn đảm bảo khả năng lựa
            chọn sản phẩm phù hợp với nhu cầu cá nhân.
          </p>
          <p>
            Đối với công tác quản trị, hệ thống đề cao tính chính xác, nhất quán và khoa học trong việc quản lý dữ liệu.
            Các chức năng quản lý sản phẩm, đơn hàng, người dùng và khuyến mãi được xây dựng nhằm hỗ trợ người quản trị
            theo dõi, kiểm soát và xử lý hoạt động kinh doanh một cách hiệu quả.
          </p>
          <p>
            Đối với định hướng phát triển lâu dài, ElectroMart Việt Nam đặt trọng tâm vào sự ổn định, khả năng mở rộng
            và tính ứng dụng thực tiễn. Hệ thống có thể tiếp tục được cải tiến để phù hợp hơn với nhu cầu của thị trường
            cũng như sự thay đổi không ngừng của lĩnh vực công nghệ.
          </p>
        </div>
      ),
    },
    {
      id: 'section-4',
      number: '4',
      title: 'Tầm nhìn',
      icon: <Eye className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-slate-600 leading-relaxed text-sm">
          <div className="mb-4 rounded-xl overflow-hidden border border-slate-100 shadow-sm max-w-md mx-auto bg-slate-50">
            <img src="/images/policies/about.png" alt="Tầm nhìn" className="w-full h-auto mix-blend-multiply" />
          </div>
      content: (
        <div className="space-y-4 text-slate-600 leading-relaxed text-sm">
          <div className="mb-4 rounded-xl overflow-hidden border border-slate-100 shadow-sm max-w-md mx-auto bg-slate-50">
            <img src="/images/policies/about.png" alt="Tầm nhìn" className="w-full h-auto mix-blend-multiply" />
          </div>
          <p>
            ElectroMart Việt Nam hướng đến mục tiêu trở thành một nền tảng thương mại điện tử chuyên biệt trong lĩnh
            vực sản phẩm công nghệ, có khả năng cung cấp trải nghiệm mua sắm trực tuyến thuận tiện, hiện đại và đáng
            tin cậy cho người tiêu dùng Việt Nam.
          </p>
          <div className="mb-4 mt-4 rounded-xl overflow-hidden border border-slate-100 shadow-sm max-w-md mx-auto bg-slate-50">
            <img src="/images/policies/tech_gadgets.png" alt="Sản phẩm công nghệ hiện đại" className="w-full h-auto mix-blend-multiply" />
          </div>
          <p>
            Trong tương lai, hệ thống có thể được mở rộng thêm nhiều chức năng như tích hợp trí tuệ nhân tạo trong tư
            vấn sản phẩm, cá nhân hóa gợi ý mua hàng, quản lý điểm thưởng khách hàng, phân tích hành vi tiêu dùng, tối
            ưu hóa quy trình vận chuyển và nâng cao khả năng bảo mật trong thanh toán trực tuyến.
          </p>
          <p>
            Tầm nhìn của ElectroMart Việt Nam không chỉ dừng lại ở việc xây dựng một website bán hàng, mà còn hướng đến
            việc hình thành một hệ sinh thái mua sắm công nghệ trực tuyến, nơi người dùng có thể tiếp cận sản phẩm chất
            lượng, dịch vụ hỗ trợ hiệu quả và quy trình giao dịch an toàn.
          </p>
        </div>
      ),
    },
    {
      id: 'section-5',
      number: '5',
      title: 'Sứ mệnh',
      icon: <Target className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-slate-600 leading-relaxed text-sm">
          <p>
            Sứ mệnh của ElectroMart Việt Nam là xây dựng một hệ thống thương mại điện tử có tính thực tiễn cao, hỗ trợ
            người dùng trong việc tiếp cận các sản phẩm công nghệ một cách nhanh chóng, chính xác và thuận tiện.
          </p>
          <p>
            Hệ thống hướng đến việc rút ngắn khoảng cách giữa người tiêu dùng và sản phẩm công nghệ, đồng thời góp phần
            thúc đẩy xu hướng mua sắm trực tuyến trong thời đại số. Thông qua việc ứng dụng các giải pháp công nghệ vào
            hoạt động kinh doanh, ElectroMart Việt Nam mong muốn nâng cao hiệu quả quản lý, cải thiện chất lượng dịch vụ
            và đem lại giá trị thiết thực cho cả khách hàng lẫn doanh nghiệp.
          </p>
        </div>
      ),
    },
    {
      id: 'section-6',
      number: '6',
      title: 'Chính sách và giá trị cốt lõi',
      icon: <Star className="h-5 w-5" />,
      content: (
        <div className="space-y-6 text-slate-600 text-sm">
          <p className="leading-relaxed">ElectroMart Việt Nam được xây dựng dựa trên các giá trị cốt lõi sau:</p>
          {[
            {
              num: '6.1',
              title: 'Sản phẩm rõ ràng, thông tin minh bạch',
              desc: 'Hệ thống cung cấp thông tin sản phẩm một cách đầy đủ, bao gồm tên sản phẩm, hình ảnh, cấu hình, thương hiệu, giá bán, tình trạng hàng hóa và các thông tin liên quan. Điều này giúp người dùng có cơ sở để so sánh, đánh giá và đưa ra quyết định mua hàng phù hợp.',
            },
            {
              num: '6.2',
              title: 'Giá cả hợp lý, ưu đãi linh hoạt',
              desc: 'ElectroMart Việt Nam hướng đến việc xây dựng cơ chế giá bán hợp lý, kết hợp với các chương trình khuyến mãi, mã giảm giá và ưu đãi dành cho khách hàng. Các chính sách này góp phần nâng cao trải nghiệm mua sắm và tăng khả năng tiếp cận sản phẩm của người tiêu dùng.',
            },
            {
              num: '6.3',
              title: 'Thanh toán thuận tiện và an toàn',
              desc: 'Hệ thống hỗ trợ các phương thức thanh toán trực tuyến nhằm đáp ứng nhu cầu đa dạng của khách hàng. Quy trình thanh toán được thiết kế theo hướng đơn giản, rõ ràng và đảm bảo an toàn trong quá trình giao dịch.',
            },
            {
              num: '6.4',
              title: 'Quản lý đơn hàng hiệu quả',
              desc: 'Người dùng có thể theo dõi trạng thái đơn hàng sau khi đặt mua, trong khi người quản trị có thể kiểm soát quá trình xử lý đơn hàng từ lúc tiếp nhận đến khi hoàn tất. Chức năng này góp phần nâng cao tính minh bạch và hiệu quả trong hoạt động bán hàng.',
            },
            {
              num: '6.5',
              title: 'Hỗ trợ khách hàng và cải thiện trải nghiệm',
              desc: 'ElectroMart Việt Nam chú trọng việc hỗ trợ người dùng trong quá trình tìm kiếm, lựa chọn và mua sản phẩm. Hệ thống có thể được phát triển thêm các chức năng như tư vấn tự động, đánh giá sản phẩm, bình luận, chăm sóc khách hàng và hỗ trợ sau bán hàng nhằm nâng cao chất lượng dịch vụ.',
            },
          ].map((item) => (
            <div key={item.num} className="rounded-lg border border-slate-100 bg-slate-50 p-4">
              <div className="mb-1.5 flex items-center gap-2">
                <span className="rounded bg-primary/10 px-2 py-0.5 text-xs font-bold text-primary">{item.num}</span>
                <h4 className="text-sm font-bold text-slate-800">{item.title}</h4>
              </div>
              <p className="leading-relaxed text-slate-600">{item.desc}</p>
            </div>
          ))}
        </div>
      ),
    },
    {
      id: 'section-7',
      number: '7',
      title: 'Kết luận',
      icon: <Heart className="h-5 w-5" />,
      content: (
        <div className="space-y-4 text-slate-600 leading-relaxed text-sm">
          <p>
            ElectroMart Việt Nam là một hệ thống thương mại điện tử được xây dựng nhằm mô phỏng và đáp ứng các nhu cầu
            cơ bản của hoạt động kinh doanh sản phẩm công nghệ trong môi trường trực tuyến. Với định hướng lấy người dùng
            làm trung tâm, hệ thống tập trung vào việc cung cấp thông tin minh bạch, quy trình mua hàng thuận tiện, khả
            năng quản lý hiệu quả và tiềm năng mở rộng trong tương lai.
          </p>
          <p>
            Việc xây dựng ElectroMart Việt Nam không chỉ có ý nghĩa trong phạm vi một đồ án luận văn mà còn thể hiện khả
            năng vận dụng kiến thức công nghệ thông tin vào giải quyết bài toán thực tiễn. Đây là nền tảng quan trọng để
            tiếp tục nghiên cứu, hoàn thiện và phát triển hệ thống theo hướng chuyên nghiệp, hiện đại và phù hợp hơn với
            nhu cầu của thị trường thương mại điện tử tại Việt Nam.
          </p>
        </div>
      ),
    },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Hero Banner */}
      <div className="relative overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-primary/80">
        <div
          className="absolute inset-0 opacity-10"
          style={{
            backgroundImage:
              'radial-gradient(circle at 20% 50%, #D70018 0%, transparent 50%), radial-gradient(circle at 80% 20%, #ffffff 0%, transparent 40%)',
          }}
        />
        <div className="relative mx-auto max-w-5xl px-4 py-14 lg:px-6">
          {/* Breadcrumb */}
          <nav className="mb-6 flex items-center gap-1.5 text-xs text-slate-400">
            <Link to="/" className="transition hover:text-white">
              Trang chủ
            </Link>
            <span>/</span>
            <span className="text-slate-200">Giới thiệu công ty</span>
          </nav>

          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-primary shadow-lg shadow-primary/30">
              <Building2 className="h-6 w-6 text-white" />
            </div>
            <div>
              <p className="mb-1 text-xs font-semibold uppercase tracking-widest text-primary">Về chúng tôi</p>
              <h1 className="text-2xl font-bold leading-tight text-white font-display lg:text-3xl">
                GIỚI THIỆU VỀ ELECTROMART VIỆT NAM
              </h1>
              <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-300">
                Nền tảng thương mại điện tử chuyên cung cấp các sản phẩm điện tử, thiết bị công nghệ và phụ kiện chính hãng —
                được xây dựng với định hướng minh bạch, thuận tiện và đáng tin cậy.
              </p>
            </div>
          </div>

          {/* Stats row */}
          <div className="mt-8 grid grid-cols-3 gap-4 border-t border-white/10 pt-6">
            {[
              { label: 'Nhóm sản phẩm', value: '6+' },
              { label: 'Phương thức thanh toán', value: '5' },
              { label: 'Hỗ trợ người dùng', value: '24/7' },
            ].map((stat) => (
              <div key={stat.label} className="text-center">
                <div className="text-2xl font-bold text-primary">{stat.value}</div>
                <div className="mt-0.5 text-xs text-slate-500">{stat.label}</div>
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
                    ? 'border-primary/30 bg-white shadow-md shadow-primary/5'
                    : 'border-slate-200 bg-white hover:border-slate-300 hover:shadow-sm'
                }`}
              >
                <button
                  id={`about-section-${section.number}`}
                  onClick={() => toggleSection(section.id)}
                  className="flex w-full items-center gap-4 px-5 py-4 text-left"
                  aria-expanded={isOpen}
                >
                  <div
                    className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg transition-colors ${
                      isOpen ? 'bg-primary text-white' : 'bg-slate-100 text-slate-500'
                    }`}
                  >
                    {section.icon}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span
                        className={`text-xs font-bold ${isOpen ? 'text-primary' : 'text-slate-400'}`}
                      >
                        Mục {section.number}
                      </span>
                    </div>
                    <div className={`text-sm font-semibold leading-tight ${isOpen ? 'text-primary' : 'text-slate-800'}`}>
                      {section.title}
                    </div>
                  </div>
                  <div className={`shrink-0 transition-colors ${isOpen ? 'text-primary' : 'text-slate-400'}`}>
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

        {/* CTA */}
        <div className="mt-10 overflow-hidden rounded-2xl bg-gradient-to-r from-primary to-red-700 p-6 text-white shadow-lg shadow-primary/20">
          <div className="flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
            <div>
              <h2 className="text-xl font-bold font-display">Bắt đầu mua sắm ngay hôm nay</h2>
              <p className="mt-1 text-sm text-red-100">
                Khám phá hàng nghìn sản phẩm công nghệ chất lượng với giá tốt nhất.
              </p>
            </div>
            <Link
              to="/products"
              className="inline-flex shrink-0 items-center gap-2 rounded-xl bg-white px-5 py-2.5 text-sm font-bold text-primary shadow-sm transition hover:bg-red-50"
            >
              Xem sản phẩm
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
