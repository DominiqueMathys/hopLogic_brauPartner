import { Bar, BarChart, CartesianGrid, Cell, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { ReportChart as ChartModel } from '../../api/reports.ts'

const COLORS = ['#0f4c57', '#8d7028', '#1d6b3e', '#b35d0a', '#9d342c', '#31414c', '#4e5b64', '#0c3d46']

const countFormat = new Intl.NumberFormat('de-CH')
const chfFormat = new Intl.NumberFormat('de-CH', { style: 'currency', currency: 'CHF' })

function display(unit: string, value: number): string {
  if (unit === 'chf') return chfFormat.format(value)
  return countFormat.format(value)
}

function rows(chart: ChartModel) {
  return chart.points.map((point) => ({
    label: point.label,
    value: chart.unit === 'chf' ? Number(point.amount ?? 0) : Number(point.count ?? 0),
  }))
}

export function ReportChart({ chart }: { chart: ChartModel }) {
  const data = rows(chart)
  const empty = data.every((point) => point.value === 0)
  return (
    <section className="border border-line bg-card p-4">
      <h3 className="text-base font-semibold">{chart.title}</h3>
      <p className="mt-1 text-sm leading-6 text-muted">{chart.note}</p>
      {empty ? (
        <p className="mt-4 text-sm">Keine Werte im gewählten Filter.</p>
      ) : (
        <div className="mt-4 h-64">
          <ResponsiveContainer width="100%" height="100%">
            {chart.kind === 'line' ? (
              <LineChart data={data} accessibilityLayer>
                <CartesianGrid stroke="#e0d6c6" />
                <XAxis dataKey="label" tick={{ fill: '#1b242b', fontSize: 12 }} />
                <YAxis tick={{ fill: '#1b242b', fontSize: 12 }} tickFormatter={(value: number) => display(chart.unit, value)} />
                <Tooltip formatter={(value) => display(chart.unit, Number(value ?? 0))} />
                <Legend />
                <Line type="monotone" dataKey="value" name={chart.unit === 'chf' ? 'CHF' : 'Anzahl'} stroke="#0f4c57" strokeWidth={2} dot />
              </LineChart>
            ) : chart.kind === 'donut' ? (
              <PieChart accessibilityLayer>
                <Pie data={data} dataKey="value" nameKey="label" innerRadius={52} outerRadius={80} label>
                  {data.map((point, index) => (
                    <Cell key={point.label} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value) => display(chart.unit, Number(value ?? 0))} />
                <Legend />
              </PieChart>
            ) : (
              <BarChart data={data} accessibilityLayer>
                <CartesianGrid stroke="#e0d6c6" />
                <XAxis dataKey="label" tick={{ fill: '#1b242b', fontSize: 12 }} interval={0} angle={-20} height={60} textAnchor="end" />
                <YAxis tick={{ fill: '#1b242b', fontSize: 12 }} tickFormatter={(value: number) => display(chart.unit, value)} />
                <Tooltip formatter={(value) => display(chart.unit, Number(value ?? 0))} />
                <Legend />
                <Bar dataKey="value" name={chart.unit === 'chf' ? 'CHF' : 'Anzahl'} fill="#0f4c57" />
              </BarChart>
            )}
          </ResponsiveContainer>
        </div>
      )}
      <table className="mt-4 w-full text-sm">
        <caption className="sr-only">Wertetabelle zu {chart.title}</caption>
        <thead>
          <tr className="border-b border-line text-left">
            <th className="py-2 font-semibold">Bezeichnung</th>
            <th className="py-2 font-semibold">Wert</th>
          </tr>
        </thead>
        <tbody>
          {data.map((point) => (
            <tr key={point.label} className="border-b border-line">
              <td className="py-2">{point.label}</td>
              <td className="py-2">{display(chart.unit, point.value)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

export function formatKpi(value: string | null, unit: string): string {
  if (value === null) return 'nicht berechenbar'
  if (unit === 'chf') return chfFormat.format(Number(value))
  if (unit === 'percent') return `${new Intl.NumberFormat('de-CH', { maximumFractionDigits: 1 }).format(Number(value))} %`
  if (unit === 'hours') return `${new Intl.NumberFormat('de-CH', { maximumFractionDigits: 1 }).format(Number(value))} h`
  return countFormat.format(Number(value))
}
