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
    backToList: 'Back to datasets',
    fallbackTitle: 'Dataset #{{id}}',
    caseCount: '{{count}} cases',
    casesTitle: 'Test cases',
    namePlaceholder: 'Dataset name',
    descriptionPlaceholder: 'Description (optional)',
    caseInputPlaceholder: 'Question or input',
    caseExpectedPlaceholder: 'Expected output (optional)',
    addCase: 'Add',
    addingCase: 'Adding…',
    emptyTitle: 'No datasets yet',
    emptyDescription: 'Datasets let you evaluate Agent behavior consistently. Save useful or failing Runs to a dataset from a Run detail page, or create one manually.',
    columns: {
      name: 'Dataset name',
      description: 'Description',
      itemCount: 'Item count',
      input: 'Input',
      expected: 'Expected output',
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
    newEvaluation: 'New Evaluation',
    selectConfig: 'Choose a saved configuration…',
    runSavedConfig: 'Run saved configuration',
    savedConfigs: 'Saved configurations',
    compareRolesHint: 'Assign compare roles (selection order carries no meaning).',
    compareCta: 'Compare baseline vs candidate',
    startError: 'Failed to start the evaluation. Please try again.',
    noDatasetsPrereq: 'No datasets yet. Add a Run to a dataset from its detail page (Add to Dataset), or create one manually, then start an evaluation.',
    formDescription: 'Choose a dataset, an Agent, and metrics, then run the evaluation. The configuration is saved so you can run it again.',
    evaluateDataset: 'Evaluate Dataset',
    runEvaluation: 'Run Evaluation',
    preparing: 'Preparing…',
    selectDataset: 'Select a dataset…',
    selectAgent: 'Select an Agent…',
    datasetOption: '{{name}} ({{count}} cases)',
    metrics: 'Metrics',
    metric: {
      answer_relevance: 'Answer relevance',
      faithfulness: 'Faithfulness',
      context_relevance: 'Context relevance'
    },
    evidence: {
      title: 'Retrieval evidence',
      available: '{{attempts}} retrieval attempt(s) · {{successful}} successful · {{contexts}} context(s) used',
      noRetrieval: 'No retrieval occurred for this run',
      unavailable: 'Retrieval evidence unavailable',
      openRun: 'Open Run',
      inspectTrace: 'Inspect Trace'
    },
    ragPipelinePlaceholder: 'e.g. kb-123',
    judgePlaceholder: 'Leave empty to use the default model',
    judgeHint: 'Model binding key used by the LLM judge',
    columns: {
      runId: 'Run ID',
      run: 'Run',
      agent: 'Agent',
      dataset: 'Dataset',
      model: 'Model',
      status: 'Status',
      score: 'Score',
      avgScore: 'Avg score',
      caseCount: 'Cases',
      errorCount: 'Errors',
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
