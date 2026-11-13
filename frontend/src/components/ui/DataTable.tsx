import type { ReactNode } from 'react'

export type DataColumn<T> = {
  id: string
  header: string
  cell: (row: T) => ReactNode
}

type DataTableProps<T> = {
  caption: string
  columns: DataColumn<T>[]
  rows: readonly T[]
  rowKey: (row: T) => string
  empty: ReactNode
}

export function DataTable<T>({ caption, columns, rows, rowKey, empty }: DataTableProps<T>) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-left text-sm">
        <caption className="sr-only">{caption}</caption>
        <thead>
          <tr>
            {columns.map((column) => (
              <th
                key={column.id}
                scope="col"
                className="border-b border-line px-3 py-2 text-xs font-semibold tracking-wide text-muted uppercase"
              >
                {column.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={columns.length}>{empty}</td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr key={rowKey(row)}>
                {columns.map((column) => (
                  <td key={column.id} className="border-b border-line px-3 py-3 align-top">
                    {column.cell(row)}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  )
}
