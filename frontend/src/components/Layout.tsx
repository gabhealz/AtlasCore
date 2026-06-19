import { Link, useLocation } from 'react-router-dom';
import { BarChart3, Bot, LogOut, Search, Users } from 'lucide-react';

import { useAuthStore } from '../store/auth';

interface LayoutProps {
  children: React.ReactNode;
}

const NAV = [
  { name: 'IA & Onboarding', href: '/dashboard', icon: Bot },
  { name: 'Ops Dashboard', href: '/ops', icon: BarChart3 },
  { name: 'Pesquisa SEO', href: '/seo', icon: Search },
];

function UserAvatar({ name, email }: { name: string | null; email: string | null }) {
  const initials = name
    ? name.split(' ').slice(0, 2).map((w) => w[0]).join('').toUpperCase()
    : (email ?? '?')[0].toUpperCase();

  return (
    <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg">
      <div className="w-8 h-8 rounded-full bg-brand/20 text-brand flex items-center justify-center text-xs font-bold flex-shrink-0">
        {initials}
      </div>
      <div className="min-w-0">
        <p className="text-sm font-medium text-ink truncate">{name ?? email ?? 'Usuário'}</p>
        {name && <p className="text-xs text-muted truncate">{email}</p>}
      </div>
    </div>
  );
}

export function Layout({ children }: LayoutProps) {
  const location = useLocation();
  const logout = useAuthStore((s) => s.logout);
  const role = useAuthStore((s) => s.role);
  const name = useAuthStore((s) => s.name);
  const email = useAuthStore((s) => s.email);

  return (
    <div className="flex h-screen bg-base">
      <aside className="w-64 bg-card border-r border-line flex flex-col">
        <div className="h-16 flex items-center gap-2.5 px-6 border-b border-line">
          <img src="/favicon-healz.png" alt="" className="h-7 w-7" />
          <span className="text-lg font-bold tracking-tight text-ink">healz</span>
          <span className="text-[10px] font-semibold uppercase tracking-[0.2em] text-subtle mt-1">Atlas</span>
        </div>

        <nav className="flex-1 px-4 py-6 space-y-1 overflow-y-auto">
          {NAV.map((item) => {
            const active = location.pathname.startsWith(item.href) && item.href !== '#';
            return (
              <Link
                key={item.name}
                to={item.href}
                className={`flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  active ? 'bg-brand/10 text-brand' : 'text-muted hover:bg-elevated hover:text-ink'
                }`}
              >
                <item.icon className={`flex-shrink-0 -ml-1 mr-3 h-5 w-5 ${active ? 'text-brand' : 'text-subtle'}`} />
                {item.name}
              </Link>
            );
          })}

          {role === 'admin' && (
            <Link
              to="/admin/users"
              className={`flex items-center px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                location.pathname.startsWith('/admin')
                  ? 'bg-brand/10 text-brand'
                  : 'text-muted hover:bg-elevated hover:text-ink'
              }`}
            >
              <Users className={`flex-shrink-0 -ml-1 mr-3 h-5 w-5 ${location.pathname.startsWith('/admin') ? 'text-brand' : 'text-subtle'}`} />
              Usuários
            </Link>
          )}
        </nav>

        <div className="border-t border-line">
          <UserAvatar name={name} email={email} />
          <div className="px-4 pb-4">
            <button
              onClick={() => logout()}
              className="flex items-center w-full px-3 py-2 text-sm font-medium text-muted rounded-lg hover:bg-rose-500/10 hover:text-rose-400 transition-colors"
            >
              <LogOut className="flex-shrink-0 -ml-1 mr-3 h-5 w-5 text-subtle" />
              Sair
            </button>
          </div>
        </div>
      </aside>

      <main className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-7xl">
          {children}
        </div>
      </main>
    </div>
  );
}
