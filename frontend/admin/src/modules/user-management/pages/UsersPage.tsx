import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Plus, Pencil, UserX, UserCheck } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '@/shared/ui/Button';
import { Badge } from '@/shared/ui/Badge';
import { DataTable, type TableColumn } from '@/shared/ui/DataTable';
import { EmptyState } from '@/shared/ui/EmptyState';
import { FormModal } from '@/shared/ui/FormModal';
import { ConfirmDialog } from '@/shared/ui/ConfirmDialog';
import { PageFrame } from '@/shared/ui/PageFrame';
import { ManagementListFrame } from '@/shared/ui/ManagementListFrame';
import { FilterToolbar } from '@/shared/ui/FilterToolbar';
import { FilterToolbarActions } from '@/shared/ui/FilterToolbarActions';
import { Pagination } from '@/shared/ui/Pagination';
import { TextField, SelectField } from '@/shared/ui/FormFields';
import { useToast } from '@/shared/ui/Toast';
import { getErrorMessage } from '@/shared/api/errors';
import {
  listUsers,
  createUser,
  updateUser,
  deleteUser,
} from '@/shared/auth/api';
import type {
  UserListItem,
  CreateUserRequest,
  UpdateUserRequest,
} from '@/shared/auth/types';

const queryKey = ['admin', 'users'];

function useUserMutations() {
  const queryClient = useQueryClient();
  const invalidate = () => queryClient.invalidateQueries({ queryKey });

  const create = useMutation({
    mutationFn: (data: CreateUserRequest) => createUser(data),
    onSuccess: invalidate,
  });

  const update = useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateUserRequest }) => updateUser(id, data),
    onSuccess: invalidate,
  });

  const deactivate = useMutation({
    mutationFn: (id: string) => deleteUser(id),
    onSuccess: invalidate,
  });

  return { create, update, deactivate };
}

function CreateUserForm({
  onSubmit,
  onCancel,
  submitting,
}: {
  onSubmit: (data: CreateUserRequest) => void;
  onCancel: () => void;
  submitting: boolean;
}) {
  const { t } = useTranslation();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('member');

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({ username, password, displayName: displayName || undefined, email: email || undefined, role });
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <TextField
        label={t('modules.userManagement.form.username')}
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        required
        autoFocus
      />
      <TextField
        label={t('modules.userManagement.form.password')}
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      <TextField
        label={t('modules.userManagement.form.displayName')}
        value={displayName}
        onChange={(e) => setDisplayName(e.target.value)}
      />
      <TextField
        label={t('modules.userManagement.form.email')}
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <SelectField
        label={t('modules.userManagement.form.role')}
        value={role}
        onChange={(e) => setRole(e.target.value)}
      >
        <option value="admin">{t('modules.userManagement.roles.admin')}</option>
        <option value="member">{t('modules.userManagement.roles.member')}</option>
      </SelectField>
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="ghost" type="button" onClick={onCancel}>{t('actions.cancel')}</Button>
        <Button type="submit" disabled={submitting}>
          {submitting ? t('modules.userManagement.form.creating') : t('modules.userManagement.form.create')}
        </Button>
      </div>
    </form>
  );
}

function EditUserForm({
  user,
  onSubmit,
  onCancel,
  submitting,
}: {
  user: UserListItem;
  onSubmit: (data: UpdateUserRequest) => void;
  onCancel: () => void;
  submitting: boolean;
}) {
  const { t } = useTranslation();
  const [displayName, setDisplayName] = useState(user.displayName ?? '');
  const [email, setEmail] = useState(user.email ?? '');
  const [role, setRole] = useState(user.role);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    onSubmit({
      displayName: displayName || undefined,
      email: email || undefined,
      role,
    });
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4">
      <TextField
        label={t('modules.userManagement.form.username')}
        value={user.username}
        disabled
      />
      <TextField
        label={t('modules.userManagement.form.displayName')}
        value={displayName}
        onChange={(e) => setDisplayName(e.target.value)}
      />
      <TextField
        label={t('modules.userManagement.form.email')}
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <SelectField
        label={t('modules.userManagement.form.role')}
        value={role}
        onChange={(e) => setRole(e.target.value)}
      >
        <option value="admin">{t('modules.userManagement.roles.admin')}</option>
        <option value="member">{t('modules.userManagement.roles.member')}</option>
      </SelectField>
      <div className="flex justify-end gap-2 pt-2">
        <Button variant="ghost" type="button" onClick={onCancel}>{t('actions.cancel')}</Button>
        <Button type="submit" disabled={submitting}>
          {submitting ? t('modules.userManagement.form.saving') : t('modules.userManagement.form.save')}
        </Button>
      </div>
    </form>
  );
}

export function UsersPage() {
  const { t } = useTranslation();
  const { toast } = useToast();
  const mutations = useUserMutations();

  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [createOpen, setCreateOpen] = useState(false);
  const [editingUser, setEditingUser] = useState<UserListItem | null>(null);
  const [deactivatingUser, setDeactivatingUser] = useState<UserListItem | null>(null);

  const listQuery = useQuery({
    queryKey: [...queryKey, page, pageSize],
    queryFn: () => listUsers({ page, pageSize }),
  });

  const items = listQuery.data?.items ?? [];
  const total = listQuery.data?.totalCount ?? 0;

  async function handleCreate(data: CreateUserRequest) {
    try {
      await mutations.create.mutateAsync(data);
      toast(t('toast.created'));
      setCreateOpen(false);
      setPage(1);
    } catch (err) {
      toast(getErrorMessage(err), 'error');
    }
  }

  async function handleUpdate(data: UpdateUserRequest) {
    if (!editingUser) return;
    try {
      await mutations.update.mutateAsync({ id: editingUser.id, data });
      toast(t('toast.updated'));
      setEditingUser(null);
    } catch (err) {
      toast(getErrorMessage(err), 'error');
    }
  }

  async function handleDeactivate() {
    if (!deactivatingUser) return;
    try {
      await mutations.deactivate.mutateAsync(deactivatingUser.id);
      toast(t('toast.deactivateDone'));
      setDeactivatingUser(null);
    } catch (err) {
      toast(getErrorMessage(err), 'error');
    }
  }

  async function handleToggleActive(user: UserListItem) {
    try {
      await mutations.update.mutateAsync({
        id: user.id,
        data: { isActive: !user.isActive },
      });
      toast(t('toast.updated'));
    } catch (err) {
      toast(getErrorMessage(err), 'error');
    }
  }

  const columns: TableColumn<UserListItem>[] = [
    {
      key: 'username',
      header: t('modules.userManagement.columns.username'),
      render: (row) => <span className="font-medium text-text-primary">{row.username}</span>,
    },
    {
      key: 'displayName',
      header: t('modules.userManagement.columns.displayName'),
      render: (row) => row.displayName ?? '—',
    },
    {
      key: 'email',
      header: t('modules.userManagement.columns.email'),
      render: (row) => row.email ?? '—',
    },
    {
      key: 'role',
      header: t('modules.userManagement.columns.role'),
      render: (row) => (
        <Badge tone={row.role === 'admin' ? 'info' : 'neutral'}>
          {t(`modules.userManagement.roles.${row.role}`)}
        </Badge>
      ),
    },
    {
      key: 'isActive',
      header: t('modules.userManagement.columns.status'),
      render: (row) => (
        <Badge tone={row.isActive ? 'success' : 'danger'}>
          {row.isActive ? t('modules.userManagement.status.active') : t('modules.userManagement.status.inactive')}
        </Badge>
      ),
    },
    {
      key: 'lastLoginAtUtc',
      header: t('modules.userManagement.columns.lastLogin'),
      render: (row) => row.lastLoginAtUtc ? new Date(row.lastLoginAtUtc).toLocaleString() : '—',
    },
    {
      key: 'actions',
      header: t('modules.userManagement.columns.actions'),
      render: (row) => (
        <div className="flex gap-1">
          <Button
            variant="ghost"
            title={t('actions.edit')}
            onClick={() => setEditingUser(row)}
          >
            <Pencil size={14} />
          </Button>
          <Button
            variant="ghost"
            title={row.isActive ? t('modules.userManagement.actions.deactivate') : t('modules.userManagement.actions.activate')}
            onClick={() => row.isActive ? setDeactivatingUser(row) : handleToggleActive(row)}
          >
            {row.isActive ? <UserX size={14} /> : <UserCheck size={14} />}
          </Button>
        </div>
      ),
    },
  ];

  return (
    <PageFrame
      title={t('modules.userManagement.title')}
      description={t('modules.userManagement.description')}
      actions={
        <Button onClick={() => setCreateOpen(true)}>
          <Plus size={16} />
          {t('modules.userManagement.newUser')}
        </Button>
      }
    >
      <ManagementListFrame
        refreshing={listQuery.isFetching}
        toolbar={
          <FilterToolbar
            compact
            actions={
              <FilterToolbarActions
                onRefresh={() => listQuery.refetch()}
                refreshing={listQuery.isFetching}
                onReset={() => { setPage(1); }}
              />
            }
          />
        }
        pagination={
          total > pageSize ? (
            <Pagination
              page={page}
              totalCount={total}
              pageSize={pageSize}
              onChange={setPage}
            />
          ) : undefined
        }
      >
        <DataTable
          columns={columns}
          rows={items}
          getRowKey={(row) => row.id}
          loading={listQuery.isLoading}
          emptyState={
            <EmptyState
              title={t('modules.userManagement.emptyTitle')}
              description={t('modules.userManagement.emptyDescription')}
            />
          }
        />
      </ManagementListFrame>

      {/* Create user modal */}
      <FormModal
        open={createOpen}
        title={t('modules.userManagement.createUserTitle')}
        onClose={() => setCreateOpen(false)}
      >
        <CreateUserForm
          onSubmit={handleCreate}
          onCancel={() => setCreateOpen(false)}
          submitting={mutations.create.isPending}
        />
      </FormModal>

      {/* Edit user modal */}
      <FormModal
        open={editingUser !== null}
        title={t('modules.userManagement.editUserTitle')}
        onClose={() => setEditingUser(null)}
      >
        {editingUser && (
          <EditUserForm
            user={editingUser}
            onSubmit={handleUpdate}
            onCancel={() => setEditingUser(null)}
            submitting={mutations.update.isPending}
          />
        )}
      </FormModal>

      {/* Deactivate confirmation */}
      <ConfirmDialog
        open={deactivatingUser !== null}
        title={t('modules.userManagement.deactivateTitle')}
        description={t('modules.userManagement.deactivateDescription', { name: deactivatingUser?.username })}
        confirmLabel={t('modules.userManagement.actions.deactivate')}
        onConfirm={handleDeactivate}
        onClose={() => setDeactivatingUser(null)}
      />
    </PageFrame>
  );
}
