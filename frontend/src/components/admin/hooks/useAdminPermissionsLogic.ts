import { type FormEvent, useMemo, useState } from 'react';
import { apiDb } from '../../../services/apiDb';

type UseAdminPermissionsLogicParams = {
  customers: any[];
  canManageCustomerAccess: boolean;
  canManageUsers: boolean;
  reloadCurrentTab: () => Promise<void>;
};

const emptyStaffForm = {
  email: '',
  password: '',
  fullName: '',
  phone: '',
  status: 'ACTIVE',
  permissionCodes: [] as string[],
};

export function useAdminPermissionsLogic({
  customers,
  canManageCustomerAccess,
  canManageUsers,
  reloadCurrentTab,
}: UseAdminPermissionsLogicParams) {
  const [permissions, setPermissions] = useState<any[]>([]);
  const [roles, setRoles] = useState<any[]>([]);
  const [rolePermissionMap, setRolePermissionMap] = useState<Record<string, string[]>>({});
  const [staffForm, setStaffForm] = useState(emptyStaffForm);
  const [editingStaffAccessId, setEditingStaffAccessId] = useState<string | null>(null);
  const [rolePermissionEditing, setRolePermissionEditing] = useState(false);
  const [staffPermissionEditor, setStaffPermissionEditor] = useState<any | null>(null);
  const [staffPermissionDraft, setStaffPermissionDraft] = useState<string[]>([]);

  const staffUsers = useMemo(() => (
    customers
      .filter((item) => String(item.role || '').toUpperCase() === 'STAFF_ADMIN')
      .sort((a, b) => String(a.role || '').localeCompare(String(b.role || '')))
  ), [customers]);

  const staffBasePermissionCodes = useMemo(() => {
    const staffRole = roles.find((role) => role.code === 'STAFF_ADMIN');
    return staffRole ? (rolePermissionMap[staffRole.id] || []) : [];
  }, [rolePermissionMap, roles]);

  const permissionsByModule = useMemo(() => permissions.reduce<Record<string, any[]>>((groups, permission) => {
    const moduleName = permission.module || 'Khac';
    groups[moduleName] = [...(groups[moduleName] || []), permission];
    return groups;
  }, {}), [permissions]);

  async function updateUserAccess(customer: any, patch: { role?: string; status?: string }) {
    if (!canManageUsers) return;
    if (customer.role === 'SUPER_ADMIN' || patch.role === 'SUPER_ADMIN') return;
    await apiDb.adminUpdateUserRole(customer.id, {
      role: patch.role || customer.role || 'CUSTOMER',
      status: patch.status || customer.status || 'ACTIVE',
      permissionCodes: patch.role === 'STAFF_ADMIN' || (!patch.role && customer.role === 'STAFF_ADMIN') ? (customer.extraPermissionCodes || []) : [],
    });
    setEditingStaffAccessId(null);
    await reloadCurrentTab();
  }

  async function createStaffAccount(event: FormEvent) {
    event.preventDefault();
    if (!canManageCustomerAccess || !staffForm.email.trim() || !staffForm.password || !staffForm.fullName.trim()) return;
    await apiDb.adminCreateStaff({
      email: staffForm.email.trim(),
      password: staffForm.password,
      fullName: staffForm.fullName.trim(),
      phone: staffForm.phone.trim() || undefined,
      status: staffForm.status,
      permissionCodes: [],
    });
    setStaffForm(emptyStaffForm);
    await reloadCurrentTab();
  }

  async function openStaffPermissionEditor(staff: any) {
    if (!canManageCustomerAccess) return;
    const detail = await apiDb.adminGetUserPermissions(staff.id).catch(() => ({ permissionCodes: staff.extraPermissionCodes || [] }));
    setStaffPermissionEditor(staff);
    setStaffPermissionDraft(detail.permissionCodes || []);
  }

  async function saveStaffPermissions() {
    if (!staffPermissionEditor?.id || !canManageCustomerAccess) return;
    await apiDb.adminUpdateUserPermissions(staffPermissionEditor.id, staffPermissionDraft);
    setStaffPermissionEditor(null);
    setStaffPermissionDraft([]);
    await reloadCurrentTab();
  }

  async function toggleRolePermission(roleId: string, code: string, checked: boolean) {
    const current = rolePermissionMap[roleId] || [];
    const next = checked ? [...new Set([...current, code])] : current.filter((item) => item !== code);
    setRolePermissionMap((prev) => ({ ...prev, [roleId]: next }));
    await apiDb.adminUpdateRolePermissions(roleId, next);
    await reloadCurrentTab();
  }

  return {
    permissions,
    setPermissions,
    roles,
    setRoles,
    rolePermissionMap,
    setRolePermissionMap,
    staffForm,
    setStaffForm,
    editingStaffAccessId,
    setEditingStaffAccessId,
    rolePermissionEditing,
    setRolePermissionEditing,
    staffPermissionEditor,
    setStaffPermissionEditor,
    staffPermissionDraft,
    setStaffPermissionDraft,
    staffUsers,
    staffBasePermissionCodes,
    permissionsByModule,
    updateUserAccess,
    createStaffAccount,
    openStaffPermissionEditor,
    saveStaffPermissions,
    toggleRolePermission,
  };
}
