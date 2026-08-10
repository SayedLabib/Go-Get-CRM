import React, { useState, useEffect } from 'react';
import { DragDropContext } from '@hello-pangea/dnd';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/apiClient';
import KanbanColumn from '@/features/tasks/components/kanban/KanbanColumn';
import TaskFormModal from '@/features/tasks/components/TaskFormModal';
import TaskStatusUpdateModal from '@/features/tasks/components/TaskStatusUpdateModal';
import { Button } from '@/components/ui/button';
import { Plus, RefreshCw } from 'lucide-react';
import { toast } from 'sonner';

const STATUSES = ['Not Started', 'In Progress', 'Blocked', 'Complete'];

export default function TaskKanban() {
  const queryClient = useQueryClient();
  const [selectedTask, setSelectedTask] = useState(null);
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [statusUpdateTask, setStatusUpdateTask] = useState(null);

  const { data: tasks = [], isLoading } = useQuery({
    queryKey: ['tasks'],
    queryFn: () => api.entities.Task.list()
  });

  const { data: user } = useQuery({
    queryKey: ['currentUser'],
    queryFn: () => api.auth.me()
  });

  const updateTaskMutation = useMutation({
    mutationFn: ({ taskId, data }) => api.entities.Task.update(taskId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
    onError: () => {
      toast.error('Failed to update task');
    }
  });

  const handleDragEnd = (result) => {
    const { draggableId, destination } = result;

    if (!destination) return;

    const task = tasks.find(t => t.id === draggableId);
    if (!task) return;

    const newStatus = destination.droppableId;
    if (task.status === newStatus) return;

    updateTaskMutation.mutate({
      taskId: task.id,
      data: { ...task, status: newStatus }
    });

    toast.success(`Task moved to ${newStatus}`);
  };

  const handleTaskClick = (task) => {
    // A plain click opens the focused status/history modal; dragging (the
    // more common way to change status on this board) is unaffected.
    setStatusUpdateTask(task);
  };

  const handleFullEdit = (task) => {
    setStatusUpdateTask(null);
    setSelectedTask(task);
    setIsFormOpen(true);
  };

  const getTasksByStatus = (status) => {
    return tasks.filter(task => task.status === status);
  };

  const canManageTasks = ['director', 'admin', 'manager'].includes(user?.role);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="w-8 h-8 border-4 border-slate-200 border-t-slate-800 rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col bg-gradient-to-br from-slate-50 via-blue-50/30 to-purple-50/30">
      {/* Header */}
      <div className="px-4 sm:px-6 lg:px-8 py-4 sm:py-6 border-b border-slate-200">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl sm:text-3xl lg:text-4xl font-bold text-slate-900">Task Kanban Board</h1>
            <p className="text-muted-foreground mt-1 text-sm sm:text-base">Drag tasks between columns to update their status</p>
          </div>
          <div className="flex gap-2">
            <Button
              variant="outline"
              onClick={() => queryClient.invalidateQueries({ queryKey: ['tasks'] })}
            >
              <RefreshCw className="w-4 h-4" />
              Refresh
            </Button>
            {canManageTasks && (
              <Button
                onClick={() => {
                  setSelectedTask(null);
                  setIsFormOpen(true);
                }}
              >
                <Plus className="w-4 h-4 mr-2" />
                New Task
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Kanban Board */}
      <div className="flex-1 overflow-x-auto p-4 sm:p-6 lg:p-8">
        <DragDropContext onDragEnd={handleDragEnd}>
          <div className="flex gap-4 sm:gap-6 min-w-min snap-x snap-mandatory">
            {STATUSES.map((status) => (
              <KanbanColumn
                key={status}
                status={status}
                tasks={getTasksByStatus(status)}
                onTaskClick={handleTaskClick}
              />
            ))}
          </div>
        </DragDropContext>
      </div>

      {/* Focused status-update modal — the default click target */}
      {statusUpdateTask && (
        <TaskStatusUpdateModal
          task={statusUpdateTask}
          currentUser={user}
          onClose={() => setStatusUpdateTask(null)}
          onFullEdit={handleFullEdit}
        />
      )}

      {/* Full create/edit form — "New Task" and "Full Edit" */}
      {isFormOpen && (
        <TaskFormModal
          task={selectedTask}
          currentUser={user}
          onClose={() => {
            setIsFormOpen(false);
            setSelectedTask(null);
          }}
        />
      )}
    </div>
  );
}