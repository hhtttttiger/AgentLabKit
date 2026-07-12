// Auto-generated — do not edit manually
export const knowledgeBase = {
      label: '知识库',
      summary: '管理知识库、上传文档并进行检索测试。',
      title: '知识库',
      list: {
        title: '知识库',
        description: '管理知识库、上传文档并测试搜索效果。',
        create: '创建知识库',
        searchLabel: '搜索',
        searchPlaceholder: '知识库名称...',
        statusLabel: '状态',
        statuses: {
          all: '全部',
          active: '活跃',
          processing: '处理中',
          disabled: '已禁用'
        },
        emptyTitle: '暂无知识库',
        emptyDescription: '点击"创建知识库"开始使用。',
        deleteTitle: '删除知识库',
        deleteDescription: '确定要删除"{{name}}"吗？'
      },
      detail: {
        eyebrow: '知识库',
        fallbackTitle: '知识库',
        backToList: '返回知识库列表',
        updateSuccess: '知识库已更新',
        updateFailed: '知识库更新失败',
        sections: {
          overview: '概览',
          documents: '文档管理',
          glossary: '术语绑定',
          search: '搜索测试'
        },
        glossaryBindingDescription: '为当前知识库选择需要参与术语匹配的分类，保存时会覆盖现有绑定。',
        glossarySave: '保存绑定',
        glossarySaving: '保存中...',
        glossaryDescriptionFallback: '未填写分类说明',
        glossaryRefreshFailed: '最新状态刷新失败，当前显示的是已加载结果。',
        glossaryEmptyTitle: '暂无术语分类',
        glossaryEmptyDescription: '请先到术语库模块创建分类，再回到这里完成知识库绑定。',
        segmentEmptyTitle: '暂无分段数据',
        folderEmptyTitle: '暂无文件夹'
      }
    } as const;
