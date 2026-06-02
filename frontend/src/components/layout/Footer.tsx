import React from 'react';
import { Link } from 'react-router-dom';
import { Facebook, Headphones, Mail, MapPin, Phone, ShieldCheck, Truck, Youtube } from 'lucide-react';
import emvLogo from '../../assets/emv-logo-new.svg';

const footerGroups = [
  {
    title: 'Mua sắm',
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
      ['Đăng nhập / Đăng ký', '/login'],
      ['Hạng thành viên', '/loyalty'],
      ['Đổi mật khẩu', '/change-password'],
    ],
  },
  {
    title: 'Chính sách mua hàng',
    links: [
      ['Chính sách mua bán', '/purchase-policy'],
      ['Chính sách giao nhận', '/delivery-policy'],
      ['Bảo hành & Đổi trả', '/return-warranty-policy'],
      ['Khiếu nại & Tranh chấp', '/dispute'],
    ],
  },
  {
    title: 'Về công ty',
    links: [
      ['Giới thiệu công ty', '/about'],
      ['Bảo mật thông tin', '/privacy'],
      ['Quy chế hoạt động', '/terms'],
      ['Hóa đơn VAT', '/invoice'],
    ],
  },
];

const paymentMethods = ['COD', 'VNPAY', 'MOMO', 'Visa', 'Mastercard'];

export function Footer() {
  return (
    <footer className="relative z-10 mt-10 border-t border-slate-200 bg-white pb-20 text-slate-600 lg:pb-0">
      <div className="mx-auto max-w-7xl px-4 py-12 lg:px-6">
        <div className="grid gap-10 lg:grid-cols-[1fr_2.5fr]">
          <div className="max-w-sm">
            <Link to="/" className="inline-flex items-center rounded-lg bg-[#d70018] px-4 py-2.5 shadow-sm transition-transform hover:-translate-y-0.5" aria-label="ElectroMart Vietnam">
              <img src={emvLogo} alt="ElectroMart Vietnam" className="h-12 w-[110px] object-contain brightness-0 invert" />
            </Link>
            <p className="mt-5 text-sm leading-relaxed text-slate-500">
              Hệ thống bán lẻ điện thoại, laptop và phụ kiện chính hãng. Mang đến trải nghiệm mua sắm thông minh với hệ thống tích điểm và ưu đãi cá nhân hóa.
            </p>

            <div className="mt-6 flex flex-col gap-4 text-sm">
              <a href="tel:18002097" className="group flex items-center gap-3 font-bold text-slate-700 transition hover:text-[#d70018]">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-red-50 text-[#d70018] transition-colors group-hover:bg-[#d70018] group-hover:text-white">
                  <Phone className="h-4 w-4" />
                </div>
                <span>Hotline: 1800.2097</span>
              </a>
              <a href="mailto:support@echophone.local" className="group flex items-center gap-3 font-semibold text-slate-700 transition hover:text-[#d70018]">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-50 text-slate-500 transition-colors group-hover:bg-[#d70018] group-hover:text-white">
                  <Mail className="h-4 w-4" />
                </div>
                <span>support@echophone.local</span>
              </a>
              <div className="flex items-start gap-3 font-medium text-slate-500">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-slate-50 text-slate-500">
                  <MapPin className="h-4 w-4" />
                </div>
                <span className="mt-2 leading-relaxed">Hệ thống mô phỏng, hỗ trợ vận hành bán lẻ điện tử.</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-x-6 gap-y-10 sm:grid-cols-4 lg:pt-2">
            {footerGroups.map((group) => (
              <div key={group.title}>
                <h3 className="mb-5 text-sm font-bold uppercase tracking-wider text-slate-900">{group.title}</h3>
                <ul className="flex flex-col gap-3 text-sm">
                  {group.links.map(([label, href]) => (
                    <li key={label}>
                      <Link to={href} className="font-medium text-slate-500 transition-colors hover:text-[#d70018]">
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
