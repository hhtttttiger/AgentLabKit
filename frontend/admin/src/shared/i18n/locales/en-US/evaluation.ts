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
    datasets: 'Datasets',
    totalRuns: 'Total Runs',
    avgScore: 'Avg Score',
    recentRuns: 'Recent Runs'
  },
  datasets: {
    title: 'Datasets',
    description: 'Manage evaluation datasets for testing and evaluating model performance.',
    createDataset: 'Create dataset',
    emptyTitle: 'No datasets',
    emptyDescription: 'Click "Create dataset" to get started.',
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
