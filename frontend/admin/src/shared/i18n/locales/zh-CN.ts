// Auto-generated from resources.ts — do not edit manually
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
  },
  modules: {
    aiChat: {
      label: 'AI 对话',
      summary: '与 AI 模型或 Agent 进行实时对话。',
      trace: {
        title: '执行轨迹',
        description: '上下文、skills、工具与回复过程会按时间顺序显示。',
        expandButton: '展开执行轨迹',
        collapseButton: '收起执行轨迹',
        emptyTitle: '暂无可视化轨迹',
        emptyDescription: '发送一条 Agent 消息后，这里会展示运行过程与结果。',
        cardModeTitle: '当前为模型模式',
        cardModeDescription: '右侧轨迹区仅展示 Agent 的 tools、MCP、skills 调用过程。切换到 Agent 模式并发送消息后即可查看。',
        noTraceDescription: '选择一条含有轨迹的助手消息，或先发送一条 Agent 消息。',
        skillsLabel: '技能',
        reasonLabel: '原因',
        runDetails: '运行详情',
        toolExpand: '展开入参与输出',
        toolCollapse: '收起',
        skills: {
          applied: '{{count}} 个已应用',
          noSkills: '本次运行未注入 skills',
          noContext: '未发现 skills 上下文。'
        },
        tools: {
          callCount: '{{count}} 次调用结果',
          noCalls: '本次运行没有工具调用',
          noResults: '没有工具、MCP 或 delegate 调用结果。'
        },
        steps: {
          count: '{{count}} 个步骤'
        }
      },
      message: {
        assistant: 'AI 助手',
        sending: '发送中…',
        failed: '发送失败',
        viewTrace: '查看执行轨迹',
        viewedTrace: '已查看执行轨迹',
        viewTraceShort: '查看轨迹',
        viewedTraceShort: '已查看轨迹',
        newConversation: '开始一段新对话',
        startTyping: '在下方输入消息开始对话',
        copy: '复制',
        regenerate: '重新生成'
      },
      sessionList: {
        eyebrow: '会话',
        newChat: '新对话',
        defaultTitle: '新对话 {{time}}',
        count: '{{count}} 个对话',
        noMessages: '暂无消息',
        deleteConversation: '删除对话',
        empty: '暂无对话记录'
      },
      selector: {
        model: '模型',
        agent: 'Agent',
        noAvailableAgent: '无可用 Agent',
        noAvailableModel: '无可用模型'
      },
      input: {
        placeholder: '想聊点什么？直接输入，Enter 发送，Shift+Enter 换行',
        addAttachment: '新增附件能力',
        toolSettings: '工具设置',
        toolLabel: '工具',
        voiceInput: '语音输入',
        sendMessage: '发送消息',
        stopGeneration: '停止生成'
      },
      loading: '加载中...'
    },
    agentManagement: {
      label: 'Agent 管理',
      summary: '管理 Agent 定义、版本发布与执行审计。',
      eyebrow: 'AI Agent 中心',
      title: 'Agent 管理',
      sections: {
        agents: 'Agent 列表',
        mcpServers: 'MCP Servers',
        skills: '技能管理',
        tools: '工具管理'
      },
      status: {
        allStatuses: '全部状态',
        draft: '草稿',
        published: '已发布',
        disabled: '已禁用',
        archived: '已归档',
        active: '活跃',
        deprecated: '已弃用',
        success: '成功',
        failed: '失败',
        timeout: '超时',
        enabled: '启用',
        stopped: '停用'
      },
      common: {
        cancel: '取消',
        save: '保存',
        submitting: '提交中...',
        loading: '加载中',
        close: '关闭',
        expand: '展开',
        collapse: '收起',
        createNow: '立即创建'
      },
      agents: {
        page: {
          newAgent: '新建 Agent',
          ownerTeamLabel: '负责团队',
          ownerTeamPlaceholder: '搜索团队',
          emptyTitle: '暂无 Agent 定义'
        },
        columns: {
          status: '状态',
          publishedVersion: '发布版本',
          ownerTeam: '负责团队',
          createdAt: '创建时间',
          actions: '操作'
        },
        actions: {
          manageVersions: '管理 Prompt 与版本',
          editDefinition: '编辑定义'
        },
        drawer: {
          titleCreate: '新建 Agent',
          titleEdit: '编辑定义',
          descCreate: '先创建 Agent 定义，再通过版本为它配置 Prompt、模型和运行策略。',
          descEdit: '这里只修改名称、描述、归属、标签和元数据。Prompt、模型与运行配置请在版本中编辑。',
          agentKey: 'Agent 标识',
          agentKeyPlaceholder: '例如 sales-assistant',
          agentKeyRequired: '请输入 Agent 标识。',
          displayName: '显示名称',
          displayNameRequired: '请输入显示名称。',
          ownerTeam: '负责团队',
          description: '描述',
          descriptionPlaceholder: '描述这个 Agent 的职责边界和业务用途',
          buttonCreate: '创建 Agent',
          buttonEdit: '保存定义',
          advanced: '高级定义信息',
          tags: '标签',
          tagsHint: '字符串数组，用于检索、筛选和分类。',
          metadata: '元数据',
          metadataHint: '仅用于扩展业务元信息，不影响 Prompt 与运行时行为。'
        },
        detail: {
          eyebrow: 'Agent 详情',
          ariaLabel: 'Agent 详情工作区',
          backTitle: '返回列表',
          breadcrumb: 'Agent 管理',
          tabVersions: '版本管理',
          tabAudits: '执行审计',
          createVersion: '创建版本',
          disable: '禁用',
          publishedVersion: '当前发布版本',
          notPublished: '未发布',
          ownerTeam: '负责团队',
          notSet: '未设置',
          createdAt: '创建时间',
          agentNotFound: '未找到该 Agent。',
          confirmPublish: {
            title: '发布版本',
            description: '确认将版本 v{{versionNumber}} 发布为当前运行版本吗？',
            label: '确认发布',
            body: '发布后该版本会成为运行时默认版本，已有已发布版本将被归档。'
          },
          confirmDisable: {
            title: '禁用 Agent',
            description: '确认禁用 {{name}} 吗？',
            label: '确认禁用',
            body: '禁用后运行时将拒绝该 Agent 的新执行请求，已在执行中的请求不受影响。'
          }
        }
      },
      audits: {
        actions: {
          viewTrace: '查看轨迹',
          copyRunId: '复制完整 Run ID'
        },
        actionLabels: {
          reply: '回复',
          handoff: '转接',
          error: '错误'
        },
        statusLabels: {
          success: '成功',
          failed: '失败',
          timeout: '超时'
        },
        filterStatuses: {
          all: '全部状态',
          success: '成功',
          error: '失败',
          timeout: '超时'
        },
        columns: {
          version: '版本',
          status: '状态',
          action: '动作',
          replyPreview: '回复预览',
          startedAt: '开始时间',
          completedAt: '完成时间',
          details: '详情'
        },
        panel: {
          title: '执行审计',
          description: '查看当前 Agent 各版本的运行记录与轨迹详情。'
        },
        searchPlaceholder: '搜索 Run ID…',
        loadError: '加载审计记录失败。',
        emptyFiltered: {
          title: '无匹配记录',
          description: '尝试修改搜索词或清除筛选条件。',
          clearFilters: '清除筛选'
        },
        emptyAll: {
          title: '暂无执行记录'
        },
        detail: {
          title: '执行详情',
          description: '查看一次 agent 运行的完整上下文、skills、工具调用与回复轨迹。',
          loadError: '加载执行详情失败。',
          loadingTitle: '加载中',
          loadingDescription: '正在读取本次运行的详细轨迹。',
          emptyTitle: '暂无执行详情',
          emptyDescription: '当前审计记录没有附带可展示的轨迹信息。'
        }
      },
      mcpServers: {
        allTransportTypes: '全部传输类型',
        columns: {
          name: '名称',
          transport: '传输类型',
          endpoint: '主连接信息',
          tags: '标签',
          status: '状态',
          createdAt: '创建时间',
          actions: '操作'
        },
        statusEnabled: '启用',
        statusStopped: '停用',
        actions: {
          edit: '编辑',
          delete: '删除'
        },
        newServer: '新建 MCP Server',
        filterTransport: '传输类型',
        searchLabel: '搜索',
        searchPlaceholder: '名称、命令、URL、标签',
        emptyTitle: '暂无 MCP Server 配置',
        confirmDelete: {
          title: '删除 MCP Server',
          description: '确认删除 MCP Server「{{name}}」吗？',
          label: '确认删除'
        },
        drawer: {
          titleCreate: '新建 MCP Server',
          titleEdit: '编辑 MCP Server',
          description: '配置 MCP Server 的传输方式与连接参数。',
          nameLabel: '名称',
          namePlaceholder: '如 filesystem',
          nameRequired: '请输入名称。',
          transportLabel: '传输类型',
          stdioCommandRequired: 'stdio 类型必须填写 command。',
          httpUrlRequired: 'http/sse 类型必须填写 URL。',
          toolNamePrefix: '工具名前缀',
          tagsLabel: '标签',
          tagsPlaceholder: '如 prod, stable（逗号分隔）',
          tagsHint: '会写入 config.tags。',
          fullConfig: '完整配置（config）',
          configHint: '将与上面的 command/url、prefix、tags 合并后提交到后端。',
          enabledLabel: '启用',
          buttonCreate: '创建',
          buttonEdit: '保存修改',
          loadingDetail: '正在加载 MCP Server 详情...',
          commandPlaceholder: '如 npx',
          urlPlaceholder: '如 http://localhost:3000/mcp',
          toolNamePrefixPlaceholder: '可选，如 fs_'
        }
      },
      skills: {
        allStatuses: '全部状态',
        columns: {
          skillKey: '技能标识',
          status: '状态',
          version: '版本',
          tags: '标签',
          updatedAt: '更新时间',
          actions: '操作'
        },
        statusPublished: '已发布',
        statusDraft: '草稿',
        actions: {
          edit: '编辑',
          workbench: '编排工作台',
          publish: '发布',
          delete: '删除'
        },
        newSkill: '新建技能',
        filterStatus: '状态',
        filterTag: '标签',
        filterTagPlaceholder: '按标签筛选',
        filterSearch: '搜索',
        filterSearchPlaceholder: '名称、标识、版本',
        emptyTitle: '暂无技能',
        emptyDescription: '创建技能后即可配置 Prompt 片段、工具绑定以及编排工作台。',
        confirmDelete: {
          title: '删除技能',
          description: '确认删除技能「{{name}}」吗？',
          label: '确认删除'
        },
        drawer: {
          titleCreate: '新建技能',
          titleEdit: '编辑技能',
          description: '定义一个可复用的技能，前端会将结构化表单映射到后端 Skill Spec。',
          skillKeyLabel: '技能标识',
          skillKeyPlaceholder: '如 summarize-document',
          skillKeyRequired: '请输入技能标识。',
          skillKeyPattern: '技能标识须以小写字母开头，只允许小写字母、数字、点、横线和下划线。',
          displayNameLabel: '显示名称',
          displayNameRequired: '请输入显示名称。',
          versionLabel: '版本号',
          versionPlaceholder: '如 1.0.0',
          versionRequired: '请输入版本号。',
          descriptionLabel: '描述',
          tagsLabel: '标签',
          tagsPlaceholder: '逗号分隔，如 nlp, summarization',
          buttonCreate: '创建技能',
          buttonEdit: '保存修改',
          loadingDetail: '加载中...',
          promptSectionsTitle: 'Prompt Sections',
          addPromptSection: '添加 Prompt Section',
          emptyPromptSections: '尚未添加 Prompt Section。',
          promptSectionTitle: 'Section #{{number}}',
          promptSectionKeyRequired: 'Prompt Section #{{number}} 的 key 不能为空。',
          promptSectionContentRequired: 'Prompt Section #{{number}} 的内容不能为空。',
          toolBindingsTitle: '工具绑定',
          addTool: '添加工具',
          emptyToolBindings: '尚未添加工具绑定。',
          toolTitle: '工具 #{{number}}',
          toolNameRequired: '工具 #{{number}} 名称不能为空。',
          advancedConfig: '高级配置',
          invocationModeAuto: '自动（LLM 决定）',
          invocationModeManual: '仅手动触发',
          invocationModeDisabled: '已禁用',
          toolNameLabel: '工具名称',
          invocationModeLabel: '调用模式',
          requiredLabel: '必需工具',
          enabledLabel: '启用',
          sectionKeyPlaceholder: '如 system / context',
          sectionSortOrder: '排序',
          sectionContent: '内容',
          configSchemaLabel: '配置 Schema（spec.configSchema）'
        },
        workbench: {
          title: '技能编排工作台',
          eyebrow: '技能编排',
          pageTitle: '{{name}} 编排工作台',
          backToList: '返回技能列表',
          autoLayout: '自动布局',
          saveOrchestration: '保存编排',
          skillKeyLabel: '技能标识：',
          validationValid: '结构有效',
          validationInvalid: '存在校验问题',
          unsavedChanges: '有未保存改动',
          synced: '已与已加载版本同步',
          versionLabel: '版本：',
          outlinePanel: '步骤目录',
          inspectorPanel: '节点检查器',
          canvasPanel: '流程画布',
          validationPanel: '校验',
          remoteUpdateMessage: '远端技能定义已更新，当前仍保留你的本地草稿。',
          applyRemoteVersion: '加载远端最新版本',
          loadingMessage: '正在加载技能编排工作台…',
          skillNotFound: '未找到对应技能。',
          nodeLabels: {
            start: '开始',
            task: '任务',
            decision: '判断',
            handoff: '转交',
            terminal: '结束'
          },
          edgeTypes: {
            default: '默认流转',
            condition: '条件分支',
            fallback: '失败兜底',
            error: '异常分支',
            handoff: '转交流转'
          },
          validation: {
            pass: '校验通过',
            fail: '校验失败',
            errorCount: '{{errors}} 条错误，{{warnings}} 条提醒',
            errorsSection: '错误',
            warningsSection: '提醒'
          },
          defaults: {
            taskTitle: '新步骤',
            handoffTitle: '转人工处理',
            handoffSummary: '请整理当前上下文后转交人工处理。',
            terminalTitle: '处理完成',
            terminalNote: '流程已完成。',
            decisionTitle: '判断去向',
            decisionQuestion: '根据当前信息选择后续分支。',
            enterDecisionLabel: '进入判断',
            continueAutoLabel: '继续自动处理',
            continueAutoDescription: '满足自动处理条件时继续执行',
            handoffBranchLabel: '转人工',
            branchHandoffLabel: '转交处理',
            branchTerminalLabel: '结束流程',
            branchConditionDescription: '命中分支 {{n}} 时结束流程',
            taskBranchHandoff: '转交处理',
            taskBranchFallbackHandoff: '兜底转交',
            taskBranchFallbackTerminal: '兜底结束',
            taskBranchErrorHandoff: '异常转交',
            taskBranchErrorTerminal: '异常结束',
            fallbackNote: '失败时转入兜底分支。',
            toolReason: '使用 {{toolId}} 支撑"{{title}}"步骤。'
          },
          inspector: {
            noSelectionTitle: '尚未选中节点',
            noSelectionDescription: '从左侧目录或画布中选择一个节点或流转后，再在这里继续编辑。',
            startNodeTitle: '开始节点无需编辑',
            startNodeDescription: '开始节点只负责定义入口，后续步骤请在其他节点上配置。',
            deleteTask: '删除任务节点',
            deleteHandoff: '删除转交节点',
            deleteTerminal: '删除结束节点',
            taskTitle: '步骤标题',
            taskGoal: '步骤目标',
            taskInherited: '继承输入',
            taskRequired: '必填输入',
            taskOptional: '可选输入',
            taskOutput: '输出结果',
            fallbackPolicyLabel: '兜底策略',
            fallbackStay: '留在当前步骤',
            fallbackHandoffOption: '转交处理',
            fallbackGoto: '跳转到兜底分支',
            fallbackTargetLabel: '兜底目标流转',
            fallbackTargetPlaceholder: '请先选择流转',
            fallbackTargetDisabled: '当前模式无需选择',
            fallbackNoteLabel: '兜底说明',
            branchSectionTitle: '异常与转交分支',
            branchSectionDescription: '补齐当前任务的兜底、异常和人工转交流程。',
            addFallbackBranch: '新增兜底分支',
            addErrorBranch: '新增异常分支',
            addHandoffBranch: '新增转交分支',
            noBranches: '当前任务尚未配置额外分支。',
            targetNode: '目标节点：{{title}}',
            branchLabelFallback: '兜底',
            branchLabelError: '异常',
            branchLabelHandoff: '转交',
            toolSectionTitle: '工具计划',
            toolSectionDescription: '为当前步骤管理要调用的技能工具。',
            addToolButton: '添加工具',
            noTools: '当前步骤尚未配置工具。',
            removeTool: '移除',
            noAvailableTools: '已启用工具均已加入当前步骤。',
            requiredBadge: '必需',
            noDescription: '暂无工具描述。',
            toolDetailTitle: '工具详情：{{name}}',
            toolNotFound: '当前工具已不在可用工具库中。',
            toolCallReason: '调用原因',
            addToolById: '添加 {{id}}',
            handoffTitle: '转交标题',
            handoffTypeLabel: '转交类型',
            handoffTypeHuman: '人工处理',
            handoffTypeTicket: '生成工单',
            handoffTypeOtherAgent: '转其他 Agent',
            handoffSummaryLabel: '交接摘要模板',
            terminalTitle: '结束标题',
            terminalOutcomeLabel: '结束结果',
            terminalResolved: '已解决',
            terminalBlocked: '被阻塞',
            terminalCancelled: '已取消',
            terminalNoteLabel: '结束说明',
            decisionTitle: '决策标题',
            decisionQuestion: '决策问题',
            decisionBranchSectionTitle: '分支概览',
            decisionBranchSectionDescription: '为当前判断节点增加新的结束或转交流转。',
            addConditionBranch: '新增条件分支',
            addDecisionHandoffBranch: '新增转交分支',
            transitionKindHandoff: '转交',
            transitionKindCondition: '条件',
            transitionKindPriority: '{{kind}} / 优先级 {{priority}}',
            transitionName: '流转名称',
            transitionType: '流转类型',
            transitionPriorityLabel: '优先级',
            transitionCondition: '命中条件说明',
            transitionField: '条件字段',
            transitionOperator: '运算符',
            transitionValue: '命中值',
            operatorEq: '等于',
            operatorIn: '包含于'
          },
          outline: {
            insertBefore: '插入前置任务步骤',
            insertAfter: '插入后置任务步骤',
            insertDecisionAfter: '插入后置判断步骤'
          }
        }
      },
      tools: {
        allTypes: '全部类型',
        allStatuses: '全部状态',
        statusActive: '活跃',
        statusDeprecated: '弃用',
        statusDisabled: '已禁用',
        columns: {
          toolName: '工具名称',
          type: '类型',
          status: '状态',
          tags: '标签',
          timeout: '超时',
          updatedAt: '更新时间'
        },
        actions: {
          view: '查看',
          edit: '编辑',
          disable: '禁用'
        },
        confirmDisable: '确认禁用工具「{{name}}」？',
        syncResult: '同步完成，共同步 {{count}} 个工具。',
        refreshButton: '刷新',
        syncButton: '同步内置工具',
        newToolButton: '新建外部工具',
        filterType: '类型',
        filterStatus: '状态',
        filterSearch: '搜索',
        filterSearchPlaceholder: '工具名称或描述',
        loadError: '加载工具列表失败，请刷新重试。',
        loadingText: '加载中…',
        emptyTitle: '暂无工具',
        emptyDescription: '尚无匹配的工具定义。',
        drawer: {
          titleBuiltin: '查看内置工具：{{name}}',
          titleEdit: '编辑外部工具：{{name}}',
          titleCreate: '新建外部工具',
          builtinNotice: '内置工具由 Python 运行时管理，元数据在服务启动时自动同步。此处仅供查看。',
          toolNameLabel: '工具名称',
          toolNameRequired: '请输入工具名称。',
          toolNamePattern: '工具名称须以小写字母开头，只允许小写字母、数字和下划线。',
          toolNameSnakeCase: '工具名称 (snake_case)',
          displayNameLabel: '显示名称',
          displayNameRequired: '请输入显示名称。',
          descriptionLabel: '描述',
          descriptionRequired: '请输入工具描述。',
          descriptionLlm: '描述（LLM function-calling）',
          endpointLabel: 'Endpoint URL',
          endpointRequired: '请输入 Endpoint URL。',
          timeoutLabel: '超时（秒）',
          maxRetriesLabel: '最大重试次数',
          tagsLabel: '标签（逗号分隔）',
          parametersSchemaLabel: '参数 Schema (JSON Schema)',
          saveButton: '保存',
          savingButton: '保存中…'
        }
      },
      versions: {
        statusDraft: '草稿',
        statusPublished: '已发布',
        statusArchived: '已归档',
        columns: {
          versionNumber: '版本号',
          status: '状态',
          label: '标签',
          changelog: 'Changelog',
          model: '模型',
          publishedAt: '发布时间',
          createdAt: '创建时间',
          actions: '操作'
        },
        actions: {
          view: '查看',
          createDraft: '创建草稿',
          editDraft: '编辑草稿',
          publish: '发布'
        },
        searchPlaceholder: '搜索版本号 / 标签 / Changelog…',
        allStatuses: '全部状态',
        publishedReadonlyInfo: '已发布版本只读。若要修改 Prompt、模型或运行策略，请基于某个版本创建草稿后再发布。',
        loadError: '加载版本列表失败。',
        emptyFiltered: {
          title: '无匹配版本',
          description: '尝试修改搜索词或清除筛选条件。',
          clearFilters: '清除筛选'
        },
        emptyAll: {
          title: '暂无版本',
          description: '先创建首个版本，再为 Agent 配置 Prompt、模型与运行策略。',
          createFirst: '创建第一个版本'
        },
        drawer: {
          titleView: '查看版本 v{{versionNumber}}',
          titleEdit: '编辑草稿 v{{versionNumber}}',
          titleClone: '基于 v{{versionNumber}} 创建草稿',
          titleCreate: '创建版本',
          descReadonly: '已发布版本为只读状态。若要修改 Prompt、模型或运行策略，请返回列表基于它创建草稿。',
          descEdit: '版本主表与 Tool / MCP / Skill / 知识库绑定会通过同一个 Agent Version 请求原子保存。',
          buttonClose: '关闭',
          buttonCancel: '取消',
          buttonSubmitting: '提交中...',
          buttonSave: '保存修改',
          buttonCreateDraft: '创建草稿',
          buttonCreate: '创建版本',
          loadingBindings: '正在加载 Tool / Knowledge Base / MCP / Skill 绑定...',
          modelLabel: '模型',
          modelLoading: '加载中...',
          modelPlaceholder: '请选择模型',
          versionLabel: '版本标签',
          versionPlaceholder: '例如 v1-beta',
          localeLabel: '默认语言',
          localePlaceholder: '例如 zh-CN',
          changelogLabel: '变更说明',
          toolBindings: '工具绑定',
          addTool: '添加工具',
          emptyToolBindings: '尚未添加工具绑定。',
          selectTool: '请选择工具',
          toolLabel: '工具 #{{number}}',
          mcpBindings: 'MCP 绑定',
          addMcpBinding: '添加 MCP 绑定',
          emptyMcpBindings: '尚未添加 MCP 绑定。',
          mcpLabel: 'MCP 绑定 #{{number}}',
          selectMcpServer: '请选择 MCP Server',
          toolWhitelist: '工具白名单',
          toolWhitelistPlaceholder: '留空表示允许全部工具，使用逗号分隔',
          skillBindings: '技能绑定',
          addSkillBinding: '添加技能绑定',
          emptySkillBindings: '尚未添加技能绑定。',
          skillLabel: '技能绑定 #{{number}}',
          selectSkill: '请选择技能',
          configOverrides: '配置覆盖（configOverrides）',
          toolOverrides: '工具覆盖',
          addToolOverride: '添加工具覆盖',
          emptyToolOverrides: '尚未添加工具覆盖。',
          toolOverrideLabel: '工具覆盖 #{{number}}',
          advancedPolicy: '高级策略配置',
          advancedPolicyHint: '以下高级 JSON 策略仅作用于当前 agent version；留空时系统将使用默认策略。',
          agentLocalGuardrailsPolicyLabel: 'Agent 本地 Guardrails 策略',
          invocationModeAuto: '自动（由模型决定）',
          invocationModeManual: '仅手动调用',
          invocationModeDisabled: '禁用',
          toolNameLabel: '工具名称',
          toolDisplayNameLabel: '显示名称',
          toolDescriptionLabel: '描述（覆盖 ToolSpec）',
          toolInvocationModeLabel: '调用模式',
          toolRequiredLabel: '必需工具',
          toolEnabledLabel: '启用',
          mcpEnabledLabel: '启用',
          skillKeyLabel: '技能',
          skillSortLabel: '排序',
          skillEnabledLabel: '启用'
        },
        kbBindings: {
          sectionTitle: '知识库绑定',
          addButton: '新增知识库绑定',
          readonlyInfo: '当前版本已发布，知识库绑定不可直接修改；如需调整，请基于该版本创建草稿。',
          missingToolWarning: '已绑定知识库，但当前 version 尚未绑定可用的 knowledge_search 工具；这些知识库不会被运行时实际消费。',
          emptyTitle: '当前版本尚未绑定知识库',
          emptyDescription: '绑定后，knowledge_search 可以在已发布版本中按该范围检索。',
          drawerTitle: '新增知识库绑定',
          drawerDescription: '为当前 draft version 添加知识库范围。',
          sortLabel: '排序',
          enabledLabel: '启用',
          selectLabel: '知识库',
          selectPlaceholder: '请选择知识库',
          saveButton: '保存绑定'
        }
      }
    },
    modelManagement: {
      label: '模型管理',
      summary: '统一维护连接配置、模型卡、模型实例和模型绑定。',
      eyebrow: 'AI 模型中心',
      title: '模型管理',
      sections: {
        cards: '模型',
        instances: '部署实例',
        bindings: '场景绑定',
        profiles: '服务商连接',
        features: '能力定义'
      },
      detail: {
        fallbackTitle: '模型详情',
        backToList: '返回模型列表',
        sections: {
          overview: '基本信息',
          instances: '部署实例',
          bindings: '场景绑定'
        }
      },
      errors: {
        connectionProfileKeyMismatch: '连接标识不一致，请刷新后重试。',
        modelKeyMismatch: '模型标识不一致，请刷新后重试。',
        instanceKeyMismatch: '实例标识不一致，请刷新后重试。',
        bindingKeyMismatch: '绑定标识不一致，请刷新后重试。',
        unsupportedProvider: '不支持该服务商类型。',
        unsupportedScene: '不支持该业务场景。',
        invalidJsonKind: '格式不正确，请检查 JSON 格式。',
        invalidJson: 'JSON 格式有误，请修正后重试。',
        inUse: '该项正在被使用中，无法删除。',
        alreadyExists: '该标识已存在，请使用其他名称。',
        notFound: '未找到该项，可能已被删除。'
      },
      featureValidation: {
        booleanRequired: '请选择是或否。',
        integerRequired: '请输入整数。',
        numberRequired: '请输入数字。',
        enumRequired: '请选择一个有效选项。'
      },
      shared: {
        enabledStatusOptions: {
          all: '全部状态',
          enabledOnly: '仅启用',
          disabledOnly: '仅停用'
        },
        filterableOptions: {
          all: '全部筛选状态',
          filterableOnly: '仅可筛选',
          notFilterableOnly: '仅不可筛选'
        },
        routableOptions: {
          all: '全部路由状态',
          routableOnly: '仅可路由',
          notRoutableOnly: '仅不可路由'
        },
        healthStatusOptions: {
          all: '全部健康状态',
          healthyOnly: '仅健康',
          unhealthyOnly: '仅异常'
        }
      },
      models: {
        page: {
          newModel: '新建模型',
          viewModeTable: '列表',
          viewModeGrid: '卡片',
          filterFeature: '能力',
          filterFeatureAll: '全部',
          filterEnableStatus: '启用状态',
          emptyTitle: '暂无模型',
          createModel: '创建模型',
          deleteTitle: '删除模型',
          deleteDescription: '确认删除模型 {{name}} 吗？',
          confirmDelete: '确认删除',
          columns: {
            displayName: '显示名称',
            instances: '部署实例',
            bindings: '场景绑定',
            features: '能力',
            status: '状态',
            actions: '操作'
          },
          rowActions: {
            edit: '编辑',
            detail: '详情',
            test: '测试',
            testEmbedding: '向量测试',
            delete: '删除'
          },
          statsInstanceCount: '{{count}} 个实例',
          statsInstanceCountWithHealth: '{{count}} 个实例 · {{healthy}} 健康',
          statsBindingCount: '{{count}} 个绑定',
          noFeature: '未配置能力',
          status: {
            enabled: '启用',
            disabled: '停用'
          }
        },
        test: {
          title: '模型测试',
          empty: '输入消息开始测试，可连续对话。每轮回复下方会显示实例 / 首 Token 延迟 / 耗时 / token 等诊断信息。',
          inputPlaceholder: '输入测试消息...',
          send: '发送',
          stop: '停止',
          generating: '生成中...',
          diagnosis: {
            instanceKey: '实例',
            provider: 'Provider',
            ttft: '首 Token',
            total: '总耗时',
            inputTokens: '入',
            outputTokens: '出',
            finishReason: '结束',
            error: '错误',
            noData: '—'
          },
          errors: {
            noEnabledInstance: '该模型没有可用的启用实例',
            upstreamError: '上游调用失败'
          }
        },
        embeddingTest: {
          title: '向量模型测试 — {{model}}',
          empty: '输入文本，点击测试即可生成向量。下方会显示向量预览及诊断信息。',
          textLabel: '测试文本',
          textPlaceholder: '输入要向量化的文本...',
          dimensionsLabel: '向量维度（可选）',
          dimensionsPlaceholder: '默认',
          dimensionsHint: '留空使用模型默认维度。Embedding-3 支持 256~2048。',
          close: '关闭',
          test: '测试',
          testing: '测试中...',
          provider: 'Provider',
          model: '模型',
          dimensions: '维度',
          latency: '耗时',
          tokens: 'Tokens',
          vectorPreview: '向量预览',
          firstN: '前 {{n}} 位',
          unknownError: '未知错误'
        },
        drawer: {
          titleCreate: '新建模型',
          titleEdit: '编辑模型',
          navigateToDetail: '创建后跳转到详情页',
          fields: {
            modelKey: '模型标识',
            type: '类型',
            modelName: '模型名称',
            displayName: '显示名称',
            enableStatus: '启用状态',
            description: '描述',
            enabled: '启用',
            disabled: '停用',
            disabledBadge: ' (已禁用)',
            connectionProfileKey: '连接配置',
            connectionProfileLoading: '加载中...',
            connectionProfilePlaceholder: '请选择连接配置'
          },
          features: {
            sectionTitle: '可用能力',
            hint: '以下是系统中可用的能力定义。创建模型后，可在详情页中配置支持的能力。',
            loading: '加载中...',
            empty: '暂无能力定义，请先在「能力定义」页创建。'
          },
          pricing: {
            sectionTitle: '定价（每 1M tokens / USD）',
            inputPrice: '输入价格',
            outputPrice: '输出价格',
            cacheWritePrice: '缓存写入价格',
            cacheReadPrice: '缓存读取价格',
            unitHint: '$/MTok'
          },
          advanced: {
            sectionTitle: '高级配置',
            tags: '标签',
            tagsHint: '用于分类和搜索的标签。',
            routingPolicy: '路由策略',
            routingPolicyHint: '控制请求如何分配到不同实例。',
            retryPolicy: '重试策略',
            retryPolicyHint: '请求失败时的自动重试规则。'
          },
          actions: {
            cancel: '取消',
            submitting: '提交中...',
            create: '创建模型',
            save: '保存修改'
          },
          validation: {
            modelKeyRequired: '请输入模型标识。',
            modelNameRequired: '请输入模型名称。',
            displayNameRequired: '请输入显示名称。',
            connectionProfileKeyRequired: '请选择连接配置。'
          }
        },
        detail: {
          loading: '正在加载...',
          loadFailed: '加载失败，请稍后重试。',
          actions: {
            backToList: '返回列表',
            addInstance: '添加实例',
            addBinding: '添加绑定'
          },
          basicInfo: {
            cardTitle: '基本信息',
            cardDescription: '模型的基础配置信息。',
            modelLabel: '模型',
            modelKeyLabel: '模型标识',
            connectionProfileLabel: '连接配置',
            bindingsCount: '场景绑定',
            instancesCount: '部署实例',
            featureCount: '能力数',
            statusLabel: '状态',
            enabled: '已启用',
            disabled: '已停用',
            descriptionLabel: '描述',
            noDescription: '暂无描述',
            countUnit: '{{count}} 个'
          },
          instances: {
            cardTitle: '部署实例',
            cardDescription: '每个实例对应一个实际的模型部署，系统会根据优先级和权重自动选择最佳实例。',
            addButton: '新增实例',
            stats: {
              total: '总实例数',
              healthy: '健康比例',
              enabled: '已启用',
              regions: '区域数'
            },
            fields: {
              deployName: '部署名',
              connection: '连接',
              region: '区域',
              priority: '优先级',
              weight: '权重',
              timeout: '超时',
              type: '类型'
            },
            status: {
              enabled: '启用',
              disabled: '停用',
              healthy: '健康',
              unhealthy: '异常'
            },
            defaultDeploy: '默认部署',
            defaultRegion: '默认区域',
            editButton: '编辑',
            empty: '暂无部署实例'
          },
          bindings: {
            cardTitle: '场景绑定',
            cardDescription: '将此模型分配到不同的业务场景中。',
            addButton: '新增绑定',
            empty: '暂无场景绑定',
            status: {
              enabled: '启用',
              disabled: '停用'
            }
          }
        },
        featureSection: {
          cardTitle: '模型能力',
          configuredCount: '已配置 {{configured}} / {{total}} 项',
          configured: '已配置',
          unconfigured: '未配置',
          loading: '正在加载能力列表...',
          empty: '暂无可配置的能力',
          disabled: '已禁用',
          filterable: '可筛选',
          routable: '影响路由',
          save: '保存',
          saving: '保存中...',
          remove: '移除',
          removing: '删除中...',
          source: '数据来源',
          remark: '备注',
          noFeature: '未配置能力',
          dnd: {
            dragAriaLabel: '拖拽 {{name}}',
            removeAriaLabel: '移除 {{name}}',
            toggleAriaLabel: '切换 {{name}} 启用状态',
            addAriaLabel: '添加 {{name}}',
            edit: '编辑',
            valueNotSet: '(未设置)',
            valuePrefix: '值: ',
            add: '添加',
            remove: '移除',
            unconfiguredTitle: '可用能力',
            configuredTitle: '已配置能力',
            unconfiguredEmpty: '已添加所有能力',
            configuredEmpty: '从左侧拖拽能力到此处',
            hint: '提示：支持拖拽，也支持直接点击"添加 / 移除"完成配置。点击"编辑"可修改能力值。',
            editModal: {
              title: '编辑能力',
              enableLabel: '启用此能力',
              featureValue: '能力值',
              booleanTrue: '是',
              booleanFalse: '否',
              source: '数据来源',
              remark: '备注',
              cancel: '取消',
              save: '保存',
              saving: '保存中...'
            }
          }
        },
        tabs: {
          loading: '正在加载...',
          loadFailed: '加载失败，请稍后重试。',
          instances: {
            description: '每个实例对应一个实际的模型部署，系统会根据优先级和权重自动选择最佳实例。',
            addButton: '新增实例',
            stats: {
              total: '总实例数',
              healthy: '健康比例',
              enabled: '已启用',
              regions: '区域数'
            },
            fields: {
              deployName: '部署名',
              connection: '连接',
              region: '区域',
              priority: '优先级',
              weight: '权重',
              timeout: '超时',
              type: '类型'
            },
            status: {
              enabled: '启用',
              disabled: '停用',
              healthy: '健康',
              unhealthy: '异常'
            },
            defaultDeploy: '默认部署',
            defaultRegion: '默认区域',
            editButton: '编辑',
            empty: '暂无部署实例'
          },
          bindings: {
            description: '将此模型分配到不同的业务场景中。',
            addButton: '新增绑定',
            empty: '暂无场景绑定',
            status: {
              enabled: '启用',
              disabled: '停用'
            }
          },
          overview: {
            basicInfo: '基本信息',
            modelLabel: '模型',
            modelKeyLabel: '模型标识',
            bindingsCount: '场景绑定',
            instancesCount: '部署实例',
            featureCount: '能力数',
            statusLabel: '状态',
            enabled: '已启用',
            disabled: '已停用',
            descriptionLabel: '描述',
            noDescription: '暂无描述',
            countUnit: '{{count}} 个',
            status: {
              enabled: '启用',
              disabled: '停用'
            }
          }
        },
        deleteDialog: {
          title: '删除模型',
          description: '确认删除模型 {{name}} 吗？',
          confirmLabel: '确认删除'
        }
      },
      connectionProfiles: {
        page: {
          newProfile: '新建连接',
          columns: {
            profileKey: '连接名称',
            endpoint: '服务地址',
            status: '状态',
            actions: '操作'
          },
          filters: {
            provider: '服务商',
            allProviders: '全部服务商',
            enableStatus: '启用状态'
          },
          emptyTitle: '暂无服务商连接',
          status: {
            enabled: '启用',
            disabled: '停用'
          },
          rowActions: {
            edit: '编辑',
            delete: '删除'
          },
          deleteTitle: '删除连接',
          deleteDescription: '确认删除连接 {{name}} 吗？',
          confirmDelete: '确认删除'
        },
        drawer: {
          titleCreate: '新建服务商连接',
          titleEdit: '编辑服务商连接',
          description: '填写 AI 服务商的接入信息。高级参数可在底部展开配置。',
          fields: {
            profileKey: '连接标识',
            displayName: '显示名称',
            baseUrl: '服务地址',
            baseUrlHint: '填写 AI 服务商的 API 根地址。例如：OpenAI 填 https://api.openai.com/v1/，Azure OpenAI 填 https://{资源名}.openai.azure.com/openai/',
            wsUrl: 'WebSocket 地址',
            wsUrlHint: '用于实时语音等 WebSocket 场景。通常无需填写，仅在服务商提供独立 WebSocket 入口时配置。',
            apiVersion: 'API 版本',
            apiVersionHint: '部分服务商（如 Azure OpenAI）需要指定 API 版本号，例如 2025-04-01-preview。OpenAI 通常无需填写。',
            apiVersionPlaceholder: '如 2025-04-01-preview',
            enableConnection: '启用此连接',
            extraJson: '扩展参数',
            extraJsonHint: '服务商特有的额外配置项。'
          },
          advanced: {
            sectionTitle: '高级参数',
            collapse: '收起',
            expand: '展开'
          },
          actions: {
            cancel: '取消',
            submitting: '提交中...',
            create: '创建连接',
            save: '保存修改'
          },
          validation: {
            profileKeyRequired: '请输入连接标识。',
            displayNameRequired: '请输入显示名称。'
          }
        }
      },
      featureDefinitions: {
        page: {
          newFeature: '新建能力',
          columns: {
            featureKey: '能力名称',
            valueType: '数据类型',
            flags: '用途标记',
            status: '状态',
            actions: '操作'
          },
          filters: {
            valueType: '数据类型',
            allTypes: '全部类型',
            enableStatus: '启用状态',
            filterable: '可筛选',
            routable: '可路由'
          },
          flags: {
            filterable: '可筛选',
            routable: '影响路由'
          },
          status: {
            enabled: '启用',
            disabled: '停用'
          },
          rowActions: {
            edit: '编辑',
            delete: '删除'
          },
          emptyTitle: '暂无能力定义',
          deleteTitle: '删除能力',
          deleteDescription: '确认删除能力 {{name}} 吗？',
          confirmDelete: '确认删除',
          createNow: '立即创建'
        },
        drawer: {
          titleCreate: '新建能力定义',
          titleEdit: '编辑能力定义',
          description: '定义模型可以声明的能力标签，用于筛选和路由。',
          fields: {
            featureKey: '能力标识',
            displayName: '显示名称',
            valueType: '数据类型',
            description: '描述',
            allowedValues: '允许的选项',
            allowedValuesHint: '仅在数据类型为枚举时使用，定义可选值列表。',
            isFilterable: '支持筛选',
            isRoutable: '影响路由',
            isEnabled: '启用'
          },
          actions: {
            cancel: '取消',
            submitting: '提交中...',
            create: '创建能力',
            save: '保存修改'
          },
          validation: {
            featureKeyRequired: '请输入能力标识。',
            displayNameRequired: '请输入显示名称。',
            valueTypeRequired: '请选择数据类型。'
          }
        }
      },
      modelBindings: {
        page: {
          newBinding: '新建绑定',
          columns: {
            bindingKey: '绑定名称',
            usage: '用途',
            mapping: '能力 / 模型',
            status: '状态',
            actions: '操作'
          },
          filters: {
            capability: '能力',
            allCapabilities: '全部能力',
            modelKey: '关联模型',
            enableStatus: '启用状态'
          },
          status: {
            enabled: '启用',
            disabled: '停用'
          },
          rowActions: {
            edit: '编辑',
            delete: '删除'
          },
          emptyTitle: '暂无场景绑定',
          createBinding: '创建绑定',
          deleteTitle: '删除绑定',
          deleteDescription: '确认删除绑定 {{name}} 吗？',
          confirmDelete: '确认删除'
        },
        drawer: {
          titleCreate: '新建绑定',
          titleEdit: '编辑绑定',
          description: '将模型分配到业务场景中。',
          fields: {
            bindingKey: '绑定标识',
            displayName: '显示名称',
            preset: '用途模板',
            presetHint: '选择后自动填入能力类型，也可在下方手动调整。',
            capability: '能力',
            modelKey: '关联模型',
            modelKeyLoading: '加载中...',
            modelKeyPlaceholder: '请选择模型',
            enableBinding: '启用此绑定',
            metadataJson: '扩展参数',
            metadataJsonHint: '场景相关的额外配置项。'
          },
          actions: {
            cancel: '取消',
            submitting: '提交中...',
            create: '创建绑定',
            save: '保存修改'
          },
          validation: {
            bindingKeyRequired: '请输入绑定标识。',
            displayNameRequired: '请输入显示名称。',
            modelKeyRequired: '请选择关联模型。'
          }
        }
      },
      modelInstances: {
        page: {
          newInstance: '新建实例',
          columns: {
            instanceKey: '实例',
            modelName: '模型名称',
            connectionProfileKey: '服务商连接',
            priority: '优先级 / 权重 / 超时',
            status: '状态',
            actions: '操作'
          },
          filters: {
            modelKey: '所属模型',
            connectionProfileKey: '服务商连接',
            feature: '能力',
            featureAll: '全部',
            featureSupport: '能力支持',
            featureSupportAll: '全部',
            featureSupportTrue: '支持',
            featureSupportFalse: '不支持',
            featureValue: '能力值',
            type: '类型',
            typeAll: '全部类型',
            loading: '加载中...',
            enableStatus: '启用状态',
            healthStatus: '健康状态'
          },
          metrics: {
            total: '总数',
            totalHint: '符合筛选条件的实例总数',
            enabled: '已启用',
            enabledHint: '当前页已启用的实例数',
            healthy: '运行正常',
            healthyHint: '当前页运行正常的实例数',
            typeCount: '能力类型',
            typeCountHint: '当前页涉及的能力类型数'
          },
          status: {
            enabled: '启用',
            disabled: '停用',
            healthy: '健康',
            unhealthy: '异常'
          },
          rowActions: {
            edit: '编辑',
            delete: '删除'
          },
          emptyTitle: '暂无部署实例',
          createInstance: '创建实例',
          deleteTitle: '删除实例',
          deleteDescription: '确认删除模型实例 {{name}} 吗？',
          confirmDelete: '确认删除'
        },
        drawer: {
          titleCreate: '新建实例',
          titleEdit: '编辑实例',
          description: '实例代表一个实际的模型部署。能力配置继承自所属模型，连接配置在实例级单独选择。',
          fields: {
            modelKey: '所属模型',
            modelKeyLoading: '加载中...',
            modelKeyPlaceholder: '请选择模型',
            instanceKey: '实例标识',
            connectionProfileKey: '所用连接',
            connectionProfileLoading: '加载中...',
            connectionProfilePlaceholder: '请选择服务商连接',
            deploymentName: '部署名称',
            region: '区域',
            priority: '优先级',
            weight: '权重',
            timeout: '默认超时 (ms)',
            apiKey: 'API 密钥',
            apiKeyHintEdit: '留空表示不修改当前密钥。',
            apiKeyHintCreate: '提交后不再显示，请妥善保管。',
            apiKeyPlaceholderEdit: '留空不修改',
            instanceUrl: '实例 URL',
            instanceUrlHint: '由所用连接自动决定，不可手动编辑。',
            isEnabled: '启用实例',
            isHealthy: '健康状态',
            extraJson: '扩展参数',
            extraJsonHint: '实例的额外配置项。',
            advancedOptions: '高级选项'
          },
          actions: {
            cancel: '取消',
            submitting: '提交中...',
            create: '创建实例',
            save: '保存修改'
          },
          validation: {
            modelKeyRequired: '请选择所属模型。',
            instanceKeyRequired: '请输入实例标识。',
            connectionProfileKeyRequired: '请选择所用连接。',
            priorityMin: '优先级不能小于 0。',
            weightMin: '权重必须大于 0。',
            timeoutMin: '默认超时必须大于 0。',
            apiKeyRequired: '请输入实例密钥。'
          }
        }
      },
      instancesByModel: {
        modelList: '模型列表',
        noModels: '暂无模型',
        selectModel: '请选择模型',
        selectModelHint: '从左侧模型列表中选择一个模型，查看其部署实例',
        instancesTitle: '{{count}} 个部署实例',
        noInstances: '暂无部署实例',
        emptyTitle: '该模型暂无部署实例',
        emptyDescription: '点击右上角按钮为该模型创建第一个实例。',
        instanceCount: '{{count}} 个实例'
      }
    },
    glossary: {
      label: '术语库',
      summary: '统一维护术语分类、术语条目并绑定到知识库。',
      eyebrow: '知识增强',
      title: '术语库',
      sections: {
        list: '术语管理'
      },
      list: {
        title: '术语库',
        description: '管理术语分类、术语条目与知识库术语素材。',
        newCategory: '新建分类',
        searchLabel: '搜索',
        searchPlaceholder: '分类名称...',
        emptyTitle: '暂无术语分类',
        emptyDescription: '点击“新建分类”开始使用。',
        deleteTitle: '删除分类',
        deleteDescription: '确定删除分类“{{name}}”吗？',
        confirmDelete: '删除分类'
      },
      categoryForm: {
        titleCreate: '新建分类',
        titleEdit: '编辑分类',
        description: '分类用于组织术语条目，并作为知识库绑定的最小单位。',
        fields: {
          name: '分类名称',
          namePlaceholder: '例如：RAG',
          description: '分类说明',
          descriptionPlaceholder: '可选，用于说明这组术语的适用场景。'
        },
        actions: {
          cancel: '取消',
          submitting: '保存中...',
          create: '创建分类',
          save: '保存'
        },
        validation: {
          nameRequired: '请输入分类名称。'
        }
      },
      category: {
        fallbackTitle: '术语分类',
        eyebrow: '术语库',
        backToList: '返回术语库',
        sections: {
          terms: '术语列表'
        }
      },
      categoryCard: {
        menuLabel: '分类操作',
        actions: {
          edit: '编辑',
          delete: '删除'
        }
      },
      categoryItem: {
        descriptionFallback: '未填写分类说明',
        actions: {
          edit: '编辑',
          delete: '删除'
        }
      },
      termsTab: {
        columns: {
          term: '术语',
          synonyms: '别名',
          createdAt: '创建时间',
          actions: '操作'
        },
        rowActions: {
          edit: '编辑',
          delete: '删除'
        },
        toolbar: {
          import: '导入术语',
          create: '新建术语',
          searchLabel: '搜索',
          searchPlaceholder: '搜索术语或别名...'
        },
        emptyTitle: '暂无术语',
        emptyDescription: '当前分类还没有术语，可以手动新增或通过导入补齐。',
        emptyAction: '添加术语',
        deleteTitle: '删除术语',
        deleteDescription: '确定删除术语“{{name}}”吗？',
        confirmDelete: '删除术语'
      },
      termForm: {
        titleCreate: '新建术语',
        titleEdit: '编辑术语',
        description: '术语与别名会用于术语匹配、导入与知识库绑定。',
        fields: {
          category: '所属分类',
          categoryPlaceholder: '请选择分类',
          term: '术语',
          termPlaceholder: '例如：Embedding',
          synonyms: '别名',
          synonymsHint: '一行一个别名，也支持使用英文逗号分隔。',
          synonymsPlaceholder: '例如：向量化'
        },
        actions: {
          cancel: '取消',
          submitting: '保存中...',
          create: '创建术语',
          save: '保存'
        },
        validation: {
          categoryRequired: '请选择所属分类。',
          termRequired: '请输入术语名称。'
        }
      },
      termImport: {
        title: '导入术语',
        description: '上传 CSV 文件，导入结果会展示成功数量与逐行错误。',
        actions: {
          cancel: '取消',
          importing: '导入中...',
          submit: '确认导入',
          downloadTemplate: '下载导入模板'
        },
        upload: {
          replaceFile: '点击重新选择文件',
          selectFile: '点击上传文件',
          hint: '支持 .csv / .xlsx 格式'
        },
        template: {
          prompt: '没有模板？'
        },
        result: {
          importedCount: '成功导入 {{count}} 条',
          noErrors: '未返回行级错误。'
        },
        errorFallback: '导入失败，请稍后重试。'
      },
      termItem: {
        noSynonyms: '暂无别名',
        actions: {
          edit: '编辑',
          delete: '删除'
        }
      }
    },
    knowledgeBase: {
      label: '知识库',
      summary: '管理知识库、上传文档并进行检索测试。',
      title: '知识库',
      list: {
        title: '知识库',
        description: '管理知识库、上传文档并测试搜索效果。',
        create: '创建知识库',
        searchLabel: '搜索',
        searchPlaceholder: '知识库名称...',
        statusLabel: '状态',
        statuses: {
          all: '全部',
          active: '活跃',
          processing: '处理中',
          disabled: '已禁用'
        },
        emptyTitle: '暂无知识库',
        emptyDescription: '点击“创建知识库”开始使用。',
        deleteTitle: '删除知识库',
        deleteDescription: '确定要删除“{{name}}”吗？'
      },
      detail: {
        eyebrow: '知识库',
        fallbackTitle: '知识库',
        backToList: '返回知识库列表',
        updateSuccess: '知识库已更新',
        updateFailed: '知识库更新失败',
        sections: {
          overview: '概览',
          documents: '文档管理',
          glossary: '术语绑定',
          search: '搜索测试'
        },
        glossaryBindingDescription: '为当前知识库选择需要参与术语匹配的分类，保存时会覆盖现有绑定。',
        glossarySave: '保存绑定',
        glossarySaving: '保存中...',
        glossaryDescriptionFallback: '未填写分类说明',
        glossaryRefreshFailed: '最新状态刷新失败，当前显示的是已加载结果。',
        glossaryEmptyTitle: '暂无术语分类',
        glossaryEmptyDescription: '请先到术语库模块创建分类，再回到这里完成知识库绑定。',
        segmentEmptyTitle: '暂无分段数据',
        folderEmptyTitle: '暂无文件夹'
      }
    },
    modelMonitoring: {
      label: '模型监控',
      summary: '按模型卡片维度查看用量统计和调用错误。',
      eyebrow: 'AI 模型中心',
      title: '模型监控',
      sections: {
        overview: '概览',
        errors: '调用错误'
      },
      overview: {
        emptyTitle: '暂无监控数据',
        emptyDescription: '当模型开始接收请求后，监控数据将会出现在这里。',
        metrics: {
          totalRequests: '总请求量',
          totalTokens: '总 Token',
          averageLatency: '平均延迟',
          totalErrors: '总错误数'
        },
        hints: {
          totalRequests: '所有模型累计请求数',
          totalTokens: '输入 + 输出 Token 总量',
          averageLatency: '按请求量加权的平均响应时间',
          totalErrors: '所有模型累计错误次数'
        },
        card: {
          requests: '{{value}} 请求',
          tokens: '{{value}} Token',
          errors: '{{value}} 错误'
        }
      },
      usage: {
        viewToggle: {
          list: '列表',
          card: '卡片'
        },
        filters: {
          model: '模型',
          allModels: '全部模型',
          loading: '加载中...',
          startTime: '开始时间',
          endTime: '结束时间'
        },
        metrics: {
          totalRequests: '总请求量',
          totalTokens: '总 Token',
          averageLatency: '平均延迟',
          totalErrors: '总错误'
        },
        table: {
          headers: {
            modelName: '模型名称',
            requests: '请求量',
            inputTokens: '输入 Token',
            outputTokens: '输出 Token',
            averageLatency: '平均延迟',
            errorRate: '错误率'
          }
        },
        detail: {
          drawerTitle: '请求明细',
          filters: {
            startTime: '开始时间',
            endTime: '结束时间'
          },
          table: {
            headers: {
              startedAt: '开始时间',
              requestId: '请求 ID',
              capability: '能力',
              attempts: '尝试数',
              inputTokens: '输入 Token',
              outputTokens: '输出 Token',
              latency: '总耗时',
              result: '结果'
            },
            status: {
              success: '成功',
              failure: '失败'
            }
          },
          empty: {
            title: '暂无请求明细',
            description: '该时间范围内没有找到请求记录。'
          }
        },
        empty: {
          title: '暂无用量数据',
          description: '当模型开始接收请求后，用量数据将出现在这里。'
        },
        error: '加载用量数据失败，请重试。',
        grid: {
          empty: {
            title: '暂无监控数据',
            description: '当模型开始接收请求后，监控数据将出现在这里。'
          },
          error: '加载监控数据失败。',
          requests: '{{value}} 请求',
          errors: '{{value}} 错误'
        }
      },
      errors: {
        filters: {
          model: '模型',
          allModels: '全部模型',
          loading: '加载中...',
          errorCode: '错误码',
          allErrorCodes: '全部错误码',
          startTime: '开始时间',
          endTime: '结束时间'
        },
        errorCodeLabels: {
          UPSTREAM_FAILURE: '上游调用失败',
          upstream_error: '上游错误',
          provider_timeout: '提供商超时',
          provider_rate_limited: '速率限制',
          provider_auth_failed: '鉴权失败',
          unsupported_capability: '不支持的能力',
          validation_error: '请求校验失败',
          session_closed: '会话已关闭'
        },
        table: {
          headers: {
            time: '时间',
            model: '模型',
            errorCode: '错误码',
            capability: '能力',
            errorMessage: '错误消息'
          },
          uncategorized: '未分类错误'
        },
        detail: {
          errorMessage: '错误消息',
          instance: '实例',
          capability: '能力',
          duration: '请求耗时'
        },
        empty: {
          title: '暂无错误记录',
          description: '没有找到符合条件的调用错误，这是一个好消息！'
        },
        error: '加载错误记录失败，请重试。'
      }
    },
    costAnalysis: {
      label: '成本分析',
      summary: '分析模型调用成本、预算和告警。',
      eyebrow: '成本分析',
      title: '成本分析',
      sections: {
        overview: '成本概览',
        budgets: '预算管理',
        alerts: '成本告警'
      },
      overview: {
        totalSpend: '总花费',
        totalRequests: '总请求量',
        totalTokens: '总 Token',
        avgLatency: '平均延迟',
        costTrend: '成本趋势',
        modelDistribution: '模型分布',
        topModels: 'Top 模型',
        error: '加载成本概览失败，请重试。'
      },
      budgets: {
        title: '预算管理',
        description: '设置和管理模型调用预算。',
        createBudget: '创建预算',
        emptyTitle: '暂无预算',
        emptyDescription: '点击"创建预算"开始设置预算限制。',
        error: '加载预算失败，请重试。',
        scope: {
          global: '全范围',
          model: '模型',
          agent: 'Agent',
          user: '用户'
        },
        form: {
          title: '新建预算',
          description: '设置预算限制和告警阈值',
          scopeType: '范围类型',
          scopeKey: '模型',
          monthlyLimit: '月度预算 (USD)',
          alertThreshold: '告警阈值 (%)',
          isEnabled: '启用'
        },
        columns: {
          name: '预算名称',
          limit: '预算上限',
          currentSpend: '当前花费',
          usage: '使用率',
          period: '周期',
          status: '状态',
          actions: '操作'
        },
        status: {
          active: '生效中',
          exceeded: '已超支',
          inactive: '未生效'
        },
        actions: {
          edit: '编辑',
          delete: '删除',
          create: '创建',
          cancel: '取消',
          creating: '创建中...'
        }
      },
      alerts: {
        title: '成本告警',
        description: '配置成本告警规则，当花费超过阈值时通知。',
        createAlert: '创建告警',
        evaluate: '评估告警',
        acknowledge: '确认',
        emptyTitle: '暂无告警',
        emptyDescription: '当前没有触发的告警。',
        error: '加载告警失败，请重试。',
        typeLabel: {
          threshold: '阈值告警',
          exceeded: '超支'
        },
        statusLabel: {
          acknowledged: '已确认',
          pending: '待处理'
        },
        columns: {
          name: '告警名称',
          threshold: '阈值',
          type: '类型',
          status: '状态',
          lastTriggered: '最近触发',
          actions: '操作'
        },
        tableHeaders: {
          type: '类型',
          scope: '范围',
          currentSpend: '当前花费',
          threshold: '阈值',
          triggeredAt: '触发时间',
          status: '状态',
          actions: '操作'
        },
        type: {
          absolute: '绝对值',
          percentage: '百分比'
        },
        status: {
          active: '启用',
          inactive: '停用'
        },
        actions: {
          edit: '编辑',
          delete: '删除'
        }
      }
    },
    observability: {
      label: '可观测性',
      summary: '查看系统可观测性数据，包括链路追踪和指标。',
      eyebrow: '可观测性',
      title: '可观测性',
      sections: {
        traces: '链路追踪'
      },
      traces: {
        title: '链路追踪',
        description: '查看系统请求链路追踪信息。',
        searchPlaceholder: '搜索 Trace ID...',
        emptyTitle: '暂无追踪数据',
        emptyDescription: '系统开始处理请求后，追踪数据将出现在这里。',
        loadError: '加载追踪数据失败，请重试。',
        detailLoadError: '加载追踪详情失败，请重试。',
        timeRange: {
          '24h': '24小时',
          '7d': '7 天',
          '30d': '30 天',
        },
        metrics: {
          totalTraces: '总 Trace 数',
          avgLatency: '平均延迟',
          totalTokens: '总 Token',
          errorCount: '错误数',
        },
        columns: {
          traceId: 'Trace ID',
          agent: 'Agent',
          operation: '操作',
          status: '状态',
          duration: '耗时',
          tokens: 'Token',
          spanCount: 'Span 数',
          startTime: '开始时间',
          services: '服务数',
        },
        status: {
          success: '成功',
          error: '失败',
        },
        detail: {
          title: '追踪详情',
          backToList: '← 返回列表',
          waterfall: '调用链路 Waterfall',
          spanList: 'Span 列表',
          spanAttributes: 'Span 属性',
          collapse: '收起',
          expand: '详情',
          noSpanData: '无 Span 数据',
          timeline: '时间线',
          spans: '跨度',
          tags: '标签',
          columns: {
            kind: '类型',
            name: '名称',
            status: '状态',
            duration: '耗时',
            actions: '操作',
          },
        },
      }
    },
    memory: {
      label: '记忆管理',
      summary: '管理 AI Agent 的记忆存储。',
      eyebrow: '记忆管理',
      title: '记忆管理',
      sections: {
        memories: '记忆列表'
      },
      list: {
        title: '记忆列表',
        description: '管理 Agent 的长期记忆和上下文。',
        searchPlaceholder: '搜索记忆...',
        emptyTitle: '暂无记忆数据',
        emptyDescription: 'Agent 开始交互后，记忆数据将出现在这里。',
        filterAll: '全部',
        typeLabels: {
          episodic: '对话摘要',
          semantic: '事实知识',
          procedural: '行为偏好'
        },
        accessCount: '访问 {{count}} 次',
        relevance: '相关度 {{score}}',
        deactivate: '停用',
        consolidate: '整合记忆',
        prevPage: '上一页',
        nextPage: '下一页',
        pageInfo: '第 {{page}} 页 / 共 {{total}} 页',
        metrics: {
          totalActive: '总记忆数',
          episodic: '对话摘要',
          semantic: '事实知识',
          procedural: '行为偏好'
        },
        loadError: '加载记忆列表失败，请刷新重试。',
        filterLabel: '按类型筛选记忆'
      }
    },
    evaluation: {
      label: '评估管理',
      summary: '管理评估数据集和评估运行。',
      eyebrow: '评估管理',
      title: '评估管理',
      sections: {
        datasets: '数据集',
        runs: '评估运行'
      },
      datasets: {
        title: '数据集',
        description: '管理评估数据集，用于测试和评估模型性能。',
        createDataset: '创建数据集',
        emptyTitle: '暂无数据集',
        emptyDescription: '点击"创建数据集"开始使用。',
        columns: {
          name: '数据集名称',
          description: '描述',
          itemCount: '数据条数',
          createdAt: '创建时间',
          actions: '操作'
        },
        actions: {
          view: '查看',
          edit: '编辑',
          delete: '删除'
        }
      },
      runs: {
        title: '评估运行',
        description: '查看评估运行记录和结果。',
        emptyTitle: '暂无评估运行',
        emptyDescription: '开始评估后，运行记录将出现在这里。',
        columns: {
          runId: '运行 ID',
          dataset: '数据集',
          model: '模型',
          status: '状态',
          score: '得分',
          startedAt: '开始时间',
          completedAt: '完成时间'
        },
        status: {
          pending: '待运行',
          running: '运行中',
          completed: '已完成',
          failed: '失败'
        }
      }
    },
    userManagement: {
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
    }
  }
} as const;
