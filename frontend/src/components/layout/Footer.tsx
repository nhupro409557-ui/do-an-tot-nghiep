import React from 'react';
import { Link } from 'react-router-dom';
import { Facebook, Headphones, Mail, MapPin, Phone, ShieldCheck, Truck, Youtube } from 'lucide-react';
import emvLogo from '../../assets/emv-logo-new.svg';

const footerGroups = [
  {
    title: 'Mua hàng',
    links: [
      ['Danh mục sản phẩm', '/category'],
      ['Sản phẩm đang bán', '/products'],
      ['Video sản phẩm', '/video'],
      ['Bảng xếp hạng', '/rankings'],
    ],
  },
  {
    title: 'Hỗ trợ khách hàng',
    links: [
      ['Tra cứu đơn hàng', '/dashboard'],
      ['Giỏ hàng của bạn', '/cart'],
      ['Thanh toán', '/checkout'],
      ['Đăng nhập tài khoản', '/login'],
    ],
  },
  {
    title: 'Tài khoản',
    links: [
      ['Đăng nhập', '/login'],
      ['Đăng ký', '/register'],
      ['Hạng thành viên', '/loyalty'],
      ['Đổi mật khẩu', '/change-password'],
    ],
  },
  {
    title: 'Giới thiệu & Chính sách',
    links: [
      ['Giới thiệu công ty', '/about'],
      ['Chính sách mua hàng & thanh toán', '/purchase-policy'],
      ['Chính sách giao nhận hàng', '/delivery-policy'],
      ['Bảo hành, Đổi trả & Kỹ thuật', '/return-warranty-policy'],
      ['Bảo mật & Dữ liệu cá nhân', '/privacy'],
      ['Khiếu nại & Tranh chấp', '/dispute'],
      ['Chính sách hóa đơn VAT', '/invoice'],
      ['Quy chế hoạt động', '/terms'],
      ['Thành viên & Khuyến mãi', '/member-policy'],
    ],
  },
];

const paymentMethods = ['COD', 'VNPAY', 'MOMO', 'Visa', 'Mastercard'];

export function Footer() {
  return (
    <footer className="relative z-10 mt-10 border-t border-slate-200 bg-white pb-20 text-slate-600 lg:pb-0">
      <div className="mx-auto max-w-7xl px-4 py-8 lg:px-6">
        <div className="grid gap-6 lg:grid-cols-[1.25fr_2fr]">
          <div>
            <Link to="/" className="inline-flex items-center rounded-lg bg-primary px-3 py-2 shadow-sm" aria-label="ElectroMart Vietnam">
              <img src={emvLogo} alt="ElectroMart Vietnam" className="h-14 w-[126px] object-contain" />
            </Link>
            <p className="mt-3 max-w-md text-sm leading-6 text-slate-500">
              Cửa hàng điện tử tập trung vào điện thoại, laptop, phụ kiện và trải nghiệm mua sắm có hỗ trợ tra cứu đơn hàng, voucher, loyalty và nội dung video.
            </p>

            <div className="mt-5 grid gap-3 text-sm">
              <a href="tel:18002097" className="flex items-center gap-2 font-semibold text-slate-700 hover:text-primary">
                <Phone className="h-4 w-4 text-primary" />
                Hotline: 1800.2097
              </a>
              <a href="mailto:support@echophone.local" className="flex items-center gap-2 font-semibold text-slate-700 hover:text-primary">
                <Mail className="h-4 w-4 text-primary" />
                support@echophone.local
              </a>
              <div className="flex items-start gap-2 text-slate-500">
                <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                <span>Hệ thống thương mại điện tử mô phỏng cho đồ án, hỗ trợ vận hành bán lẻ điện tử.</span>
              </div>
            </div>
          </div>

          <div className="grid gap-6 sm:grid-cols-4">
            {footerGroups.map((group) => (
              <div key={group.title}>
                <h3 className="text-sm font-bold uppercase tracking-wide text-slate-950">{group.title}</h3>
                <ul className="mt-3 space-y-2 text-sm">
                  {group.links.map(([label, href]) => (
                    <li key={label}>
                      <Link to={href} className="text-slate-500 transition hover:text-primary">
                        {label}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>

        <div className="mt-8 grid gap-4 border-t border-slate-100 pt-5 md:grid-cols-3">
          <div className="flex items-start gap-3 rounded-md bg-slate-50 p-3">
            <Truck className="h-5 w-5 shrink-0 text-primary" />
            <div>
              <div className="text-sm font-bold text-slate-900">Giao hàng linh hoạt</div>
              <div className="mt-1 text-xs leading-5 text-slate-500">Theo dõi trạng thái đơn hàng trong tài khoản khách hàng.</div>
            </div>
          </div>
          <div className="flex items-start gap-3 rounded-md bg-slate-50 p-3">
            <ShieldCheck className="h-5 w-5 shrink-0 text-primary" />
            <div>
              <div className="text-sm font-bold text-slate-900">Thông tin minh bạch</div>
              <div className="mt-1 text-xs leading-5 text-slate-500">Tập trung vào danh mục, đơn hàng, thanh toán và hỗ trợ sau mua.</div>
            </div>
          </div>
          <div className="flex items-start gap-3 rounded-md bg-slate-50 p-3">
            <Headphones className="h-5 w-5 shrink-0 text-primary" />
            <div>
              <div className="text-sm font-bold text-slate-900">Hỗ trợ sau bán</div>
              <div className="mt-1 text-xs leading-5 text-slate-500">Thông báo, voucher và chăm sóc khách hàng trong cùng hệ thống.</div>
            </div>
          </div>
        </div>

        <div className="mt-6 flex flex-col gap-4 border-t border-slate-100 pt-5 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="text-xs font-bold uppercase tracking-wide text-slate-400">Thanh toán hỗ trợ</div>
            <div className="mt-2 flex flex-wrap gap-2">
              {paymentMethods.map((method) => (
                <span key={method} className="rounded-md border border-slate-200 bg-white px-3 py-1 text-xs font-bold text-slate-600">
                  {method}
                </span>
              ))}
            </div>
          </div>

          <div className="flex items-center gap-2">
            <a href="https://facebook.com" target="_blank" rel="noreferrer" className="rounded-full border border-slate-200 p-2 text-slate-500 transition hover:border-primary hover:text-primary">
              <Facebook className="h-4 w-4" />
            </a>
            <a href="https://youtube.com" target="_blank" rel="noreferrer" className="rounded-full border border-slate-200 p-2 text-slate-500 transition hover:border-primary hover:text-primary">
              <Youtube className="h-4 w-4" />
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
