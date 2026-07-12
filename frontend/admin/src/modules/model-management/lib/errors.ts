export function translateCatalogError(message: string): string {
  if (message.includes('ConnectionProfileKeyMismatch')) return 'modelManagement:errors.connectionProfileKeyMismatch';
  if (message.includes('ModelKeyMismatch')) return 'modelManagement:errors.modelKeyMismatch';
  if (message.includes('InstanceKeyMismatch')) return 'modelManagement:errors.instanceKeyMismatch';
  if (message.includes('BindingKeyMismatch')) return 'modelManagement:errors.bindingKeyMismatch';
  if (message.includes('UnsupportedProvider')) return 'modelManagement:errors.unsupportedProvider';
  if (message.includes('UnsupportedScene')) return 'modelManagement:errors.unsupportedScene';
  if (message.includes('InvalidJsonKind')) return 'modelManagement:errors.invalidJsonKind';
  if (message.includes('InvalidJson')) return 'modelManagement:errors.invalidJson';
  if (message.includes('InUse')) return 'modelManagement:errors.inUse';
  if (message.includes('AlreadyExists')) return 'modelManagement:errors.alreadyExists';
  if (message.includes('NotFound')) return 'modelManagement:errors.notFound';
  return message;
}
