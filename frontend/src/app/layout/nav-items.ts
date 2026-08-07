export interface NavItem {
  label: string;
  route: string;
  icon: string;
  exact: boolean;
}

export const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', route: '/', icon: 'dashboard', exact: true },
  { label: 'Analyze', route: '/analyze', icon: 'search', exact: false },
  { label: 'Downloads', route: '/downloads', icon: 'download', exact: false },
  { label: 'History', route: '/history', icon: 'history', exact: false },
  { label: 'Settings', route: '/settings', icon: 'settings', exact: false },
];

export const HEALTH_NAV: NavItem = {
  label: 'Backend Status',
  route: '/status',
  icon: 'monitor_heart',
  exact: true,
};
