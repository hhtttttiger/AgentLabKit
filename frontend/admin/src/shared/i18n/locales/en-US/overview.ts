export const overview = {
  greeting: 'Good {{time}}',
  subtitle: 'What do you want to do?',
  actions: {
    testAgent: 'Test an Agent',
    createAgent: 'Create Agent',
  },
  guidance: {
    title: 'Build your first Agent',
    description: 'Create an Agent, configure a model, publish it, and test a real run.',
    cta: 'Create Agent',
    addKnowledge: 'Add Knowledge',
    exploreEvaluation: 'Explore Evaluation',
  },
  metrics: {
    agents: 'Agents',
    runs: 'Runs',
    evaluation: 'Evaluation',
    cost: 'Cost',
    noData: 'No data yet',
    noRuns: 'No runs yet',
    totalRuns: 'Total runs',
    manageAgents: 'Manage agents',
    evaluationHint: 'Evaluate Agent behavior against datasets',
    costComingSoon: 'Coming soon',
  },
  recentRuns: {
    title: 'Recent Runs',
    empty: 'No runs yet. Runs will appear here after you test or execute an Agent.',
    openPlayground: 'Open Playground',
    viewAll: 'View all runs',
  },
} as const;
