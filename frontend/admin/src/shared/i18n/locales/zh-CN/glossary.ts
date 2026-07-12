// Auto-generated — do not edit manually
export const glossary = {
      label: '术语库',
      summary: '统一维护术语分类、术语条目并绑定到知识库。',
      eyebrow: '知识增强',
      title: '术语库',
      sections: {
        list: '术语管理'
      },
      list: {
        title: '术语库',
        description: '管理术语分类、术语条目与知识库术语素材。',
        newCategory: '新建分类',
        searchLabel: '搜索',
        searchPlaceholder: '分类名称...',
        emptyTitle: '暂无术语分类',
        emptyDescription: '点击"新建分类"开始使用。',
        deleteTitle: '删除分类',
        deleteDescription: '确定删除分类"{{name}}"吗？',
        confirmDelete: '删除分类'
      },
      categoryForm: {
        titleCreate: '新建分类',
        titleEdit: '编辑分类',
        description: '分类用于组织术语条目，并作为知识库绑定的最小单位。',
        fields: {
          name: '分类名称',
          namePlaceholder: '例如：RAG',
          description: '分类说明',
          descriptionPlaceholder: '可选，用于说明这组术语的适用场景。'
        },
        actions: {
          cancel: '取消',
          submitting: '保存中...',
          create: '创建分类',
          save: '保存'
        },
        validation: {
          nameRequired: '请输入分类名称。'
        }
      },
      category: {
        fallbackTitle: '术语分类',
        eyebrow: '术语库',
        backToList: '返回术语库',
        sections: {
          terms: '术语列表'
        }
      },
      categoryCard: {
        menuLabel: '分类操作',
        actions: {
          edit: '编辑',
          delete: '删除'
        }
      },
      categoryItem: {
        descriptionFallback: '未填写分类说明',
        actions: {
          edit: '编辑',
          delete: '删除'
        }
      },
      termsTab: {
        columns: {
          term: '术语',
          synonyms: '别名',
          createdAt: '创建时间',
          actions: '操作'
        },
        rowActions: {
          edit: '编辑',
          delete: '删除'
        },
        toolbar: {
          import: '导入术语',
          create: '新建术语',
          searchLabel: '搜索',
          searchPlaceholder: '搜索术语或别名...'
        },
        emptyTitle: '暂无术语',
        emptyDescription: '当前分类还没有术语，可以手动新增或通过导入补齐。',
        emptyAction: '添加术语',
        deleteTitle: '删除术语',
        deleteDescription: '确定删除术语"{{name}}"吗？',
        confirmDelete: '删除术语'
      },
      termForm: {
        titleCreate: '新建术语',
        titleEdit: '编辑术语',
        description: '术语与别名会用于术语匹配、导入与知识库绑定。',
        fields: {
          category: '所属分类',
          categoryPlaceholder: '请选择分类',
          term: '术语',
          termPlaceholder: '例如：Embedding',
          synonyms: '别名',
          synonymsHint: '一行一个别名，也支持使用英文逗号分隔。',
          synonymsPlaceholder: '例如：向量化'
        },
        actions: {
          cancel: '取消',
          submitting: '保存中...',
          create: '创建术语',
          save: '保存'
        },
        validation: {
          categoryRequired: '请选择所属分类。',
          termRequired: '请输入术语名称。'
        }
      },
      termImport: {
        title: '导入术语',
        description: '上传 CSV 文件，导入结果会展示成功数量与逐行错误。',
        actions: {
          cancel: '取消',
          importing: '导入中...',
          submit: '确认导入',
          downloadTemplate: '下载导入模板'
        },
        upload: {
          replaceFile: '点击重新选择文件',
          selectFile: '点击上传文件',
          hint: '支持 .csv / .xlsx 格式'
        },
        template: {
          prompt: '没有模板？'
        },
        result: {
          importedCount: '成功导入 {{count}} 条',
          noErrors: '未返回行级错误。'
        },
        errorFallback: '导入失败，请稍后重试。'
      },
      termItem: {
        noSynonyms: '暂无别名',
        actions: {
          edit: '编辑',
          delete: '删除'
        }
      }
    } as const;
