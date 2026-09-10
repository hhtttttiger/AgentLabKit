// Auto-generated — do not edit manually
export const evaluation = {
      label: '评估管理',
      summary: '管理评估数据集和评估运行。',
      eyebrow: '评估管理',
      title: '评估管理',
      sections: {
        overview: '概览',
        datasets: '数据集',
        runs: '评估运行'
      },
      overview: {
        title: '评估概览',
        description: '用数据集评估 Agent 行为，并对比改进效果。',
        datasets: '数据集',
        totalRuns: '总运行数',
        avgScore: '平均分',
        recentRuns: '最近运行',
        noDatasets: '暂无数据集。可在运行详情页将有价值或失败的运行保存为数据集用例，再对 Agent 运行评估。',
        openDatasets: '打开数据集'
      },
      datasets: {
        title: '数据集',
        description: '用示例用例一致地评估 Agent 行为。',
        createDataset: '创建数据集',
        backToList: '返回数据集',
        fallbackTitle: '数据集 #{{id}}',
        caseCount: '{{count}} 条用例',
        casesTitle: '测试用例',
        namePlaceholder: '数据集名称',
        descriptionPlaceholder: '描述（可选）',
        caseInputPlaceholder: '问题或输入',
        caseExpectedPlaceholder: '期望输出（可选）',
        addCase: '添加',
        addingCase: '添加中…',
        emptyTitle: '暂无数据集',
        emptyDescription: '数据集用于以相同用例一致地评估 Agent 行为。可在运行详情页选择"添加到数据集"，也可以手动创建。',
        columns: {
          name: '数据集名称',
          description: '描述',
          itemCount: '数据条数',
          input: '输入',
          expected: '期望输出',
          createdAt: '创建时间',
          actions: '操作'
        },
        actions: {
          view: '查看',
          edit: '编辑',
          delete: '删除'
        }
      },
      form: {
        advanced: '高级设置',
        configurationName: '配置名称',
        targetMode: '目标模式',
        judgeBinding: 'Judge 模型绑定（可选）',
        dataset: '数据集',
        agent: 'Agent',
        ragPipeline: 'RAG Pipeline',
      },
      runs: {
        title: '评估运行',
        description: '查看评估运行记录和结果。',
        emptyTitle: '暂无评估运行',
        emptyDescription: '开始评估后，运行记录将出现在这里。',
        newEvaluation: '新建评估',
        selectConfig: '选择已保存配置…',
        runSavedConfig: '运行已保存配置',
        savedConfigs: '已保存配置',
        compareRolesHint: '指定对比角色（勾选顺序不代表语义）。',
        compareCta: '对比 Baseline 与 Candidate',
        startError: '无法启动评估，请重试。',
        noDatasetsPrereq: '暂无数据集。可先在运行详情页选择"添加到数据集"，或手动创建数据集，然后再开始评估。',
        formDescription: '选择数据集、Agent 和指标，然后运行评估。配置会保存下来供后续 Run Again 使用。',
        evaluateDataset: '评估数据集',
        runEvaluation: '运行评估',
        preparing: '运行准备中…',
        selectDataset: '选择数据集…',
        selectAgent: '选择 Agent…',
        datasetOption: '{{name}}（{{count}} 条用例）',
        metrics: '评估指标',
        metric: {
          answer_relevance: '答案相关性',
          faithfulness: '忠实度',
          context_relevance: '上下文相关性'
        },
        evidence: {
          title: '检索证据',
          available: '检索 {{attempts}} 次 · 成功 {{successful}} 次 · 使用 {{contexts}} 条上下文',
          noRetrieval: '本次运行没有发生检索',
          unavailable: '检索证据不可用',
          openRun: '查看运行',
          inspectTrace: '查看 Trace'
        },
        ragPipelinePlaceholder: '例如：kb-123',
        judgePlaceholder: '留空则使用默认模型',
        judgeHint: 'LLM-as-Judge 使用的模型绑定 key',
        columns: {
          runId: '运行 ID',
          run: '运行',
          agent: 'Agent',
          dataset: '数据集',
          model: '模型',
          status: '状态',
          score: '得分',
          avgScore: '平均分',
          caseCount: '用例数',
          errorCount: '错误数',
          startedAt: '开始时间',
          createdAt: '创建时间',
          completedAt: '完成时间'
        },
        status: {
          pending: '待运行',
          running: '运行中',
          completed: '已完成',
          failed: '失败'
        }
      }
    } as const;
