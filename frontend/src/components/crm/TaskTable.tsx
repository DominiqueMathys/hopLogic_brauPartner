import { Link } from 'react-router'
import { ApiError, completeTask } from '../../api/crm.ts'
import { labelOf, taskPriorityOptions, taskStatusOptions, type Task } from '../../domain/crm.ts'
import { formatDateTime } from '../../domain/partners.ts'
import { Badge } from '../ui/Badge.tsx'
import { Button } from '../ui/Button.tsx'
import { DataTable, type DataColumn } from '../ui/DataTable.tsx'
import { EmptyState } from '../ui/EmptyState.tsx'
import { useToast } from '../ui/toast-state.ts'

function priorityTone(task: Task): 'critical' | 'warning' | 'neutral' | 'success' {
  if (task.is_overdue || task.priority === 'dringend') {
    return 'critical'
  }
  if (task.is_due_soon || task.priority === 'hoch') {
    return 'warning'
  }
  if (task.status === 'erledigt') {
    return 'success'
  }
  return 'neutral'
}

const columns: DataColumn<Task>[] = [
  {
    id: 'title',
    header: 'Aufgabe',
    cell: (row) => (
      <div>
        <Link to={`/aufgaben/${row.id}/bearbeiten`} className="font-semibold text-petrol">
          {row.title}
        </Link>
        {row.is_demo ? (
          <div className="mt-1">
            <Badge tone="accent">Testdaten</Badge>
          </div>
        ) : null}
      </div>
    ),
  },
  {
    id: 'due',
    header: 'Fällig',
    cell: (row) => (
      <span className={row.is_overdue ? 'font-semibold text-critical' : undefined}>
        {formatDateTime(row.due_at)}
        {row.is_overdue ? ' · Überfällig' : row.is_due_soon ? ' · Bald fällig' : ''}
      </span>
    ),
  },
  {
    id: 'priority',
    header: 'Priorität',
    cell: (row) => <Badge tone={priorityTone(row)}>{labelOf(taskPriorityOptions, row.priority)}</Badge>,
  },
  {
    id: 'status',
    header: 'Status',
    cell: (row) => labelOf(taskStatusOptions, row.status),
  },
  {
    id: 'owner',
    header: 'Zuständig',
    cell: (row) => row.account_owner ?? 'Nicht zugewiesen',
  },
]

type TaskTableProps = {
  rows: Task[]
  onChanged: () => void
}

export function TaskTable({ rows, onChanged }: TaskTableProps) {
  const { notify } = useToast()
  const withAction: DataColumn<Task>[] = [
    ...columns,
    {
      id: 'action',
      header: 'Aktion',
      cell: (row) =>
        row.status === 'offen' || row.status === 'in_bearbeitung' ? (
          <Button
            variant="secondary"
            onClick={() => {
              void completeTask(row.id)
                .then(() => {
                  notify({ tone: 'success', message: 'Die Aufgabe wurde als erledigt markiert.' })
                  onChanged()
                })
                .catch((caught: unknown) => {
                  notify({
                    tone: 'critical',
                    message: caught instanceof ApiError ? caught.message : 'Die Verbindung zur API ist fehlgeschlagen.',
                  })
                })
            }}
          >
            Erledigt
          </Button>
        ) : (
          <span className="text-sm text-muted">Keine</span>
        ),
    },
  ]

  return (
    <DataTable
      caption="Aufgaben"
      columns={withAction}
      rows={rows}
      rowKey={(row) => row.id}
      empty={<EmptyState compact title="Keine Aufgaben" description="Es sind keine Aufgaben für diese Ansicht gespeichert." />}
    />
  )
}

