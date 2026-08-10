import React, { useState } from 'react';
import { useMutation, useQueryClient, useQuery } from '@tanstack/react-query';
import { api } from '@/api/apiClient';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';
import { Textarea } from '@/components/ui/textarea';
import { Building2, Calendar, Clock, History, Pencil } from 'lucide-react';
import { toast } from 'sonner';
import { cn } from '@/lib/utils';
import TaskFlags from '@/features/tasks/components/TaskFlags';

const STATUS_OPTIONS = [
  { value: 'Not Started', color: 'bg-slate-600 hover:bg-slate-700' },
  { value: 'In Progress', color: 'bg-blue-600 hover:bg-blue-700' },
  { value: 'Blocked', color: 'bg-red-600 hover:bg-red-700' },
  { value: 'Complete', color: 'bg-green-600 hover:bg-green-700' },
];

const getStatusColor = (status) => {
  switch (status) {
    case 'Complete': return 'bg-green-100 text-green-800';
    case 'In Progress': return 'bg-blue-100 text-blue-800';
    case 'Blocked': return 'bg-red-100 text-red-800';
    default: return 'bg-gray-100 text-gray-800';
  }
};

// The focused "update this task" experience for routine status work — the
// service/frequency/dates/assignment were already set once when the task
// was created (usually auto-created from Client -> Service), so this only
// ever shows them read-only. Genuine full edits go through "Full Edit"
// (TaskFormModal) instead, which stays the create/reassign/reconfigure tool.
export default function TaskStatusUpdateModal({ task, currentUser, onClose, onFullEdit }) {
  const queryClient = useQueryClient();
  const [confirmingComplete, setConfirmingComplete] = useState(false);
  const [clientEmailed, setClientEmailed] = useState(false);
  const [clientEmailedNote, setClientEmailedNote] = useState('');
  const [hoursInput, setHoursInput] = useState(task?.actual_hours ?? '');

  const { data: clients = [] } = useQuery({ queryKey: ['clients'], queryFn: () => api.entities.Client.list() });
  const { data: users = [] } = useQuery({ queryKey: ['users'], queryFn: () => api.entities.User.list() });
  const { data: linkedFiling } = useQuery({
    queryKey: ['serviceFiling', task?.service_filing_id],
    queryFn: () => api.entities.ServiceFiling.get(task.service_filing_id),
    enabled: !!task?.service_filing_id,
  });

  const invalidateAfterSave = () => {
    queryClient.invalidateQueries({ queryKey: ['tasks'] });
    queryClient.invalidateQueries({ queryKey: ['myTasks'] });
    queryClient.invalidateQueries({ queryKey: ['teamTasks'] });
    queryClient.invalidateQueries({ queryKey: ['clientTasks'] });
    queryClient.invalidateQueries({ queryKey: ['communications'] });
    queryClient.invalidateQueries({ queryKey: ['activities'] });
  };

  const statusMutation = useMutation({
    mutationFn: (data) => api.entities.Task.update(task.id, data),
    onSuccess: () => {
      invalidateAfterSave();
      toast.success('Status updated');
      setConfirmingComplete(false);
    },
    onError: (error) => toast.error(error.message || 'Failed to update status'),
  });

  const hoursMutation = useMutation({
    mutationFn: (actual_hours) => api.entities.Task.update(task.id, { actual_hours }),
    onSuccess: () => {
      invalidateAfterSave();
      toast.success('Hours logged');
    },
    onError: (error) => toast.error(error.message || 'Failed to log hours'),
  });

  if (!task) return null;

  const client = clients.find((c) => c.id === task.client_id);
  const assignee = users.find((u) => u.email === task.assigned_to);
  const history = [...(task.extra?.status_history || [])].reverse();
  const nameForEmail = (email) => users.find((u) => u.email === email)?.full_name || email;

  const handleStatusClick = (newStatus) => {
    if (newStatus === task.status) return;
    if (newStatus === 'Complete' && task.client_id) {
      setConfirmingComplete(true);
      return;
    }
    statusMutation.mutate({ status: newStatus });
  };

  const confirmComplete = () => {
    statusMutation.mutate({
      status: 'Complete',
      ...(clientEmailed ? { _client_emailed: true, _client_emailed_note: clientEmailedNote.trim() || undefined } : {}),
    });
  };

  return (
    <Dialog open={true} onOpenChange={onClose}>
      <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{task.title}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {task.description && <p className="text-sm text-muted-foreground">{task.description}</p>}

          <div className="flex items-center flex-wrap gap-2">
            <Badge className={getStatusColor(task.status)} variant="outline">{task.status}</Badge>
            {task.priority && <Badge variant="outline">{task.priority}</Badge>}
            <TaskFlags task={task} />
          </div>

          {/* Read-only context — set once at creation, not re-editable here */}
          <div className="grid grid-cols-2 gap-3 p-3 rounded-lg bg-slate-50 border text-sm">
            {client && (
              <div className="col-span-2 flex items-center gap-2">
                <Building2 className="w-4 h-4 text-muted-foreground" />
                <span className="font-medium">{client.legal_name}</span>
              </div>
            )}
            {assignee && (
              <div className="col-span-2 text-muted-foreground">
                Assigned to: <span className="font-medium text-slate-700">{assignee.full_name || assignee.email}</span>
              </div>
            )}
            {task.due_date && (
              <div className="flex items-center gap-1.5 text-muted-foreground">
                <Calendar className="w-3.5 h-3.5" />
                Due {new Date(task.due_date).toLocaleDateString()}
              </div>
            )}
            {task.estimated_hours != null && task.estimated_hours !== '' && (
              <div className="flex items-center gap-1.5 text-muted-foreground">
                <Clock className="w-3.5 h-3.5" />
                Est. {task.estimated_hours}h
              </div>
            )}
            {linkedFiling && (
              <div className="col-span-2 text-blue-800">
                📋 Linked service: <span className="font-semibold">{linkedFiling.service_name}</span>
              </div>
            )}
            {task.service_frequency && (
              <div className="col-span-2 text-muted-foreground">Frequency: {task.service_frequency}</div>
            )}
          </div>

          {/* Status — one click, unless completing a client-linked task */}
          <div>
            <Label className="mb-2 block">Update Status</Label>
            <div className="grid grid-cols-2 gap-2">
              {STATUS_OPTIONS.map((opt) => (
                <Button
                  key={opt.value}
                  type="button"
                  disabled={statusMutation.isPending}
                  onClick={() => handleStatusClick(opt.value)}
                  className={cn(
                    task.status === opt.value ? opt.color : 'bg-white text-slate-700 border hover:bg-slate-50',
                  )}
                  variant={task.status === opt.value ? 'default' : 'outline'}
                >
                  {opt.value}
                </Button>
              ))}
            </div>
          </div>

          {confirmingComplete && (
            <div className="p-3 rounded-lg border border-slate-200 bg-slate-50 space-y-2">
              <div className="flex items-center gap-2">
                <Checkbox id="client_emailed" checked={clientEmailed} onCheckedChange={(c) => setClientEmailed(!!c)} />
                <Label htmlFor="client_emailed" className="cursor-pointer">Client has been emailed about this</Label>
              </div>
              {clientEmailed && (
                <Textarea
                  placeholder="Optional note about what was communicated..."
                  value={clientEmailedNote}
                  onChange={(e) => setClientEmailedNote(e.target.value)}
                  rows={2}
                  className="bg-white"
                />
              )}
              <div className="flex gap-2 pt-1">
                <Button type="button" size="sm" onClick={confirmComplete} disabled={statusMutation.isPending}>
                  Confirm Complete
                </Button>
                <Button type="button" size="sm" variant="outline" onClick={() => setConfirmingComplete(false)}>
                  Cancel
                </Button>
              </div>
            </div>
          )}

          {/* Actual hours — decoupled from status, anyone doing the work logs their own */}
          <div>
            <Label htmlFor="actual_hours">Actual Hours Worked</Label>
            <div className="flex gap-2">
              <Input
                id="actual_hours"
                type="number"
                step="0.5"
                value={hoursInput}
                onChange={(e) => setHoursInput(e.target.value)}
                className="flex-1"
              />
              <Button
                type="button"
                variant="outline"
                disabled={hoursMutation.isPending || hoursInput === (task.actual_hours ?? '')}
                onClick={() => hoursMutation.mutate(hoursInput === '' ? null : Number(hoursInput))}
              >
                Save
              </Button>
            </div>
          </div>

          {/* Status history */}
          {history.length > 0 && (
            <div>
              <Label className="mb-2 flex items-center gap-1.5"><History className="w-3.5 h-3.5" />Status History</Label>
              <div className="space-y-1.5 max-h-40 overflow-y-auto">
                {history.map((entry, idx) => (
                  <div key={idx} className="text-xs text-muted-foreground flex items-center justify-between gap-2 border-b pb-1 last:border-0">
                    <span>
                      <span className="font-medium text-slate-700">{entry.from || '—'} → {entry.to}</span>
                      {entry.by && <> · {nameForEmail(entry.by)}</>}
                    </span>
                    {entry.at && <span className="whitespace-nowrap">{new Date(entry.at).toLocaleDateString()}</span>}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="flex gap-2 pt-2 border-t">
            <Button type="button" variant="outline" onClick={onClose} className="flex-1">Close</Button>
            <Button
              type="button"
              variant="ghost"
              onClick={() => onFullEdit?.(task)}
              className="gap-1.5 text-muted-foreground"
            >
              <Pencil className="w-3.5 h-3.5" />Full Edit
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
