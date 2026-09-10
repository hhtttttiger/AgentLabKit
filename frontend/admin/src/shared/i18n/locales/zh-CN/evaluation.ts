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
        emptyTitle: '暂无数据集',
        emptyDescription: '数据集用于以相同用例一致地评估 Agent 行为。可在运行详情页选择"添加到数据集"，也可以手动创建。',
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
        columns: {
          runId: '运行 ID',
          dataset: '数据集',
          model: '模型',
          status: '状态',
          score: '得分',
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
