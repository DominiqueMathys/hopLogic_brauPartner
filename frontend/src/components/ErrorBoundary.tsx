import { Component, type ErrorInfo, type ReactNode } from 'react'
import { ErrorState } from './ui/ErrorState.tsx'

type Props = { children: ReactNode }
type State = { failed: boolean }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { failed: false }

  static getDerivedStateFromError(): State {
    return { failed: true }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    console.error(error, info.componentStack)
  }

  render(): ReactNode {
    if (this.state.failed) {
      return (
        <div className="min-h-screen bg-cream p-6 text-ink">
          <ErrorState
            title="Die Ansicht konnte nicht angezeigt werden"
            description="Laden Sie die Seite neu. Wenn der Hinweis bleibt, ist die Oberfläche auf einen unerwarteten Fehler gestossen."
            action={
              <a className="text-sm font-semibold text-petrol underline" href="/">
                Seite neu laden
              </a>
            }
          />
        </div>
      )
    }
    return this.props.children
  }
}
