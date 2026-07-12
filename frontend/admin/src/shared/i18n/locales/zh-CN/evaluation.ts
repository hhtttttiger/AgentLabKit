// Auto-generated — do not edit manually
export const evaluation = {
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
    } as const;
