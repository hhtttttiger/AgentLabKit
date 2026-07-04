import { ModelsPageView } from './ModelCardsPageView';
import { useModelsPageState } from './useModelCardsPageState';

export function ModelsPage() {
  const state = useModelsPageState();
  return <ModelsPageView state={state} />;
}
