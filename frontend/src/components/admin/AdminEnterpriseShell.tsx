import React from 'react';
import {
  BellOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  ReloadOutlined,
  SearchOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { Avatar, Badge, Breadcrumb, Button, Dropdown, Input, Layout, Menu, Space, Tooltip, Typography } from 'antd';

const { Header, Sider, Content } = Layout;
const { Text, Title } = Typography;

export type AdminShellTab = {
  id: string;
  label: string;
  group?: string;
  icon: React.ReactNode;
};

type AdminEnterpriseShellProps = {
  tabs: AdminShellTab[];
  activeTab: string;
  onTabChange: (tabId: string) => void;
  collapsed: boolean;
  onToggleCollapsed: () => void;
  title: string;
  description: string;
  sectionLabel: string;
  sectionIcon: React.ReactNode;
  query: string;
  onQueryChange: (value: string) => void;
  searchPlaceholder: string;
  onRefresh: () => void;
  onSignOut: () => Promise<void> | void;
  busy?: boolean;
  children: React.ReactNode;
};

export function AdminEnterpriseShell({
  tabs,
  activeTab,
  onTabChange,
  collapsed,
  onToggleCollapsed,
  title,
  description,
  sectionLabel,
  sectionIcon,
  query,
  onQueryChange,
  searchPlaceholder,
  onRefresh,
  onSignOut,
  busy = false,
  children,
}: AdminEnterpriseShellProps) {
  // Keep the shell copy centralized so any future admin page reusing this component inherits the same UX language.
  const groupedTabs = tabs.reduce<Record<string, AdminShellTab[]>>((groups, tab) => {
    const groupName = tab.group || 'Khac';
    groups[groupName] = [...(groups[groupName] || []), tab];
    return groups;
  }, {});
  const menuItems = collapsed
    ? tabs.map((tab) => ({ key: tab.id, icon: tab.icon, label: tab.label }))
    : Object.entries(groupedTabs).map(([label, children]) => ({
      key: label,
      label,
      type: 'group' as const,
      children: children.map((tab) => ({ key: tab.id, icon: tab.icon, label: tab.label })),
    }));

  return (
    <Layout className="min-h-screen bg-[#f5f7fb]">
      <Sider
        collapsible
        collapsed={collapsed}
        trigger={null}
        width={272}
        collapsedWidth={84}
        breakpoint="lg"
        onBreakpoint={(broken) => {
          if (broken && !collapsed) onToggleCollapsed();
        }}
        className="border-r border-slate-200 !bg-white"
      >
        <div className="flex h-full flex-col">
          <div className="border-b border-slate-200 px-4 py-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[#d70018] text-sm font-black text-white">
                EM
              </div>
              {!collapsed && (
                <div className="min-w-0">
                  <Title level={5} className="!mb-0 truncate !text-slate-950">
                    ElectroMart Admin
                  </Title>
                  <Text className="block truncate text-xs !text-slate-500">Bảng điều hành quản trị</Text>
                </div>
              )}
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-3 py-4">
            <Menu
              mode="inline"
              selectedKeys={[activeTab]}
              onClick={({ key }) => onTabChange(String(key))}
              items={menuItems}
              inlineCollapsed={collapsed}
              className="admin-pro-menu border-0 bg-transparent"
            />
          </div>

          <div className="border-t border-slate-200 px-4 py-4">
            {!collapsed ? (
              <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-3">
                <div className="text-xs font-bold uppercase text-slate-500">Hệ thống</div>
                <div className="mt-1 text-sm font-semibold text-slate-900">Chế độ enterprise</div>
                <div className="mt-1 text-xs leading-5 text-slate-500">
                  Điều hướng theo vai trò, nhật ký thao tác và các luồng vận hành quan trọng.
                </div>
              </div>
            ) : (
              <div className="flex justify-center">
                <Badge status="processing" />
              </div>
            )}
          </div>
        </div>
      </Sider>

      <Layout>
        <Header className="h-auto border-b border-slate-200 !bg-white px-4 py-3 sm:px-6">
          <div className="flex flex-col gap-3 xl:flex-row xl:items-center xl:justify-between">
            <div className="flex items-center gap-3">
              <Button
                type="text"
                icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
                onClick={onToggleCollapsed}
              />
              <div className="min-w-0">
                <Breadcrumb
                  items={[
                    { title: 'Admin' },
                    { title: 'Dashboard' },
                    { title: title },
                  ]}
                  className="mb-0"
                />
              </div>
            </div>

            <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
              <Input
                allowClear
                size="large"
                prefix={<SearchOutlined className="text-slate-400" />}
                placeholder={searchPlaceholder}
                value={query}
                onChange={(event) => onQueryChange(event.target.value)}
                className="w-full sm:w-[340px]"
              />
              <Tooltip title="Làm mới dữ liệu">
                <Button size="large" icon={<ReloadOutlined spin={busy} />} onClick={onRefresh} />
              </Tooltip>
              <Badge dot>
                <Button size="large" icon={<BellOutlined />} />
              </Badge>
              <Dropdown
                menu={{
                  items: [
                    {
                      key: 'settings',
                      icon: <SettingOutlined />,
                      label: 'Đổi mật khẩu',
                    },
                    {
                      key: 'logout',
                      icon: <LogoutOutlined />,
                      label: 'Đăng xuất',
                      danger: true,
                      onClick: () => void onSignOut(),
                    },
                  ],
                }}
                trigger={['click']}
              >
                <Button size="large">
                  <Space>
                    <Avatar size="small" style={{ backgroundColor: '#1677ff' }}>
                      A
                    </Avatar>
                    Admin
                  </Space>
                </Button>
              </Dropdown>
            </div>
          </div>
        </Header>

        <Content className="p-4 sm:p-6">
          <div className="mb-5 rounded-lg border border-slate-200 bg-white px-4 py-4 shadow-sm sm:px-5">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div className="min-w-0">
                <Space size={8} align="center" wrap>
                  <span className="text-[#d70018]">{sectionIcon}</span>
                  <Text className="text-xs font-bold uppercase !text-slate-500">{sectionLabel}</Text>
                </Space>
                <Title level={3} className="!mb-1 !mt-2 !text-slate-950">
                  {title}
                </Title>
                <Text className="block max-w-4xl text-sm leading-6 !text-slate-500">{description}</Text>
              </div>
            </div>
          </div>
          {busy && (
            <div className="mb-4 rounded-lg border border-sky-100 bg-sky-50 px-4 py-3 text-sm font-semibold text-sky-700">
              Đang đồng bộ dữ liệu quản trị...
            </div>
          )}
          {children}
        </Content>
      </Layout>
    </Layout>
  );
}
