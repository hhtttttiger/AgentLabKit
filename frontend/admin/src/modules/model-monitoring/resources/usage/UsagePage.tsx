import { UsagePageView } from './UsagePageView';
import { useUsagePageState } from './useUsagePageState';

export function UsagePage() {
  const state = useUsagePageState();
  return <UsagePageView state={state} />;
}
