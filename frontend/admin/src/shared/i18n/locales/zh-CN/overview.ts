export const overview = {
  greeting: '{{time}}好',
  subtitle: '你想做什么？',
  actions: {
    testAgent: '测试 Agent',
    createAgent: '创建 Agent',
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
    evaluationUnavailable: '当前暂无评估数据。',
    costComingSoon: '即将推出',
  },
  recentRuns: {
    title: '最近运行',
    empty: '暂无运行记录。测试或执行 Agent 后，运行记录将显示在此处。',
    openPlayground: '打开 Playground',
    viewAll: '查看全部运行',
  },
  needsAttention: {
    title: '需要关注',
    empty: '未检测到问题',
  },
} as const;
