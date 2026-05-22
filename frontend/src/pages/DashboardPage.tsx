import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import {
  AlertTriangle,
  CheckCircle2,
  ClipboardList,
  Diamond,
  Eye,
  EyeOff,
  Gift,
  Home,
  KeyRound,
  LogOut,
  Mail,
  MapPin,
  Pencil,
  Phone,
  Plus,
  Settings,
  ShieldCheck,
  Star,
  Trash2,
  UserRound,
} from 'lucide-react';
import {
  changePassword,
  deleteCurrentUser,
  getAuthErrorMessage,
  signOut,
  updateUserProfile,
} from '../services/authDb';
import { apiDb } from '../services/apiDb';
import { DeleteAccountModal } from '../components/account/DeleteAccountModal';
import { LocationPicker } from '../components/LocationPicker';
import { VietnamAddressSelector, AddressData } from '../components/VietnamAddressSelector';

type AccountTab = 'overview' | 'orders' | 'membership' | 'addresses' | 'settings';

type Address = {
  id: string;
  receiverName: string;
  receiverPhone: string;
  addressLine: string; // The combined full address for display/backward compatibility
  addressData?: AddressData; // Structured data
  mapQueryAddress?: string;
  lat?: number;
  lng?: number;
  mapUrl?: string;
  note?: string;
  isDefault: boolean;
  isMapVerified: boolean;
};

type ProfileForm = {
  displayName: string;
  birthDate: string;
  gender: string;
  phone: string;
  avatarUrl: string;
  verificationRole: string;
  schoolOrWorkplace: string;
  verificationCode: string;
};

type AuthSession = {
  id: string;
  current: boolean;
  userAgent?: string | null;
  ipAddress?: string | null;
  createdAt: string;
  rotatedAt?: string | null;
  expiresAt: string;
};

const emptyAddress = {
  receiverName: '',
  receiverPhone: '',
  addressLine: '',
  addressData: {
    provinceId: '',
    provinceName: '',
    districtId: '',
    districtName: '',
    wardId: '',
    wardName: '',
    street: ''
  } as AddressData,
  mapQueryAddress: '',
  note: '',
  lat: undefined as number | undefined,
  lng: undefined as number | undefined,
  mapUrl: '',
};

export default function DashboardPage() {
  const { user, userData, loading } = useAuth();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState<AccountTab>('overview');
  const [orders, setOrders] = useState<any[]>([]);
  const [authSessions, setAuthSessions] = useState<AuthSession[]>([]);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [profileMessage, setProfileMessage] = useState('');
  const [passwordMessage, setPasswordMessage] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [isProfileEditing, setIsProfileEditing] = useState(false);
  const [isPasswordEditing, setIsPasswordEditing] = useState(false);
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [addressDraft, setAddressDraft] = useState(emptyAddress);
  const [isAddressFormOpen, setIsAddressFormOpen] = useState(false);
  const [editingAddressId, setEditingAddressId] = useState<string | null>(null);
  const [profileForm, setProfileForm] = useState<ProfileForm>({
    displayName: '',
    birthDate: '',
    gender: '',
    phone: '',
    avatarUrl: '',
    verificationRole: '',
    schoolOrWorkplace: '',
    verificationCode: '',
  });

  const addresses = useMemo<Address[]>(() => userData?.addresses || [], [userData]);

  useEffect(() => {
    if (!userData || !user) return;
    setProfileForm({
      displayName: userData.displayName || user.displayName || '',
      birthDate: userData.birthDate || '',
      gender: userData.gender || '',
      phone: userData.phone || '',
      avatarUrl: userData.avatarUrl || '',
      verificationRole: userData.verificationRole || '',
      schoolOrWorkplace: userData.schoolOrWorkplace || '',
      verificationCode: userData.verificationCode || '',
    });
  }, [user, userData]);

  useEffect(() => {
    if (!user) return;
    apiDb.listOrders(user.uid)
      .then(data => setOrders(data.sort((a: any, b: any) => String(b.createdAt || '').localeCompare(String(a.createdAt || '')))))
      .catch(e => console.log('Error loading orders', e));
  }, [user]);

  useEffect(() => {
    if (!user || activeTab !== 'settings') return;
    apiDb.listAuthSessions()
      .then(data => setAuthSessions(data))
      .catch(e => console.log('Error loading auth sessions', e));
  }, [user, activeTab]);

  const handleDeleteAccount = async () => {
    if (!user) return;
    setIsDeleting(true);
    try {
      updateUserProfile(user.uid, { points: 0, tier: 'S-New' });
      await deleteCurrentUser();
      navigate('/');
    } catch (error: any) {
      if (error.code === 'auth/requires-recent-login') {
        alert('Vui lòng đăng nhập lại trước khi xóa tài khoản.');
        await signOut();
      } else {
        alert('Có lỗi xảy ra khi xóa tài khoản.');
      }
    } finally {
      setIsDeleting(false);
      setShowDeleteModal(false);
    }
  };

  const handleRevokeSession = async (sessionId: string, isCurrent: boolean) => {
    await apiDb.revokeAuthSession(sessionId);
    if (isCurrent) {
      await signOut();
      navigate('/login');
      return;
    }
    setAuthSessions(sessions => sessions.filter(session => session.id !== sessionId));
  };

  const handleProfileSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    if (!user) return;
    updateUserProfile(user.uid, {
      ...profileForm,
      displayName: profileForm.displayName.trim(),
      phone: profileForm.phone.trim(),
      verificationStatus: profileForm.verificationRole ? 'PENDING' : 'NONE',
    });
    setProfileMessage('Đã lưu cài đặt tài khoản.');
    setIsProfileEditing(false);
    setTimeout(() => setProfileMessage(''), 2500);
  };

  const getNewAddressLine = (data?: AddressData) => {
    if (!data) return addressDraft.addressLine;
    return [data.street, data.wardName, data.provinceName].filter(Boolean).join(', ');
  };

  const stripAdministrativePrefix = (value?: string) =>
    (value || '')
      .replace(/^(phường|phuong|xã|xa|thị trấn|thi tran)\s+/i, '')
      .replace(/^(thành phố|thanh pho|tp\.?|tỉnh|tinh)\s+/i, '')
      .trim();

  const getMapSearchAddress = (data?: AddressData) => {
    if (!data) return addressDraft.addressLine;
    return [
      data.street,
      stripAdministrativePrefix(data.wardName),
      stripAdministrativePrefix(data.provinceName),
    ].filter(Boolean).join(', ');
  };

  const mapPredictionAddress = getMapSearchAddress(addressDraft.addressData);

  const handleAddAddress = (event: React.FormEvent) => {
    event.preventDefault();
    const fullAddressLine = getNewAddressLine(addressDraft.addressData);

    if (editingAddressId) {
      updateUserProfile(user.uid, {
        addresses: addresses.map(address => address.id === editingAddressId ? {
          ...address,
          receiverName: addressDraft.receiverName.trim(),
          receiverPhone: addressDraft.receiverPhone.trim(),
          addressLine: fullAddressLine,
          addressData: addressDraft.addressData,
          mapQueryAddress: mapPredictionAddress,
          lat: addressDraft.lat,
          lng: addressDraft.lng,
          mapUrl: addressDraft.mapUrl,
          note: addressDraft.note.trim(),
          isMapVerified: Boolean(addressDraft.mapUrl),
        } : address),
      });
    } else {
      const nextAddress: Address = {
        id: crypto.randomUUID(),
        receiverName: addressDraft.receiverName.trim(),
        receiverPhone: addressDraft.receiverPhone.trim(),
        addressLine: fullAddressLine,
        addressData: addressDraft.addressData,
        mapQueryAddress: mapPredictionAddress,
        lat: addressDraft.lat,
        lng: addressDraft.lng,
        mapUrl: addressDraft.mapUrl,
        note: addressDraft.note.trim(),
        isDefault: addresses.length === 0,
        isMapVerified: Boolean(addressDraft.mapUrl),
      };

      updateUserProfile(user.uid, { addresses: [...addresses, nextAddress] });
    }

    setAddressDraft(emptyAddress);
    setEditingAddressId(null);
    setIsAddressFormOpen(false);
  };

  const openNewAddressForm = () => {
    setAddressDraft(emptyAddress);
    setEditingAddressId(null);
    setIsAddressFormOpen(true);
  };

  const openEditAddressForm = (address: Address) => {
    setAddressDraft({
      receiverName: address.receiverName,
      receiverPhone: address.receiverPhone,
      addressLine: address.addressLine,
      addressData: address.addressData || {
        provinceId: '', provinceName: '',
        districtId: '', districtName: '',
        wardId: '', wardName: '',
        street: address.addressLine
      },
      mapQueryAddress: address.mapQueryAddress || '',
      lat: address.lat,
      lng: address.lng,
      mapUrl: address.mapUrl || '',
      note: address.note || '',
    });
    setEditingAddressId(address.id);
    setIsAddressFormOpen(true);
  };

  const updateAddresses = (nextAddresses: Address[]) => {
    if (!user) return;
    updateUserProfile(user.uid, { addresses: nextAddresses });
  };

  const verifyAddressOnMap = (address: Address) => {
    const mapUrl = address.mapUrl || `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address.addressLine)}`;
    window.open(mapUrl, '_blank');
    updateAddresses(addresses.map(item => item.id === address.id ? { ...item, mapUrl, isMapVerified: true } : item));
  };

  const handleChangePassword = async (event: React.FormEvent) => {
    event.preventDefault();
    setPasswordMessage('');
    setPasswordError('');

    if (newPassword !== confirmPassword) {
      setPasswordError('Mật khẩu mới nhập lại không khớp.');
      return;
    }
    if (newPassword === currentPassword) {
      setPasswordError('Mật khẩu mới cần khác mật khẩu hiện tại.');
      return;
    }

    setIsChangingPassword(true);
    try {
      await changePassword(currentPassword, newPassword);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setIsPasswordEditing(false);
      setPasswordMessage('Đổi mật khẩu thành công.');
    } catch (err: any) {
      setPasswordError(getAuthErrorMessage(err.code, err.message || 'Không thể đổi mật khẩu.'));
    } finally {
      setIsChangingPassword(false);
    }
  };

  const points = userData?.points || 0;
  const nextTierInfo = points < 3000
    ? { name: 'S-Mem', needed: 3000 - points, percentage: (points / 3000) * 100 }
    : points < 15000
      ? { name: 'S-Vip', needed: 15000 - points, percentage: ((points - 3000) / 12000) * 100 }
      : { name: 'Tối đa', needed: 0, percentage: 100 };

  if (loading || !user) return <div className="text-center py-20">Đang tải...</div>;

  const avatarLetter = user.displayName?.charAt(0) || user.email?.charAt(0) || 'U';
  const inputType = showPassword ? 'text' : 'password';
  const navItems = [
    { id: 'overview', label: 'Tổng quan', icon: Home },
    { id: 'orders', label: 'Lịch sử mua hàng', icon: ClipboardList },
    { id: 'membership', label: 'Hạng thành viên', icon: Diamond },
    { id: 'addresses', label: 'Địa chỉ', icon: MapPin },
    { id: 'settings', label: 'Cài đặt tài khoản', icon: Settings },
  ] as const;

  return (
    <div className="container mx-auto px-4 py-8 max-w-[1200px]">
      <DeleteAccountModal
        isOpen={showDeleteModal}
        onClose={() => setShowDeleteModal(false)}
        onConfirm={handleDeleteAccount}
        currentLoyaltyPoints={points}
        isDeleting={isDeleting}
      />

      <div className="bg-white rounded-xl shadow-sm p-6 mb-4 flex flex-col md:flex-row gap-6 md:items-center">
        <div className="flex gap-4 items-center flex-1 md:border-r border-gray-100 md:pr-6">
          {profileForm.avatarUrl ? (
            <img src={profileForm.avatarUrl} alt="Ảnh đại diện" className="w-16 h-16 rounded-full object-cover shrink-0 border border-gray-100" />
          ) : (
            <div className="w-16 h-16 bg-yellow-400 rounded-full flex items-center justify-center text-xl font-bold text-gray-800 shrink-0">
              {avatarLetter.toUpperCase()}
            </div>
          )}
          <div className="flex-1 min-w-0">
            <h2 className="text-lg font-bold text-gray-800 truncate">{profileForm.displayName || user.displayName || 'Khách hàng'}</h2>
            <p className="text-sm text-gray-500 mb-1 truncate">{user.email}</p>
            <div className="flex flex-wrap gap-2">
              <span className="bg-[#d70018] text-white px-2 py-0.5 rounded text-xs font-bold leading-tight">{userData?.tier || 'S-New'}</span>
              {userData?.verificationRole && (
                <span className="bg-blue-50 text-blue-700 px-2 py-0.5 rounded text-xs font-bold leading-tight">
                  {userData.verificationRole === 'student' ? 'Sinh viên' : 'Giảng viên'}
                </span>
              )}
            </div>
          </div>
        </div>

        <div className="flex-[2] md:px-6">
          <div className="bg-gradient-to-br from-slate-900 to-slate-700 rounded-xl shadow-lg p-5 text-white w-full max-w-md">
            <div className="flex justify-between items-start mb-2">
              <span className="text-[10px] bg-yellow-500 text-slate-900 px-2 py-0.5 rounded-full font-bold">{userData?.tier || 'S-New'}</span>
              <Star className="w-5 h-5 text-yellow-400 fill-yellow-400" />
            </div>
            <div className="flex items-end gap-2 mb-3">
              <p className="text-2xl font-bold leading-none">{points.toLocaleString('vi-VN')} <span className="text-sm font-normal opacity-70">Điểm</span></p>
            </div>
            <div className="w-full bg-white/20 h-2 rounded-full mb-2 overflow-hidden shadow-inner">
              <div className="bg-yellow-400 h-full rounded-full transition-all duration-1000 ease-out" style={{ width: `${Math.min(100, Math.max(0, nextTierInfo.percentage))}%` }} />
            </div>
            <p className="text-[11px] opacity-80 font-medium">
              {nextTierInfo.needed > 0 ? <>Còn <strong className="text-yellow-400">{nextTierInfo.needed.toLocaleString('vi-VN')} điểm</strong> để lên hạng {nextTierInfo.name}</> : <span className="text-yellow-400">Bạn đã đạt hạng cao nhất!</span>}
            </p>
          </div>
        </div>

        <div className="flex-1 md:pl-6 md:border-l border-gray-100 flex justify-end">
          <button onClick={() => signOut()} className="inline-flex items-center justify-center gap-2 text-sm font-medium text-red-600 hover:text-white hover:bg-red-600 border border-red-600 transition-colors px-4 py-2 rounded-lg w-full">
            <LogOut className="w-4 h-4" /> Đăng xuất
          </button>
        </div>
      </div>

      <div className="flex flex-col lg:flex-row gap-6 mt-6">
        <aside className="w-full lg:w-64 bg-white rounded-xl shadow-sm py-4 h-fit">
          <ul className="text-sm font-medium text-gray-700">
            {navItems.map(item => {
              const Icon = item.icon;
              const isActive = activeTab === item.id;
              return (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => setActiveTab(item.id)}
                    className={`w-full flex items-center gap-3 px-6 py-3 border-l-4 transition-colors ${isActive ? 'text-[#d70018] bg-red-50 border-[#d70018]' : 'border-transparent hover:bg-gray-50 hover:text-red-500'}`}
                  >
                    <Icon className="w-4 h-4" /> {item.label}
                  </button>
                </li>
              );
            })}
          </ul>
        </aside>

        <div className="flex-1 flex flex-col gap-6">
          {activeTab === 'overview' && (
            <>
              <div className="bg-blue-50 text-blue-900 px-6 py-4 rounded-xl flex items-center gap-3 text-sm border border-blue-100">
                <ShieldCheck className="w-5 h-5 shrink-0" />
                <span>Nâng cấp hạng thành viên để nhận ngay voucher 500k sinh nhật!</span>
              </div>

              <section className="bg-white rounded-xl shadow-sm p-6">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
                  <h3 className="font-bold text-gray-800">Địa chỉ giao hàng</h3>
                  <button onClick={() => setActiveTab('addresses')} className="text-sm font-semibold text-[#d70018]">Quản lý địa chỉ</button>
                </div>
                {addresses.length === 0 ? (
                  <p className="text-sm text-gray-500">Bạn chưa có địa chỉ. Thêm địa chỉ để hỗ trợ thanh toán và tích hợp đơn vị vận chuyển.</p>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {addresses.slice(0, 2).map(address => (
                      <div key={address.id} className="border border-gray-100 rounded-lg p-4">
                        <div className="flex items-center justify-between gap-3 mb-2">
                          <p className="font-bold text-sm text-gray-800">{address.receiverName}</p>
                          {address.isDefault && <span className="text-[11px] bg-red-50 text-[#d70018] px-2 py-1 rounded">Mặc định</span>}
                        </div>
                        <p className="text-sm text-gray-600 flex items-center gap-2"><Phone className="w-4 h-4" /> {address.receiverPhone}</p>
                        <p className="text-sm text-gray-600 mt-2 flex gap-2"><MapPin className="w-4 h-4 shrink-0 mt-0.5" /> {address.addressLine}</p>
                        <p className={`text-xs mt-3 font-semibold ${address.isMapVerified ? 'text-green-600' : 'text-amber-600'}`}>
                          {address.isMapVerified ? 'Đã xác minh trên Google Maps' : 'Chưa xác minh bản đồ'}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <section className="bg-white rounded-xl shadow-sm p-6">
                  <h3 className="font-bold text-gray-800 mb-4">Đơn hàng gần đây</h3>
                  {orders.length === 0 ? (
                    <p className="text-sm text-gray-500 py-4">Bạn chưa có đơn hàng nào.</p>
                  ) : (
                    <div className="space-y-4">
                      {orders.slice(0, 3).map(order => (
                        <div key={order.id} className="border border-gray-100 rounded-lg p-4 text-sm">
                          <div className="flex justify-between mb-2">
                            <span className="font-mono font-medium text-gray-700">#{order.id.slice(0, 8).toUpperCase()}</span>
                            <span className="text-green-600 bg-green-50 px-2 py-0.5 rounded text-xs font-semibold">{order.status}</span>
                          </div>
                          <div className="text-gray-500 text-xs mb-3">Ngày đặt: {order.createdAt ? new Date(order.createdAt).toLocaleDateString('vi-VN') : ''}</div>
                          <div className="flex justify-between font-bold text-gray-800 border-t border-dashed pt-3">
                            <span className="font-normal text-gray-500">Tổng thanh toán:</span>
                            <span className="text-red-600">{order.totalAmount?.toLocaleString('vi-VN')}đ</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </section>

                <section className="bg-white rounded-xl shadow-sm p-6">
                  <h3 className="font-bold text-gray-800 mb-4">Ưu đãi / Nhiệm vụ</h3>
                  <button onClick={() => navigate('/loyalty')} className="w-full flex gap-4 items-center border border-gray-100 rounded-lg p-4 hover:border-red-100 transition-colors text-left">
                    <div className="w-12 h-12 bg-[#d70018] text-white rounded-lg flex items-center justify-center shadow-sm"><Gift className="w-6 h-6" /></div>
                    <div>
                      <h4 className="font-bold text-sm text-gray-800 mb-1">Cửa hàng quy đổi loyalty</h4>
                      <p className="text-blue-600 font-semibold text-xs mb-1">Dùng điểm đổi mã giảm giá</p>
                    </div>
                  </button>
                </section>
              </div>
            </>
          )}

          {activeTab === 'orders' && (
            <section className="bg-white rounded-xl shadow-sm p-6">
              <h3 className="font-bold text-gray-800 mb-4">Lịch sử mua hàng</h3>
              <p className="text-sm text-gray-500">{orders.length ? 'Các đơn hàng của bạn sẽ hiển thị tại đây.' : 'Bạn chưa có đơn hàng nào.'}</p>
            </section>
          )}

          {activeTab === 'membership' && (
            <section className="bg-white rounded-xl shadow-sm p-6">
              <h3 className="font-bold text-gray-800 mb-4">Hạng thành viên</h3>
              <p className="text-sm text-gray-600">Bạn đang có <strong>{points.toLocaleString('vi-VN')} điểm</strong>. {nextTierInfo.needed > 0 ? `Cần thêm ${nextTierInfo.needed.toLocaleString('vi-VN')} điểm để lên ${nextTierInfo.name}.` : 'Bạn đã đạt hạng cao nhất.'}</p>
            </section>
          )}

          {activeTab === 'addresses' && (
            <section className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-5">
                <div className="flex items-center gap-3">
                  <MapPin className="w-6 h-6 text-[#d70018]" />
                  <h3 className="font-bold text-gray-800">Địa chỉ nhận hàng</h3>
                </div>
                <button type="button" onClick={openNewAddressForm} className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg bg-[#d70018] text-white text-sm font-bold hover:bg-red-700">
                  <Plus className="w-4 h-4" /> Thêm địa chỉ
                </button>
              </div>

              {isAddressFormOpen && (
                <form onSubmit={handleAddAddress} className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5 rounded-lg border border-slate-100 bg-slate-50 p-4">
                  <input required value={addressDraft.receiverName} onChange={event => setAddressDraft({ ...addressDraft, receiverName: event.target.value })} placeholder="Họ tên người nhận" className="px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] bg-white disabled:bg-gray-50 disabled:text-gray-500" />
                  <input required value={addressDraft.receiverPhone} onChange={event => setAddressDraft({ ...addressDraft, receiverPhone: event.target.value })} placeholder="Số điện thoại người nhận" className="px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] bg-white disabled:bg-gray-50 disabled:text-gray-500" />
                  
                  <div className="md:col-span-2">
                    <label className="text-sm font-semibold text-gray-700 block mb-2">Địa chỉ nhận hàng</label>
                    <VietnamAddressSelector 
                      value={addressDraft.addressData!} 
                      onChange={(data) => setAddressDraft(prev => ({ 
                        ...prev, 
                        addressData: data,
                        addressLine: [data.street, data.wardName, data.provinceName].filter(Boolean).join(', '),
                        mapQueryAddress: '',
                        mapUrl: '',
                        lat: undefined,
                        lng: undefined,
                      }))} 
                    />
                  </div>

                  <input value={addressDraft.note} onChange={event => setAddressDraft({ ...addressDraft, note: event.target.value })} placeholder="Ghi chú giao hàng (không bắt buộc)" className="md:col-span-2 px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] bg-white disabled:bg-gray-50 disabled:text-gray-500" />
                  
                  <div className="md:col-span-2">
                    <LocationPicker 
                      address={mapPredictionAddress}
                      mapUrl={addressDraft.mapUrl}
                      lat={addressDraft.lat}
                      lng={addressDraft.lng}
                      onPredict={(mapUrl, coords) => setAddressDraft(prev => ({
                        ...prev,
                        mapUrl,
                        lat: coords?.lat,
                        lng: coords?.lng,
                      }))}
                    />
                    {mapPredictionAddress && (
                      <p className="mt-2 text-xs text-slate-500">
                        Google Maps se tim theo dia chi moi: {mapPredictionAddress}
                      </p>
                    )}
                  </div>

                  <button type="button" onClick={() => { setIsAddressFormOpen(false); setEditingAddressId(null); setAddressDraft(emptyAddress); }} className="py-3 rounded-lg border border-gray-300 text-gray-700 font-bold hover:bg-white">Hủy</button>
                  <button type="submit" disabled={!addressDraft.addressData?.provinceId || !addressDraft.addressData?.wardId || !addressDraft.addressData?.street || !addressDraft.mapUrl} className="inline-flex justify-center items-center gap-2 bg-slate-900 hover:bg-slate-800 text-white py-3 rounded-lg font-bold transition-colors disabled:opacity-50">
                    {editingAddressId ? 'Lưu địa chỉ' : 'Thêm địa chỉ'}
                  </button>
                  {!addressDraft.mapUrl && (
                    <p className="md:col-span-2 text-xs text-amber-600">
                      Vui long bam Du doan tu dia chi de ghim vi tri tren ban do truoc khi luu.
                    </p>
                  )}
                </form>
              )}

              <div className="space-y-3">
                {addresses.map(address => (
                  <div key={address.id} className="border border-gray-100 rounded-lg p-4">
                    <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-3">
                      <div>
                        <div className="flex flex-wrap items-center gap-2 mb-2">
                          <p className="font-bold text-gray-800">{address.receiverName}</p>
                          {address.isDefault && <span className="text-[11px] bg-red-50 text-[#d70018] px-2 py-1 rounded">Mặc định</span>}
                          {address.isMapVerified && <span className="inline-flex items-center gap-1 text-[11px] bg-green-50 text-green-700 px-2 py-1 rounded"><CheckCircle2 className="w-3 h-3" /> Đã xác minh</span>}
                        </div>
                        <p className="text-sm text-gray-600">{address.receiverPhone}</p>
                        <p className="text-sm text-gray-600 mt-1">{address.addressLine}</p>
                        {address.note && <p className="text-xs text-gray-400 mt-1">{address.note}</p>}
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <button type="button" onClick={() => openEditAddressForm(address)} className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-gray-200 text-gray-700 text-sm font-semibold hover:bg-gray-50"><Pencil className="w-4 h-4" /> Chỉnh sửa</button>
                        <button type="button" onClick={() => verifyAddressOnMap(address)} className="px-3 py-2 rounded-lg border border-blue-200 text-blue-700 text-sm font-semibold hover:bg-blue-50">Xác minh Google Maps</button>
                        <button type="button" onClick={() => updateAddresses(addresses.map(item => ({ ...item, isDefault: item.id === address.id })))} className="px-3 py-2 rounded-lg border border-gray-200 text-gray-700 text-sm font-semibold hover:bg-gray-50">Đặt mặc định</button>
                        <button type="button" onClick={() => updateAddresses(addresses.filter(item => item.id !== address.id))} className="px-3 py-2 rounded-lg border border-red-100 text-red-600 text-sm font-semibold hover:bg-red-50"><Trash2 className="w-4 h-4" /></button>
                      </div>
                    </div>
                  </div>
                ))}
                {addresses.length === 0 && <p className="text-sm text-gray-500">Chưa có địa chỉ nào. Bấm thêm địa chỉ để nhập thông tin nhận hàng.</p>}
              </div>
            </section>
          )}

          {activeTab === 'settings' && (
            <div className="space-y-6">
              <section className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-5">
                  <div className="flex items-center gap-3">
                    <UserRound className="w-6 h-6 text-[#d70018]" />
                    <h3 className="font-bold text-gray-800">Cài đặt tài khoản</h3>
                  </div>
                  {!isProfileEditing && (
                    <button type="button" onClick={() => setIsProfileEditing(true)} className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg border border-[#d70018] text-[#d70018] text-sm font-bold hover:bg-red-50">
                      <Pencil className="w-4 h-4" /> Chỉnh sửa
                    </button>
                  )}
                </div>
                {profileMessage && <div className="bg-green-50 text-green-700 p-3 rounded-lg mb-5 text-sm">{profileMessage}</div>}
                <form onSubmit={handleProfileSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <label className="text-sm font-semibold text-gray-700 md:col-span-2">Gmail
                    <div className="mt-2 flex items-center gap-3 px-4 py-3 border border-gray-200 rounded-lg bg-gray-50 text-gray-500">
                      <Mail className="w-4 h-4" />
                      <span className="truncate">{user.email}</span>
                    </div>
                  </label>
                  <label className="text-sm font-semibold text-gray-700">Họ tên
                    <input disabled={!isProfileEditing} value={profileForm.displayName} onChange={event => setProfileForm({ ...profileForm, displayName: event.target.value })} className="mt-2 w-full px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] disabled:bg-gray-50 disabled:text-gray-500" />
                  </label>
                  <label className="text-sm font-semibold text-gray-700">Số điện thoại chính
                    <input disabled={!isProfileEditing} value={profileForm.phone} onChange={event => setProfileForm({ ...profileForm, phone: event.target.value })} className="mt-2 w-full px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] disabled:bg-gray-50 disabled:text-gray-500" />
                  </label>
                  <label className="text-sm font-semibold text-gray-700">Ngày tháng năm sinh
                    <input disabled={!isProfileEditing} type="date" value={profileForm.birthDate} onChange={event => setProfileForm({ ...profileForm, birthDate: event.target.value })} className="mt-2 w-full px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] disabled:bg-gray-50 disabled:text-gray-500" />
                  </label>
                  <label className="text-sm font-semibold text-gray-700">Giới tính
                    <select disabled={!isProfileEditing} value={profileForm.gender} onChange={event => setProfileForm({ ...profileForm, gender: event.target.value })} className="mt-2 w-full px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] disabled:bg-gray-50 disabled:text-gray-500">
                      <option value="">Chưa chọn</option>
                      <option value="female">Nữ</option>
                      <option value="male">Nam</option>
                      <option value="other">Khác</option>
                    </select>
                  </label>
                  <label className="text-sm font-semibold text-gray-700 md:col-span-2">Ảnh đại diện (có thể để trống)
                    <input disabled={!isProfileEditing} value={profileForm.avatarUrl} onChange={event => setProfileForm({ ...profileForm, avatarUrl: event.target.value })} placeholder="Dán liên kết ảnh nếu muốn dùng ảnh đại diện" className="mt-2 w-full px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] disabled:bg-gray-50 disabled:text-gray-500" />
                  </label>
                  <div className="md:col-span-2 grid grid-cols-1 md:grid-cols-3 gap-4 bg-slate-50 rounded-lg p-4">
                    <label className="text-sm font-semibold text-gray-700">Xác minh
                      <select disabled={!isProfileEditing} value={profileForm.verificationRole} onChange={event => setProfileForm({ ...profileForm, verificationRole: event.target.value })} className="mt-2 w-full px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] bg-white disabled:bg-gray-50 disabled:text-gray-500">
                        <option value="">Không xác minh</option>
                        <option value="student">Sinh viên</option>
                        <option value="lecturer">Giảng viên</option>
                      </select>
                    </label>
                    <label className="text-sm font-semibold text-gray-700">Trường / đơn vị
                      <input disabled={!isProfileEditing} value={profileForm.schoolOrWorkplace} onChange={event => setProfileForm({ ...profileForm, schoolOrWorkplace: event.target.value })} className="mt-2 w-full px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] bg-white disabled:bg-gray-50 disabled:text-gray-500" />
                    </label>
                    <label className="text-sm font-semibold text-gray-700">Mã sinh viên / giảng viên
                      <input disabled={!isProfileEditing} value={profileForm.verificationCode} onChange={event => setProfileForm({ ...profileForm, verificationCode: event.target.value })} className="mt-2 w-full px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] bg-white disabled:bg-gray-50 disabled:text-gray-500" />
                    </label>
                  </div>
                  {isProfileEditing && (
                    <div className="md:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-3">
                      <button type="button" onClick={() => setIsProfileEditing(false)} className="border border-gray-300 text-gray-700 py-3 rounded-lg font-bold hover:bg-gray-50">Hủy</button>
                      <button type="submit" className="bg-[#d70018] hover:bg-red-700 text-white py-3 rounded-lg font-bold transition-colors">Lưu thông tin tài khoản</button>
                    </div>
                  )}
                </form>
              </section>

              <section className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
                <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-5">
                  <div className="flex items-center gap-3">
                    <KeyRound className="w-6 h-6 text-[#d70018]" />
                    <h3 className="font-bold text-gray-800">Đổi mật khẩu</h3>
                  </div>
                  {!isPasswordEditing && (
                    <button type="button" onClick={() => setIsPasswordEditing(true)} className="inline-flex items-center justify-center gap-2 px-4 py-2 rounded-lg border border-[#d70018] text-[#d70018] text-sm font-bold hover:bg-red-50">
                      <KeyRound className="w-4 h-4" /> Đổi mật khẩu
                    </button>
                  )}
                </div>
                {passwordMessage && <div className="bg-green-50 text-green-700 p-3 rounded-lg mb-5 text-sm">{passwordMessage}</div>}
                {passwordError && <div className="bg-red-50 text-red-600 p-3 rounded-lg mb-5 text-sm">{passwordError}</div>}
                {isPasswordEditing ? (
                <form onSubmit={handleChangePassword} className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <input type={inputType} required value={currentPassword} onChange={event => setCurrentPassword(event.target.value)} placeholder="Mật khẩu hiện tại" className="px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] disabled:bg-gray-50 disabled:text-gray-500" />
                  <input type={inputType} required minLength={6} value={newPassword} onChange={event => setNewPassword(event.target.value)} placeholder="Mật khẩu mới" className="px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] disabled:bg-gray-50 disabled:text-gray-500" />
                  <input type={inputType} required minLength={6} value={confirmPassword} onChange={event => setConfirmPassword(event.target.value)} placeholder="Nhập lại mật khẩu mới" className="px-4 py-3 border border-gray-300 rounded-lg outline-none focus:border-[#d70018] disabled:bg-gray-50 disabled:text-gray-500" />
                  <button type="button" onClick={() => setShowPassword(value => !value)} className="inline-flex items-center justify-center gap-2 text-sm font-semibold text-slate-600 hover:text-[#d70018]">
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                    {showPassword ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}
                  </button>
                  <button type="submit" disabled={isChangingPassword} className="md:col-span-2 bg-[#d70018] hover:bg-red-700 text-white py-3 rounded-lg font-bold transition-colors disabled:opacity-60">
                    {isChangingPassword ? 'Đang cập nhật...' : 'Lưu mật khẩu mới'}
                  </button>
                </form>
                ) : (
                  <p className="text-sm text-gray-500">Bấm Đổi mật khẩu để nhập mật khẩu hiện tại và mật khẩu mới.</p>
                )}
              </section>

              <section className="bg-white rounded-xl shadow-sm border border-slate-100 p-6">
                <div className="flex items-center gap-3 mb-5">
                  <ShieldCheck className="w-6 h-6 text-[#d70018]" />
                  <h3 className="font-bold text-gray-800">Phiên đăng nhập</h3>
                </div>
                {authSessions.length === 0 ? (
                  <p className="text-sm text-gray-500">Chưa có dữ liệu phiên đăng nhập.</p>
                ) : (
                  <div className="space-y-3">
                    {authSessions.map(session => (
                      <div key={session.id} className="flex flex-col gap-3 rounded-lg border border-slate-100 p-4 md:flex-row md:items-center md:justify-between">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <p className="truncate text-sm font-bold text-gray-800">{session.userAgent || 'Thiết bị không xác định'}</p>
                            {session.current && <span className="rounded bg-green-50 px-2 py-0.5 text-xs font-bold text-green-700">Hiện tại</span>}
                          </div>
                          <p className="mt-1 text-xs text-gray-500">IP: {session.ipAddress || 'unknown'} · Tạo lúc: {new Date(session.createdAt).toLocaleString('vi-VN')}</p>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleRevokeSession(session.id, session.current)}
                          className="inline-flex items-center justify-center gap-2 rounded-lg border border-red-200 px-3 py-2 text-sm font-bold text-red-600 hover:bg-red-50"
                        >
                          <LogOut className="w-4 h-4" /> Đăng xuất phiên này
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </section>

              <section className="bg-white rounded-xl shadow-sm border border-red-100 p-6">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <AlertTriangle className="w-6 h-6 text-red-600 shrink-0" />
                    <div>
                      <h3 className="font-bold text-red-700">Xóa tài khoản</h3>
                      <p className="text-sm text-gray-500 mt-1">Thao tác này sẽ xóa tài khoản và hồ sơ đang lưu trong bản demo.</p>
                    </div>
                  </div>
                  <button onClick={() => setShowDeleteModal(true)} className="px-4 py-3 rounded-lg border border-red-600 text-red-600 font-bold hover:bg-red-600 hover:text-white transition-colors">Xóa tài khoản</button>
                </div>
              </section>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

