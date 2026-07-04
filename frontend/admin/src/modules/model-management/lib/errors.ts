export function translateCatalogError(message: string): string {
  if (message.includes('ConnectionProfileKeyMismatch')) return 'modules.modelManagement.errors.connectionProfileKeyMismatch';
  if (message.includes('ModelKeyMismatch')) return 'modules.modelManagement.errors.modelKeyMismatch';
  if (message.includes('InstanceKeyMismatch')) return 'modules.modelManagement.errors.instanceKeyMismatch';
  if (message.includes('BindingKeyMismatch')) return 'modules.modelManagement.errors.bindingKeyMismatch';
  if (message.includes('UnsupportedProvider')) return 'modules.modelManagement.errors.unsupportedProvider';
  if (message.includes('UnsupportedScene')) return 'modules.modelManagement.errors.unsupportedScene';
  if (message.includes('InvalidJsonKind')) return 'modules.modelManagement.errors.invalidJsonKind';
  if (message.includes('InvalidJson')) return 'modules.modelManagement.errors.invalidJson';
  if (message.includes('InUse')) return 'modules.modelManagement.errors.inUse';
  if (message.includes('AlreadyExists')) return 'modules.modelManagement.errors.alreadyExists';
  if (message.includes('NotFound')) return 'modules.modelManagement.errors.notFound';
  return message;
}
