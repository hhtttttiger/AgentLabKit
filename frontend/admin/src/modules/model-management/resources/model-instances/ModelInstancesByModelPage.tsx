import { ModelInstancesByModelPageView } from './ModelInstancesByModelPageView';
import { useModelInstancesByModelPageState } from './useModelInstancesByModelPageState';

export function ModelInstancesByModelPage() {
  const state = useModelInstancesByModelPageState();
  return <ModelInstancesByModelPageView state={state} />;
}
