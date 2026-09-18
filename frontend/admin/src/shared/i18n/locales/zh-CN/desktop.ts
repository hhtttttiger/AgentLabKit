export const desktop = {
  brandSubtitle: 'Agent 工程工作台',
  nav: { home: '首页', sessions: '会话', runs: '运行记录', datasets: '数据集', evaluations: '评估', knowledge: '知识库', settings: '设置' },
  groups: { workspace: '工作区', work: '工作', engineering: '工程', context: '上下文' },
  home: {
    kicker: 'Agent 工程工作区', lede: '一个用于运行、检查 Agent 工作，并将其沉淀为可复用案例的工作台。', newSession: '新建会话',
    workspace: '工作区', chooseProject: '选择项目', openProjectHint: '打开本地项目，为 Agent 提供真实上下文。', local: '本地', openProject: '打开项目', changeProject: '更换',
    activity: '活动', recentRuns: '最近运行', viewAll: '查看全部', loadingRuns: '正在加载运行记录…', noRuns: '暂无运行记录。下一次 Agent 运行会显示在这里。',
    assets: '资源', workspaceAssets: '工作区', datasets: '数据集', collections: '{{count}} 个集合', evaluations: '评估', reviewResults: '查看结果', knowledge: '知识库', browseSources: '浏览来源',
    footer: '运行、Trace、检索事实和评估结果仍由各自模块负责。', timeUnavailable: '时间不可用', nativeAgent: 'Native Agent',
  },
  session: {
    runWork: '运行工作', newSession: '新建会话', description: '在本地项目中给 Agent 一个真实任务。', running: '运行中', completed: '已完成', ready: '就绪', project: '项目', noProject: '未选择项目', chooseDirectory: '选择一个本地目录开始。', change: '更换', open: '打开项目', task: '你想让 Agent 做什么？', taskPlaceholder: '修复失败的评估测试…', agent: 'Agent', loadingAgents: '正在加载 Agent…', selectAgent: '选择 Agent', context: '上下文', workingDirectory: '工作目录', selectProject: '请先选择项目', run: '运行', liveExecution: '实时执行', working: 'Agent 正在工作…', runComplete: '运行完成', readyWhen: '准备就绪', waiting: '等待运行', timelineHint: '执行时间线会显示在这里。', output: '输出', inspectRun: '查看运行', started: '已开始', tool: '工具', toolCompleted: '工具已完成', unknownTool: '未知工具', completedDetail: '运行成功完成', executionFailed: '执行失败', runtimeReady: 'Agent Runtime 已就绪', nativeNotConfigured: 'Native Agent 尚未配置。请先配置模型提供商，再开始会话。', openModelSettings: '打开模型设置', agentExecutionFailed: 'Agent 执行失败。',
  },
  sessions: { kicker: '工作', title: '会话', description: '按发生时间查看交互式 Agent 工作。', runs: '{{count}} 次运行', loading: '正在加载会话…', error: '无法加载会话。', empty: '暂无会话。开始一次 Agent 运行后会显示在这里。', recent: '最近', nativeAgentRun: 'Native Agent 运行', timeUnavailable: '时间不可用' },
  settings: {
    models: '设置 / 模型', title: '模型设置', description: '配置此 Desktop 工作区中 Native Agent 使用的默认模型。', defaultModel: '默认模型', defaultDescription: '此设置会应用到新的 Native Agent 会话。Codex 使用自己的配置。', provider: '提供商', providerHint: '这里只显示当前 Desktop Runtime 已支持的提供商。', openaiCompatible: 'OpenAI 兼容', anthropic: 'Anthropic', baseUrl: 'Base URL', baseUrlHint: '连接兼容服务时可使用 OpenAI 兼容端点。', apiKey: 'API Key', apiKeyConfiguredHint: '已配置 Key。留空则保留当前 Key。', apiKeyMissingHint: 'Key 会保存在现有的 Desktop 本地配置中。', apiKeyEnvironmentHint: '此值由环境变量提供，不会在这里显示。', configuredPlaceholder: '已配置 — 输入新 Key 可替换', enterKey: '输入 API Key', clearKey: '清除已保存的 Key', keepKey: '保留当前 Key', model: '模型', connection: '连接', connectionHint: '测试当前草稿配置，不会保存。', connected: '已连接', notTested: '未测试', environmentOverride: '环境变量覆盖', saved: '模型设置已保存，新会话将使用此配置。', testSuccess: '连接成功，提供商已接受此配置。', loadFailed: '无法加载模型设置。', test: '测试连接', saving: '保存中…', save: '保存', show: '显示', hide: '隐藏', authFailed: '认证失败，请检查 API Key。', endpointFailed: '无法连接到提供商端点。', modelFailed: '无法使用当前配置的模型。',
  },
} as const;
