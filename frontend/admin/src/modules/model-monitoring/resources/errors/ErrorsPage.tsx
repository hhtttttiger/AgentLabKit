import { ErrorsPageView } from './ErrorsPageView';
import { useErrorsPageState } from './useErrorsPageState';

export function ErrorsPage() {
  const state = useErrorsPageState();
  return <ErrorsPageView state={state} />;
}
