import { useEffect } from 'react';
import { useBlocker } from 'react-router-dom';

export function useUnsavedChangesPrompt(when: boolean, message: string) {
  const blocker = useBlocker(when);

  useEffect(() => {
    if (blocker.state !== 'blocked') {
      return;
    }

    if (window.confirm(message)) {
      blocker.proceed();
    } else {
      blocker.reset();
    }
  }, [blocker, message]);

  useEffect(() => {
    if (!when) {
      return;
    }

    const handler = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = message;
      return message;
    };

    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [when, message]);
}
