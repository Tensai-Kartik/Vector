import React, { Component, ErrorInfo, ReactNode } from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Uncaught error caught by ErrorBoundary:', error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen bg-[#07090e] text-slate-100 flex flex-col items-center justify-center p-6 font-mono">
          <div className="bg-[#0b0f17] border border-rose-500/30 rounded-2xl p-6 sm:p-8 max-w-lg w-full text-center shadow-2xl space-y-4">
            <div className="w-12 h-12 rounded-xl bg-rose-500/10 border border-rose-500/30 flex items-center justify-center mx-auto text-rose-400">
              <AlertTriangle className="w-6 h-6" />
            </div>
            <h2 className="text-base font-bold text-white uppercase tracking-wider">
              UI Render Warning Caught
            </h2>
            <p className="text-xs text-slate-400 font-sans">
              A temporary interface error occurred. The system guardrails have preserved your session state.
            </p>
            {this.state.error && (
              <pre className="text-[11px] text-rose-300 bg-black/60 p-3 rounded-xl text-left overflow-x-auto max-h-36">
                {this.state.error.message}
              </pre>
            )}
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.reload();
              }}
              className="px-5 py-2 rounded-xl bg-[#d4ff00] hover:bg-[#c2ea00] text-black font-bold text-xs flex items-center space-x-2 mx-auto transition shadow-lg shadow-[#d4ff00]/10"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              <span>RELOAD INTERFACE</span>
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;

