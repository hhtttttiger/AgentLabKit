// Auto-generated — do not edit manually
export const evaluation = {
  label: 'Evaluation',
  summary: 'Manage evaluation datasets and runs.',
  eyebrow: 'Evaluation',
  title: 'Evaluation',
  sections: {
    overview: 'Overview',
    datasets: 'Datasets',
    runs: 'Evaluation runs'
  },
  overview: {
    title: 'Evaluation Overview',
    description: 'Evaluate an Agent against a dataset to measure behavior and compare improvements.',
    datasets: 'Datasets',
    totalRuns: 'Total Runs',
    avgScore: 'Avg Score',
    recentRuns: 'Recent Runs',
    noDatasets: 'No datasets yet. Save useful or failing Runs to a dataset from a Run detail page, then evaluate an Agent against it.',
    openDatasets: 'Open Datasets'
  },
  datasets: {
    title: 'Datasets',
    description: 'Evaluate Agent behavior against the same examples consistently.',
    createDataset: 'Create dataset',
    emptyTitle: 'No datasets yet',
    emptyDescription: 'Datasets let you evaluate Agent behavior consistently. Save useful or failing Runs to a dataset from a Run detail page, or create one manually.',
    columns: {
      name: 'Dataset name',
      description: 'Description',
      itemCount: 'Item count',
      createdAt: 'Created at',
      actions: 'Actions'
    },
    actions: {
      view: 'View',
      edit: 'Edit',
      delete: 'Delete'
    }
  },
  form: {
    advanced: 'Advanced',
    configurationName: 'Configuration Name',
    targetMode: 'Target Mode',
    judgeBinding: 'Judge Binding (optional)',
    dataset: 'Dataset',
    agent: 'Agent',
    ragPipeline: 'RAG Pipeline',
  },
  runs: {
    title: 'Evaluation runs',
    description: 'View evaluation run records and results.',
    emptyTitle: 'No evaluation runs',
    emptyDescription: 'Run records will appear here once evaluation starts.',
    columns: {
      runId: 'Run ID',
      dataset: 'Dataset',
      model: 'Model',
      status: 'Status',
      score: 'Score',
      startedAt: 'Started at',
      createdAt: 'Created at',
      completedAt: 'Completed at'
    },
    status: {
      pending: 'Pending',
      running: 'Running',
      completed: 'Completed',
      failed: 'Failed'
    }
  }
} as const;
