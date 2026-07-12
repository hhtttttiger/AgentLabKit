// Auto-generated — do not edit manually
export const common = {
  userMenu: {
    ariaLabel: '用户菜单',
    account: '账户信息',
    language: 'Language',
    languageTitle: '选择语言',
    preferences: '界面偏好',
    preferencesTitle: '界面偏好',
    profile: '个人资料',
    changePassword: '修改密码',
    back: '返回',
    localeShort: {
      'zh-CN': '中文',
      'en-US': 'EN'
    },
    logout: '登出'
  },
  preferences: {
    theme: {
      dark: '深色模式',
      light: '浅色模式'
    },
    motion: {
      enable: '开启动画',
      disable: '关闭动画'
    },
    accent: '主题色',
    accentOptions: {
      blue: '蓝色（默认）',
      violet: '紫色',
      emerald: '绿色',
      rose: '玫瑰红',
      amber: '琥珀',
      orange: '小米橙'
    },
    zoom: '缩放比例',
    language: {
      label: '显示语言',
      options: {
        'zh-CN': '简体中文',
        'en-US': 'English'
      }
    },
    catalog: {
      scenes: {
        gateway: '网关',
        voice: '语音',
      },
      capabilities: {
        Text: '文本对话',
        Multimodal: '多模态',
        Embedding: '向量嵌入',
        SpeechBatch: '批量语音',
        SpeechStream: '流式语音',
        Realtime: '实时语音',
        Image: '图像生成',
        Tool: '工具调用',
      },
      bindingPresets: {
        custom: '自定义',
        gateway_text: { label: '对话问答', description: '通用文本对话、问答、总结与改写。' },
        gateway_multimodal: { label: '多模态对话', description: '支持图文混合输入的对话与理解。' },
        gateway_embedding: { label: '向量检索', description: '文本向量化，用于检索、相似度与 RAG。' },
        gateway_speech_batch: { label: '语音转写（批量）', description: '批量音频转文字，适合离线处理录音文件。' },
        gateway_speech_stream: { label: '语音转写（流式）', description: '实时流式音频转文字，边录边出结果。' },
        gateway_image: { label: '图像生成', description: '根据文本描述生成图片。' },
        gateway_realtime: { label: '实时多模态', description: '低延迟实时语音/视频对话。' },
        gateway_tool: { label: '工具调用', description: '模型可调用外部工具/函数（Agent 场景）。' },
        voice_text: { label: '语音助手文本', description: '语音助手后端使用的文本对话模型。' },
        voice_realtime: { label: '语音实时通道', description: '语音助手的实时语音对话通道。' },
      },
    },
  },
  login: {
    title: 'AI Admin',
    username: '用户名',
    usernamePlaceholder: '请输入用户名',
    password: '密码',
    passwordPlaceholder: '请输入密码',
    submit: '登录',
    submitting: '登录中…',
    errorFallback: '登录失败，请检查账号密码。',
    preferences: {
      ariaLabel: '登录偏好设置',
      trigger: '界面偏好',
      helper: '语言、主题色与主题模式',
      panelLabel: '登录偏好设置面板',
      openPanel: '打开登录偏好设置。当前：{{locale}}、{{accent}}、{{theme}}',
      closePanel: '关闭登录偏好设置。当前：{{locale}}、{{accent}}、{{theme}}',
      language: '语言',
      accent: '主题色',
      theme: '主题'
    }
  },
  themeToggle: {
    toLight: '切换到浅色模式',
    toDark: '切换到深色模式'
  },
  nav: {
    ariaLabel: '模块导航',
    brandTitle: 'AI Admin',
    brandSubtitle: 'Frontend Base',
    aiChat: 'AI 对话',
    agentManagement: 'Agent 管理',
    modelManagement: '模型管理',
    glossary: '术语库',
    knowledgeBase: '知识库',
    modelMonitoring: '模型监控',
    costAnalysis: '成本分析',
    observability: '可观测性',
    memory: '记忆管理',
    evaluation: '评估管理',
    userManagement: '用户管理',
    voiceLab: '语音延迟调试',
    collapse: '收起菜单',
    expand: '展开菜单',
    collapseShort: '收起',
    expandShort: '展开'
  },
  actions: {
    create: '创建',
    edit: '编辑',
    refresh: '刷新',
    reset: '重置',
    delete: '删除',
    cancel: '取消',
    backToList: '返回列表',
    addInstance: '添加实例',
    addBinding: '添加绑定'
  },
  pagination: {
    totalPrefix: '共 ',
    totalSuffix: ' 条',
    pageSizeOption: '{{count}} 条/页',
    previousPage: '上一页',
    nextPage: '下一页',
    jumpTo: '跳至',
    pageUnit: '页'
  },
  datePicker: {
    selectDate: '选择日期',
    previousMonth: '上个月',
    nextMonth: '下个月',
    clear: '清空'
  },
  states: {
    loading: '加载中',
    loadingFailed: '加载失败',
    empty: '暂无数据',
    unknown: '未知',
    processing: '处理中...',
    lastUpdated: '最后更新 {{value}}'
  },
  api: {
    requestFailed: '接口请求失败。',
    sessionExpired: '会话已过期，请重新登录。'
  },
  shared: {
    auth: {
      profile: {
        title: '个人资料',
        username: '用户名',
        displayName: '显示名称',
        email: '邮箱',
        save: '保存',
        saving: '保存中...'
      },
      changePassword: {
        title: '修改密码',
        currentPassword: '当前密码',
        newPassword: '新密码',
        confirmPassword: '确认新密码',
        save: '修改密码',
        saving: '修改中...',
        tooShort: '密码长度至少 8 位。',
        mismatch: '两次输入的密码不一致。'
      }
    }
  },
  toast: {
    created: '创建成功',
    updated: '更新成功',
    deleted: '删除成功',
    saved: '保存成功',
    operationSuccess: '操作成功',
    operationFailed: '操作失败',
    syncCompleted: '同步完成',
    syncFailed: '同步失败',
    importCompleted: '导入完成',
    importFailed: '导入失败',
    exportCompleted: '导出完成',
    uploadSuccess: '上传成功',
    uploadFailed: '上传失败',
    reindexSubmitted: '已提交重新索引',
    consolidateDone: '记忆整合完成',
    deactivateDone: '已停用',
    published: '发布成功',
    unpublished: '已取消发布'
  },
  dialogs: {
    confirm: {
      dangerBody: '删除后不可恢复，请确认当前资源没有被其他配置依赖。',
      defaultBody: '请确认操作。'
    }
  }
} as const;
