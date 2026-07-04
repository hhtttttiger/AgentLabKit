/**
 * AI Chat Module - Layout
 */

import { Outlet } from 'react-router-dom';

export function AiChatLayout() {
  return (
    <div className="flex h-full min-h-0 flex-col overflow-hidden">
      <Outlet />
    </div>
  );
}
