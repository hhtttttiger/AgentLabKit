// Auto-generated — do not edit manually
export const userManagement = {
      title: '用户管理',
      description: '管理系统用户、角色和访问权限。',
      newUser: '新建用户',
      createUserTitle: '创建用户',
      editUserTitle: '编辑用户',
      emptyTitle: '暂无用户',
      emptyDescription: '创建第一个用户开始使用。',
      deactivateTitle: '停用用户',
      deactivateDescription: '确认停用用户「{{name}}」吗？停用后该用户将无法登录。',
      columns: {
        username: '用户名',
        displayName: '显示名称',
        email: '邮箱',
        role: '角色',
        status: '状态',
        lastLogin: '最后登录',
        actions: '操作'
      },
      roles: {
        admin: '管理员',
        member: '普通用户'
      },
      status: {
        active: '正常',
        inactive: '已停用'
      },
      actions: {
        deactivate: '停用',
        activate: '启用'
      },
      form: {
        username: '用户名',
        password: '密码',
        displayName: '显示名称',
        email: '邮箱',
        role: '角色',
        create: '创建',
        creating: '创建中...',
        save: '保存',
        saving: '保存中...'
      }
    } as const;
