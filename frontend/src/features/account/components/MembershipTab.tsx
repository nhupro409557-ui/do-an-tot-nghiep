type MembershipTabProps = {
  points: number;
  nextTierInfo: {
    name: string;
    needed: number;
    percentage: number;
  };
};

export function MembershipTab({ points, nextTierInfo }: MembershipTabProps) {
  return (
    <section className="bg-white rounded-xl shadow-sm p-6">
      <h3 className="font-bold text-gray-800 mb-4">Hạng thành viên</h3>
      <p className="text-sm text-gray-600">
        Bạn đang có <strong>{points.toLocaleString('vi-VN')} điểm</strong>.{' '}
        {nextTierInfo.needed > 0
          ? `Cần thêm ${nextTierInfo.needed.toLocaleString('vi-VN')} điểm để lên ${nextTierInfo.name}.`
          : 'Bạn đã đạt hạng cao nhất.'}
      </p>
    </section>
  );
}
