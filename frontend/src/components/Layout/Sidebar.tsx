import { useState } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { useAuth } from '../../contexts/AuthContext';
import { LayoutDashboard, Users, Settings, LogOut, Menu, X, Zap } from 'lucide-react';

export function Sidebar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const navItems = [
    { to: '/', icon: LayoutDashboard, label: 'Dashboard' },
    { to: '/clientes', icon: Users, label: 'Clientes' },
    { to: '/configuracoes', icon: Settings, label: 'Configurações' },
  ];

  return (
    <aside
      className="sidebar"
      style={{
        width: collapsed ? '64px' : '240px',
        minHeight: '100vh',
        background: 'var(--color-bg-sidebar)',
        borderRight: '1px solid var(--color-border)',
        display: 'flex',
        flexDirection: 'column',
        transition: 'width var(--transition-base)',
        position: 'fixed',
        left: 0,
        top: 0,
        bottom: 0,
        zIndex: 50,
      }}
    >
      {/* Logo */}
      <div style={{
        padding: 'var(--spacing-lg)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: collapsed ? 'center' : 'space-between',
        borderBottom: '1px solid var(--color-border)',
        minHeight: '60px',
      }}>
        {!collapsed && (
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--spacing-sm)' }}>
            <div style={{
              width: 32,
              height: 32,
              borderRadius: 'var(--radius-md)',
              background: 'linear-gradient(135deg, var(--color-accent), var(--color-accent-hover))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <Zap size={18} color="white" />
            </div>
            <span style={{ fontWeight: 700, fontSize: 'var(--font-size-lg)', color: 'var(--color-text-primary)' }}>
              Atlas Core
            </span>
          </div>
        )}
        <button
          className="btn btn-ghost btn-icon"
          onClick={() => setCollapsed(!collapsed)}
          style={{ flexShrink: 0 }}
        >
          {collapsed ? <Menu size={18} /> : <X size={18} />}
        </button>
      </div>

      {/* Navigation */}
      <nav style={{ flex: 1, padding: 'var(--spacing-md)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {navItems.map(item => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.to === '/'}
            style={({ isActive }) => ({
              display: 'flex',
              alignItems: 'center',
              gap: 'var(--spacing-md)',
              padding: collapsed ? 'var(--spacing-sm)' : 'var(--spacing-sm) var(--spacing-md)',
              borderRadius: 'var(--radius-md)',
              color: isActive ? 'var(--color-accent)' : 'var(--color-text-secondary)',
              background: isActive ? 'var(--color-accent-light)' : 'transparent',
              fontSize: 'var(--font-size-base)',
              fontWeight: isActive ? 600 : 400,
              textDecoration: 'none',
              transition: 'all var(--transition-fast)',
              justifyContent: collapsed ? 'center' : 'flex-start',
            })}
          >
            <item.icon size={20} />
            {!collapsed && <span>{item.label}</span>}
          </NavLink>
        ))}
      </nav>

      {/* User section */}
      <div style={{
        padding: 'var(--spacing-md)',
        borderTop: '1px solid var(--color-border)',
      }}>
        {!collapsed && user && (
          <div style={{
            padding: 'var(--spacing-sm) var(--spacing-md)',
            marginBottom: 'var(--spacing-sm)',
          }}>
            <p style={{ fontSize: 'var(--font-size-sm)', fontWeight: 600, color: 'var(--color-text-primary)' }}>
              {user.full_name}
            </p>
            <p style={{ fontSize: 'var(--font-size-xs)', color: 'var(--color-text-muted)' }}>
              {user.email}
            </p>
          </div>
        )}
        <button
          className="btn btn-ghost"
          onClick={handleLogout}
          style={{
            width: '100%',
            justifyContent: collapsed ? 'center' : 'flex-start',
            gap: 'var(--spacing-sm)',
            color: 'var(--color-text-muted)',
            fontSize: 'var(--font-size-sm)',
          }}
        >
          <LogOut size={18} />
          {!collapsed && <span>Sair</span>}
        </button>
      </div>
    </aside>
  );
}
