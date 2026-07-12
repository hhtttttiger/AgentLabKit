// Auto-generated — do not edit manually
export const userManagement = {
  title: 'User management',
  description: 'Manage system users, roles and access permissions.',
  newUser: 'New user',
  createUserTitle: 'Create user',
  editUserTitle: 'Edit user',
  emptyTitle: 'No users',
  emptyDescription: 'Create the first user to get started.',
  deactivateTitle: 'Deactivate user',
  deactivateDescription: 'Are you sure you want to deactivate user "{{name}}"? They will not be able to log in.',
  columns: {
    username: 'Username',
    displayName: 'Display name',
    email: 'Email',
    role: 'Role',
    status: 'Status',
    lastLogin: 'Last login',
    actions: 'Actions'
  },
  roles: {
    admin: 'Admin',
    member: 'Member'
  },
  status: {
    active: 'Active',
    inactive: 'Inactive'
  },
  actions: {
    deactivate: 'Deactivate',
    activate: 'Activate'
  },
  form: {
    username: 'Username',
    password: 'Password',
    displayName: 'Display name',
    email: 'Email',
    role: 'Role',
    create: 'Create',
    creating: 'Creating...',
    save: 'Save',
    saving: 'Saving...'
  }
} as const;
