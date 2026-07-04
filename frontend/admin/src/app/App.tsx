import { AppProviders } from './providers/AppProviders';
import { AppRouter } from './router';

export function App() {
  return (
    <AppProviders>
      <AppRouter />
    </AppProviders>
  );
}
