export const overview = {
  greeting: '{{time}}好',
  timeOfDay: {
    morning: '早上',
    afternoon: '下午',
    evening: '晚上',
  },
  subtitle: '你想做什么？',
  actions: {
    testAgent: '测试 Agent',
    createAgent: '创建 Agent',
  },
  guidance: {
    title: '创建你的第一个 Agent',
    description: '创建 Agent，配置模型，发布后即可测试真实运行。',
    cta: '创建 Agent',
    addKnowledge: '添加知识库',
    exploreEvaluation: '了解评估',
  },
  metrics: {
    agents: 'Agents',
    runs: '运行次数',
    evaluation: '评估',
    cost: '成本',
    noData: '暂无数据',
    noRuns: '暂无运行',
    totalRuns: '总运行次数',
    manageAgents: '管理 Agents',
    evaluationHint: '用数据集评估 Agent 行为',
    costComingSoon: '即将推出',
  },
  recentRuns: {
    title: '最近运行',
    empty: '暂无运行记录。测试或执行 Agent 后，运行记录将显示在此处。',
    openPlayground: '打开 Playground',
    viewAll: '查看全部运行',
  },
} as const;
