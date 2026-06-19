import { useEffect, useState } from 'react';
import { Mail, Plus, Shield, ShieldOff, UserCheck, X } from 'lucide-react';

import { api } from '../lib/api';

type User = {
  id: number;
  email: string;
  full_name: string | null;
  role: string;
  department: string | null;
  is_active: boolean;
  created_at: string | null;
};

type Invitation = {
  id: number;
  email: string;
  role: string;
  department: string | null;
  expires_at: string;
  created_at: string;
};

const ROLES = [
  { value: 'admin', label: 'Admin', color: 'bg-violet-100 text-violet-800' },
  { value: 'operator', label: 'Operador', color: 'bg-sky-100 text-sky-800' },
  { value: 'reviewer', label: 'Visualizador', color: 'bg-slate-100 text-slate-700' },
];

const DEPARTMENTS = ['Comercial', 'Pós Venda', 'BI', 'Ops', 'Tecnologia', 'Gestão', 'Marketing'];

function RoleBadge({ role }: { role: string }) {
  const r = ROLES.find((r) => r.value === role) ?? ROLES[1];
  return (
    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${r.color}`}>
      {r.label}
    </span>
  );
}

export function AdminUsers() {
  const [users, setUsers] = useState<User[]>([]);
  const [invites, setInvites] = useState<Invitation[]>([]);
  const [loading, setLoading] = useState(true);

  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteEmail, setInviteEmail] = useState('');
  const [inviteRole, setInviteRole] = useState('operator');
  const [inviteDept, setInviteDept] = useState('');
  const [inviting, setInviting] = useState(false);
  const [inviteError, setInviteError] = useState('');
  const [inviteSuccess, setInviteSuccess] = useState('');

  const [editUser, setEditUser] = useState<User | null>(null);
  const [editRole, setEditRole] = useState('');
  const [editDept, setEditDept] = useState('');
  const [editName, setEditName] = useState('');
  const [saving, setSaving] = useState(false);

  const load = async () => {
    try {
      const [uRes, iRes] = await Promise.all([
        api.get<User[]>('/admin/users'),
        api.get<Invitation[]>('/admin/invitations'),
      ]);
      setUsers(uRes.data);
      setInvites(iRes.data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const sendInvite = async () => {
    setInviting(true);
    setInviteError('');
    setInviteSuccess('');
    try {
      await api.post('/admin/invitations', {
        email: inviteEmail,
        role: inviteRole,
        department: inviteDept || null,
      });
      setInviteSuccess(`Convite enviado para ${inviteEmail}!`);
      setInviteEmail('');
      setInviteRole('operator');
      setInviteDept('');
      void load();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: { message?: string } } } })
        ?.response?.data?.detail?.message;
      setInviteError(msg || 'Erro ao enviar convite.');
    } finally {
      setInviting(false);
    }
  };

  const cancelInvite = async (id: number) => {
    await api.delete(`/admin/invitations/${id}`);
    void load();
  };

  const toggleActive = async (user: User) => {
    await api.patch(`/admin/users/${user.id}`, { is_active: !user.is_active });
    void load();
  };

  const openEdit = (user: User) => {
    setEditUser(user);
    setEditRole(user.role);
    setEditDept(user.department ?? '');
    setEditName(user.full_name ?? '');
  };

  const saveEdit = async () => {
    if (!editUser) return;
    setSaving(true);
    try {
      await api.patch(`/admin/users/${editUser.id}`, {
        role: editRole,
        department: editDept || null,
        full_name: editName || null,
      });
      setEditUser(null);
      void load();
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <div className="py-8 text-center text-muted text-sm">Carregando...</div>;

  return (
    <div className="py-8 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-brand mb-1">Administração</p>
          <h1 className="text-2xl font-bold tracking-tight text-ink">Usuários</h1>
          <p className="mt-1 text-sm text-muted">Gerencie quem tem acesso ao Atlas.</p>
        </div>
        <button
          onClick={() => { setShowInviteModal(true); setInviteError(''); setInviteSuccess(''); }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium bg-brand text-onbrand hover:bg-brand-soft transition-colors"
        >
          <Plus className="w-4 h-4" />
          Convidar usuário
        </button>
      </div>

      {/* Users table */}
      <div className="bg-card rounded-xl border border-line shadow-sm overflow-hidden">
        <div className="px-6 py-4 border-b border-line">
          <h2 className="text-base font-semibold text-ink">Usuários ativos ({users.filter((u) => u.is_active).length})</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-elevated text-xs uppercase tracking-wide text-subtle">
              <tr>
                <th className="px-6 py-3 font-semibold">Nome</th>
                <th className="px-6 py-3 font-semibold">Email</th>
                <th className="px-6 py-3 font-semibold">Departamento</th>
                <th className="px-6 py-3 font-semibold">Role</th>
                <th className="px-6 py-3 font-semibold">Status</th>
                <th className="px-6 py-3 font-semibold">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {users.map((u) => (
                <tr key={u.id} className={`hover:bg-elevated/50 transition-colors ${!u.is_active ? 'opacity-50' : ''}`}>
                  <td className="px-6 py-3 font-medium text-ink">
                    {u.full_name || <span className="text-muted italic">Sem nome</span>}
                  </td>
                  <td className="px-6 py-3 text-muted">{u.email}</td>
                  <td className="px-6 py-3 text-muted">{u.department || '—'}</td>
                  <td className="px-6 py-3"><RoleBadge role={u.role} /></td>
                  <td className="px-6 py-3">
                    <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-semibold ${u.is_active ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-700'}`}>
                      {u.is_active ? 'Ativo' : 'Inativo'}
                    </span>
                  </td>
                  <td className="px-6 py-3">
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => openEdit(u)}
                        className="p-1.5 rounded hover:bg-elevated text-muted hover:text-ink transition-colors"
                        title="Editar"
                      >
                        <UserCheck className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => toggleActive(u)}
                        className={`p-1.5 rounded transition-colors ${u.is_active ? 'hover:bg-rose-50 text-muted hover:text-rose-600' : 'hover:bg-emerald-50 text-muted hover:text-emerald-600'}`}
                        title={u.is_active ? 'Desativar' : 'Reativar'}
                      >
                        {u.is_active ? <ShieldOff className="w-4 h-4" /> : <Shield className="w-4 h-4" />}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pending invites */}
      {invites.length > 0 && (
        <div className="bg-card rounded-xl border border-line shadow-sm overflow-hidden">
          <div className="px-6 py-4 border-b border-line">
            <h2 className="text-base font-semibold text-ink">Convites pendentes ({invites.length})</h2>
          </div>
          <div className="divide-y divide-line">
            {invites.map((inv) => (
              <div key={inv.id} className="px-6 py-3 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Mail className="w-4 h-4 text-muted flex-shrink-0" />
                  <div>
                    <p className="text-sm font-medium text-ink">{inv.email}</p>
                    <p className="text-xs text-muted">
                      {inv.department && `${inv.department} · `}
                      <RoleBadge role={inv.role} />
                      {' · expira '}
                      {new Date(inv.expires_at).toLocaleDateString('pt-BR')}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => cancelInvite(inv.id)}
                  className="p-1.5 rounded hover:bg-rose-50 text-muted hover:text-rose-600 transition-colors"
                  title="Cancelar convite"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Invite modal */}
      {showInviteModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-card rounded-xl border border-line shadow-xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-semibold text-ink">Convidar usuário</h3>
              <button onClick={() => setShowInviteModal(false)} className="text-muted hover:text-ink">
                <X className="w-5 h-5" />
              </button>
            </div>

            {inviteSuccess ? (
              <div className="text-center space-y-3 py-4">
                <p className="text-emerald-600 font-medium">{inviteSuccess}</p>
                <button
                  onClick={() => { setShowInviteModal(false); setInviteSuccess(''); }}
                  className="text-sm text-brand hover:underline"
                >
                  Fechar
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {inviteError && (
                  <div className="p-3 bg-rose-50 text-rose-700 rounded text-sm">{inviteError}</div>
                )}
                <div>
                  <label className="block text-sm font-medium text-muted mb-1">Email</label>
                  <input
                    type="email"
                    value={inviteEmail}
                    onChange={(e) => setInviteEmail(e.target.value)}
                    placeholder="fulano@healz.com.br"
                    className="block w-full px-3 py-2 border border-line rounded-lg text-sm text-ink bg-base focus:outline-none focus:ring-2 focus:ring-brand"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-muted mb-1">Role</label>
                  <select
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value)}
                    className="block w-full px-3 py-2 border border-line rounded-lg text-sm text-ink bg-base focus:outline-none focus:ring-2 focus:ring-brand"
                  >
                    {ROLES.map((r) => (
                      <option key={r.value} value={r.value}>{r.label}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-muted mb-1">Departamento</label>
                  <select
                    value={inviteDept}
                    onChange={(e) => setInviteDept(e.target.value)}
                    className="block w-full px-3 py-2 border border-line rounded-lg text-sm text-ink bg-base focus:outline-none focus:ring-2 focus:ring-brand"
                  >
                    <option value="">— Selecionar —</option>
                    {DEPARTMENTS.map((d) => (
                      <option key={d} value={d}>{d}</option>
                    ))}
                  </select>
                </div>
                <div className="flex gap-2 pt-2">
                  <button
                    onClick={() => setShowInviteModal(false)}
                    className="flex-1 px-4 py-2 rounded-lg text-sm font-medium border border-line text-muted hover:bg-elevated transition-colors"
                  >
                    Cancelar
                  </button>
                  <button
                    onClick={sendInvite}
                    disabled={inviting || !inviteEmail}
                    className="flex-1 px-4 py-2 rounded-lg text-sm font-medium bg-brand text-onbrand hover:bg-brand-soft disabled:opacity-60 disabled:cursor-not-allowed transition-colors"
                  >
                    {inviting ? 'Enviando...' : 'Enviar convite'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Edit user modal */}
      {editUser && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-card rounded-xl border border-line shadow-xl w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-base font-semibold text-ink">Editar usuário</h3>
              <button onClick={() => setEditUser(null)} className="text-muted hover:text-ink">
                <X className="w-5 h-5" />
              </button>
            </div>
            <p className="text-sm text-muted mb-4">{editUser.email}</p>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-muted mb-1">Nome completo</label>
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="block w-full px-3 py-2 border border-line rounded-lg text-sm text-ink bg-base focus:outline-none focus:ring-2 focus:ring-brand"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-muted mb-1">Role</label>
                <select
                  value={editRole}
                  onChange={(e) => setEditRole(e.target.value)}
                  className="block w-full px-3 py-2 border border-line rounded-lg text-sm text-ink bg-base focus:outline-none focus:ring-2 focus:ring-brand"
                >
                  {ROLES.map((r) => (
                    <option key={r.value} value={r.value}>{r.label}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-muted mb-1">Departamento</label>
                <select
                  value={editDept}
                  onChange={(e) => setEditDept(e.target.value)}
                  className="block w-full px-3 py-2 border border-line rounded-lg text-sm text-ink bg-base focus:outline-none focus:ring-2 focus:ring-brand"
                >
                  <option value="">— Selecionar —</option>
                  {DEPARTMENTS.map((d) => (
                    <option key={d} value={d}>{d}</option>
                  ))}
                </select>
              </div>
              <div className="flex gap-2 pt-2">
                <button
                  onClick={() => setEditUser(null)}
                  className="flex-1 px-4 py-2 rounded-lg text-sm font-medium border border-line text-muted hover:bg-elevated transition-colors"
                >
                  Cancelar
                </button>
                <button
                  onClick={saveEdit}
                  disabled={saving}
                  className="flex-1 px-4 py-2 rounded-lg text-sm font-medium bg-brand text-onbrand hover:bg-brand-soft disabled:opacity-60 transition-colors"
                >
                  {saving ? 'Salvando...' : 'Salvar'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
