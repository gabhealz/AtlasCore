import { Component, type ErrorInfo, type ReactNode } from 'react';

type AppErrorBoundaryProps = {
  children: ReactNode;
  resetKey: string;
};

type AppErrorBoundaryState = {
  error: Error | null;
};

export default class AppErrorBoundary extends Component<
  AppErrorBoundaryProps,
  AppErrorBoundaryState
> {
  state: AppErrorBoundaryState = {
    error: null,
  };

  static getDerivedStateFromError(error: Error): AppErrorBoundaryState {
    return { error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Frontend route crashed', error, errorInfo);
  }

  componentDidUpdate(previousProps: AppErrorBoundaryProps) {
    if (previousProps.resetKey !== this.props.resetKey && this.state.error) {
      this.setState({ error: null });
    }
  }

  private handleRetry = () => {
    window.location.reload();
  };

  private handleDashboard = () => {
    window.location.assign('/dashboard');
  };

  render() {
    if (!this.state.error) {
      return this.props.children;
    }

    return (
      <div className="min-h-screen bg-elevated px-4 py-12">
        <div className="mx-auto max-w-xl rounded-xl border border-red-100 bg-card p-6 shadow">
          <p className="text-sm font-semibold uppercase tracking-wide text-red-700">
            Erro ao carregar a tela
          </p>
          <h1 className="mt-2 text-2xl font-bold text-ink">
            A pagina encontrou um problema.
          </h1>
          <p className="mt-3 text-sm text-muted">
            A aplicacao continuou aberta, mas esta rota travou durante o
            carregamento. Recarregue a pagina ou volte para o dashboard.
          </p>

          <div className="mt-6 flex flex-col gap-3 sm:flex-row">
            <button
              type="button"
              onClick={this.handleRetry}
              className="rounded-md border border-transparent bg-brand px-4 py-2 text-sm font-medium text-white hover:bg-brand-soft"
            >
              Recarregar pagina
            </button>
            <button
              type="button"
              onClick={this.handleDashboard}
              className="rounded-md border border-line px-4 py-2 text-sm font-medium text-ink hover:bg-elevated"
            >
              Ir para dashboard
            </button>
          </div>
        </div>
      </div>
    );
  }
}
