import { useState } from 'react';
import { useAuthStore } from '../../store/authStore';
import { useAlerts } from '../../hooks/useApi';
import { useAppStore } from '../../store/appStore';
import { useAgentStore } from '../../store/agentStore';
import LGADetailPanel from '../LGADetail/LGADetailPanel';
import LGASearchBar from '../Search/LGASearchBar';
import AgentSidebar from '../Agent/AgentSidebar';
import SystemConsole from '../Agent/SystemConsole';
import type { TabId } from '../../App';

interface MainLayoutProps {
  activeTab: TabId;
  onTabChange: (tab: TabId) => void;
  children: React.ReactNode;
}

interface NavItem {
  id: TabId;
  label: string;
  icon: string;
  badge?: number;
}

export default function MainLayout({ activeTab, onTabChange, children }: MainLayoutProps) {
  const { user, logout } = useAuthStore();
  const { data: alerts } = useAlerts();
  const { selectedLGAId } = useAppStore();
  const { sidebarOpen, setSidebarOpen, consoleOpen, hasNewUiNotification, setHasNewUiNotification } = useAgentStore();

  // Mobile menu drawer state
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const criticalAlerts = alerts?.filter((a) => a.severity === 'critical').length || 0;

  const navItems: NavItem[] = [
    { id: 'dashboard', label: 'Dashboard', icon: 'dashboard' },
    { id: 'facilities', label: 'Facilities (FMOH)', icon: 'local_hospital' },
    { id: 'map', label: 'Map View', icon: 'map' },
    { id: 'reports', label: 'Reports', icon: 'description' },
    { id: 'correlation', label: 'Analytics', icon: 'insights' },
    { id: 'alerts', label: 'Alerts', icon: 'notifications_active', badge: criticalAlerts > 0 ? criticalAlerts : undefined },
    { id: 'satellite', label: 'Satellite', icon: 'satellite_alt' },
    { id: 'agent-ui', label: 'Agent Explorer', icon: 'extension', badge: hasNewUiNotification ? 1 : undefined },
    { id: 'settings', label: 'Settings', icon: 'settings' },
  ];

  const handleItemClick = (id: TabId) => {
    if (id === 'agent-ui') {
      setHasNewUiNotification(false);
    }
    onTabChange(id);
    setMobileMenuOpen(false); // Close mobile drawer on selection
  };

  return (
    <div className="flex h-screen w-full bg-[#f6f7f8] font-display overflow-hidden text-gray-900">
      {/* ── Mobile Menu Backdrop Overlay ── */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 md:hidden backdrop-blur-sm transition-opacity"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* ── Left Navigation Sidebar (Desktop: fixed w-64, Mobile: slide-over drawer) ── */}
      <aside
        className={`fixed md:relative inset-y-0 left-0 z-50 md:z-20 w-64 flex flex-col border-r border-[#e6e8eb] bg-white transition-transform duration-300 ease-in-out ${
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        <div className="flex h-full flex-col justify-between p-4 overflow-y-auto">
          <div className="flex flex-col gap-6">
            {/* Mobile Header Close Row */}
            <div className="flex items-center justify-between md:hidden pb-2 border-b border-gray-100">
              <span className="text-xs font-bold uppercase tracking-wider text-gray-400">Navigation Menu</span>
              <button
                onClick={() => setMobileMenuOpen(false)}
                className="p-1 rounded-lg text-gray-500 hover:bg-gray-100"
              >
                <span className="material-symbols-outlined">close</span>
              </button>
            </div>

            {/* User Profile */}
            <div className="flex items-center gap-3 px-2">
              <div className="bg-primary text-white rounded-full size-10 flex items-center justify-center font-bold text-lg ring-2 ring-primary/20 shrink-0">
                {user?.name?.charAt(0).toUpperCase() || 'U'}
              </div>
              <div className="flex flex-col min-w-0">
                <h1 className="text-base font-bold leading-tight text-[#111518] truncate">{user?.name || 'User'}</h1>
                <p className="text-[#637588] text-xs font-medium truncate">{user?.role?.replace('_', ' ') || 'Health Officer'}</p>
              </div>
            </div>

            {/* Navigation Links */}
            <nav className="flex flex-col gap-1">
              {navItems.map((item) => (
                <button
                  key={item.id}
                  onClick={() => handleItemClick(item.id)}
                  className={`flex items-center justify-between px-3 py-2.5 rounded-lg transition-colors w-full text-left ${
                    activeTab === item.id
                      ? 'bg-primary/10 text-primary font-semibold'
                      : 'text-[#637588] hover:bg-[#f0f2f5] font-medium'
                  }`}
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span className={`material-symbols-outlined shrink-0 ${activeTab === item.id ? 'filled' : ''}`} style={{ fontSize: '22px' }}>
                      {item.icon}
                    </span>
                    <span className="text-sm truncate">{item.label}</span>
                  </div>
                  {item.badge && (
                    <span className="bg-alert-orange text-white text-[10px] font-bold px-1.5 py-0.5 rounded-full shrink-0">
                      {item.badge}
                    </span>
                  )}
                </button>
              ))}
            </nav>
          </div>

          {/* Bottom Links */}
          <div className="flex flex-col gap-2 border-t border-[#e6e8eb] pt-4 mt-4">
            {/* AI Copilot Toggle */}
            <button
              onClick={() => {
                setSidebarOpen(!sidebarOpen);
                setMobileMenuOpen(false);
              }}
              className={`flex items-center gap-3 px-3 py-2 rounded-lg transition-colors w-full text-left ${
                sidebarOpen ? 'bg-primary/10 text-primary' : 'text-[#637588] hover:bg-[#f0f2f5]'
              }`}
            >
              <span className={`material-symbols-outlined ${sidebarOpen ? 'filled' : ''}`} style={{ fontSize: '22px' }}>smart_toy</span>
              <span className="text-sm font-medium">AI Copilot</span>
              {sidebarOpen && <span className="ml-auto size-2 rounded-full bg-emerald-400 animate-pulse" />}
            </button>

            <button
              onClick={logout}
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-[#637588] hover:bg-[#f0f2f5] transition-colors w-full text-left"
            >
              <span className="material-symbols-outlined" style={{ fontSize: '22px' }}>logout</span>
              <span className="text-sm font-medium">Sign Out</span>
            </button>
          </div>
        </div>
      </aside>

      {/* ── Center: Header + Main Content ── */}
      <main className="flex flex-1 flex-col overflow-hidden relative min-w-0">
        {/* Top Header */}
        <header className="flex h-16 items-center justify-between border-b border-[#e6e8eb] bg-white px-3 sm:px-6 flex-shrink-0 z-10">
          <div className="flex items-center gap-2 sm:gap-3 flex-shrink-0">
            {/* Hamburger Button for Mobile */}
            <button
              onClick={() => setMobileMenuOpen(true)}
              className="md:hidden p-2 rounded-lg text-gray-600 hover:bg-gray-100 transition-colors"
              aria-label="Open navigation menu"
            >
              <span className="material-symbols-outlined" style={{ fontSize: '24px' }}>menu</span>
            </button>

            <div className="size-8 text-primary flex items-center justify-center bg-primary/20 rounded-lg flex-shrink-0">
              <span className="material-symbols-outlined filled" style={{ fontSize: '20px' }}>health_and_safety</span>
            </div>
            <h2 className="text-sm sm:text-lg font-bold tracking-tight text-[#111518] truncate">
              Cholera Surveillance
            </h2>
            <span className="text-xs text-[#637588] hidden lg:block flex-shrink-0">• Federal Republic of Nigeria (774 LGAs)</span>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            {/* Search (Desktop) */}
            <div className="hidden md:block w-56 lg:w-72">
              <LGASearchBar placeholder="Search LGA..." />
            </div>

            {/* Console toggle */}
            <button
              onClick={() => useAgentStore.getState().setConsoleOpen(!consoleOpen)}
              className={`flex items-center justify-center size-8 sm:size-9 rounded-lg transition-colors relative ${
                consoleOpen ? 'bg-[#0f172a] text-emerald-400' : 'hover:bg-[#f0f2f5] text-[#637588]'
              }`}
              title={consoleOpen ? 'Hide console' : 'Show console'}
            >
              <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>terminal</span>
            </button>

            {/* Notifications */}
            <button className="flex items-center justify-center size-8 sm:size-9 rounded-lg hover:bg-[#f0f2f5] text-[#637588] transition-colors relative">
              <span className="material-symbols-outlined" style={{ fontSize: '20px' }}>notifications</span>
              {criticalAlerts > 0 && (
                <span className="absolute top-1 right-1 size-2 bg-alert-orange rounded-full border-2 border-white" />
              )}
            </button>
          </div>
        </header>

        {/* Scrollable Main Content */}
        <div className="flex-1 overflow-y-auto p-3 sm:p-6 scroll-smooth custom-scrollbar">
          <div className="max-w-[1600px] mx-auto">{children}</div>
        </div>

        {/* System Console */}
        <SystemConsole />
      </main>

      {/* ── Right: Contextual LGA Detail Panel ── */}
      {selectedLGAId && (
        <aside className="fixed inset-y-0 right-0 z-40 md:relative w-full sm:w-96 flex-shrink-0 overflow-hidden border-l border-[#e6e8eb] bg-white shadow-2xl md:shadow-none">
          <LGADetailPanel />
        </aside>
      )}

      {/* ── Right: AI Copilot Sidebar ── */}
      <AgentSidebar />
    </div>
  );
}
