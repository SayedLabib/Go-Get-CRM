import React from 'react';
import { Mail, RotateCcw } from 'lucide-react';

// Small read-only badges surfacing narrow JSONB breadcrumbs on a task:
// extra.overdue_reschedule_history (auto-reschedule) and extra.client_emailed
// (completion-time client notification). Shared by Tasks.jsx's task rows and
// TaskStatusUpdateModal so both show the same flags.
export default function TaskFlags({ task }) {
  const rescheduled = task.extra?.overdue_reschedule_history?.length > 0
    || task.overdue_reschedule_history?.length > 0;
  const emailed = task.extra?.client_emailed || task.client_emailed;
  if (!rescheduled && !emailed) return null;
  return (
    <>
      {rescheduled && (
        <span
          className="flex items-center gap-1 text-xs text-amber-700 bg-amber-50 border border-amber-200 rounded-full px-2 py-0.5"
          title="This task was automatically rescheduled after going overdue"
        >
          <RotateCcw className="w-3 h-3" />Auto-Rescheduled
        </span>
      )}
      {emailed && (
        <span className="flex items-center gap-1 text-xs text-green-700 bg-green-50 border border-green-200 rounded-full px-2 py-0.5">
          <Mail className="w-3 h-3" />Emailed
        </span>
      )}
    </>
  );
}
