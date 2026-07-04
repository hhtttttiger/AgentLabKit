import { ModelInstancesPageView } from './ModelInstancesPageView';
import { useModelInstancesPageState } from './useModelInstancesPageState';

export function ModelInstancesPage() {
  const state = useModelInstancesPageState();
  return <ModelInstancesPageView state={state} />;
}
