import os

files = [
    ('frontend/src/pages/PrivacyPage.tsx', 'Hệ thống áp dụng các biện pháp bảo mật', 'privacy.png', 'Bảo mật thông tin'),
    ('frontend/src/pages/DisputePage.tsx', 'Mọi tranh chấp trước hết được giải quyết thông qua thương lượng', 'dispute.png', 'Thương lượng tranh chấp'),
    ('frontend/src/pages/TermsPage.tsx', 'Hoạt động giao dịch trên ElectroMart Việt Nam được thực hiện dựa trên nguyên tắc', 'terms.png', 'Nguyên tắc hoạt động'),
    ('frontend/src/pages/AboutPage.tsx', 'ElectroMart Việt Nam định hướng trở thành', 'about.png', 'Tầm nhìn và sứ mệnh'),
    ('frontend/src/pages/PurchasePolicyPage.tsx', 'cam kết xử lý hoàn tiền nhanh chóng', 'payment.png', 'Hoàn tiền nhanh chóng'),
    ('frontend/src/pages/DeliveryPolicyPage.tsx', 'Khi nhận hàng, khách hàng có quyền kiểm tra tình trạng bên ngoài kiện hàng', 'package.png', 'Kiểm tra kiện hàng'),
    ('frontend/src/pages/ReturnWarrantyPolicyPage.tsx', 'Khách hàng gửi yêu cầu qua tổng đài hoặc', 'support.png', 'Hỗ trợ khách hàng'),
    ('frontend/src/pages/MemberPolicyPage.tsx', 'Hệ thống có thể phân hạng thành viên dựa trên tổng giá trị mua hàng', 'reward.png', 'Quyền lợi thành viên VIP')
]

for filepath, search_str, img_name, alt_text in files:
    if not os.path.exists(filepath):
        print(f'File not found: {filepath}')
        continue
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    img_tag = f'<div className="mb-4 mt-2 rounded-xl overflow-hidden border border-slate-100 shadow-sm max-w-md mx-auto bg-slate-50">\\n            <img src="/images/policies/{img_name}" alt="{alt_text}" className="w-full h-auto mix-blend-multiply" />\\n          </div>\\n          '
    
    if search_str in content:
        lines = content.split('\\n')
        for i, line in enumerate(lines):
            if search_str in line:
                indent = len(line) - len(line.lstrip())
                img_html = ' ' * indent + img_tag.strip().replace('\\n', '\n' + ' ' * indent) + '\n' + line
                lines[i] = img_html
                break
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('\\n'.join(lines))
        print(f'Updated {filepath} with {img_name}')
    else:
        print(f'Could not find search string in {filepath}: {search_str}')
