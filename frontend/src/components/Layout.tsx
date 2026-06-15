import { Link, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  BarChart3,
  Settings,
  LogOut,
  Bot,
  Search
} from 'lucide-react';
import { useAuthStore } from '../store/auth';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const logout = useAuthStore((state) => state.logout);

  const navigation = [
    { name: 'IA & Onboarding', href: '/dashboard', icon: Bot },
    { name: 'Ops Dashboard', href: '/ops', icon: BarChart3 },
    { name: 'Pesquisa SEO', href: '/seo', icon: Search },
    { name: 'Configurações', href: '#', icon: Settings },
  ];

  return (
    <div className="flex h-screen bg-base">
      {/* Sidebar */}
      <aside className="w-64 bg-card border-r border-line flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-line">
          <div className="flex items-center gap-2 text-brand">
            <LayoutDashboard className="h-6 w-6" />
            <span className="text-xl font-bold tracking-tight">Atlas Core</span>
          </div>
        </div>

        <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
          {navigation.map((item) => {
            const isActive = location.pathname.startsWith(item.href) && item.href !== '#';
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-brand/10 text-brand'
                    : 'text-muted hover:bg-elevated hover:text-ink'
                }`}
              >
                <item.icon
                  className={`flex-shrink-0 -ml-1 mr-3 h-5 w-5 ${
                    isActive ? 'text-brand' : 'text-subtle'
                  }`}
                />
                {item.name}
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-line">
          <button
            onClick={() => logout()}
            className="flex items-center w-full px-3 py-2.5 text-sm font-medium text-muted rounded-lg hover:bg-rose-500/10 hover:text-rose-400 transition-colors"
          >
            <LogOut className="flex-shrink-0 -ml-1 mr-3 h-5 w-5 text-subtle group-hover:text-rose-400" />
            Sair
          </button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-7xl">
          {children}
        </div>
      </main>
    </div>
  );
}
