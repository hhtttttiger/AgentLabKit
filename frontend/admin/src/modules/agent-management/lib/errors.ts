export function translateAgentError(message: string) {
  if (message.includes('agent_key_duplicate')) return '该 Agent 标识已存在，请使用其他名称。';
  if (message.includes('agent_not_found')) return '未找到该 Agent，可能已被删除。';
  if (message.includes('concurrency_conflict')) return '数据已被其他用户修改，请刷新后重试。';
  if (message.includes('version_not_found')) return '未找到该版本。';
  if (message.includes('version_not_draft')) return '仅草稿状态的版本可以发布。';
  if (message.includes('version_not_editable')) return '仅草稿和已发布版本允许编辑，已归档版本不可修改。';
  if (message.includes('draft_version_exists')) return '已存在草稿版本，请编辑现有草稿或先将其发布。';
  if (message.includes('system_prompt_required')) return 'System Prompt 不能为空。';
  if (message.includes('model_binding_key_required')) return '模型绑定不能为空。';
  if (message.includes('runtime_policy_required')) return '运行时策略不能为空，请在「高级策略配置」中填写至少一项有效策略。';
  if (message.includes('no_draft_version')) return '没有可发布的草稿版本。';
  if (message.includes('row_version_required')) return '缺少版本标记，请刷新后重试。';
  return message;
}
