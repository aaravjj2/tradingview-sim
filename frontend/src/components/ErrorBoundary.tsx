import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
    children: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
    errorInfo: ErrorInfo | null;
}

class ErrorBoundary extends Component<Props, State> {
    public state: State = {
        hasError: false,
        error: null,
        errorInfo: null
    };

    public static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error, errorInfo: null };
    }

    public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error('ErrorBoundary caught an error:', error, errorInfo);
        this.setState({ error, errorInfo });
    }

    public render() {
        if (this.state.hasError) {
            return (
                <div style={{
                    backgroundColor: '#1a1f2e',
                    color: 'white',
                    padding: '40px',
                    minHeight: '100vh',
                    fontFamily: 'monospace'
                }}>
                    <h1 style={{ color: '#ff6b6b', marginBottom: '20px' }}>
                        🚨 Application Crashed
                    </h1>
                    <div style={{
                        backgroundColor: '#0f1117',
                        padding: '20px',
                        borderRadius: '8px',
                        marginBottom: '20px'
                    }}>
                        <h2 style={{ color: '#ffa502', marginBottom: '10px' }}>
                            Error Message:
                        </h2>
                        <pre style={{ color: '#ff6b6b', whiteSpace: 'pre-wrap' }}>
                            {this.state.error?.message}
                        </pre>
                    </div>
                    <div style={{
                        backgroundColor: '#0f1117',
                        padding: '20px',
                        borderRadius: '8px',
                        marginBottom: '20px'
                    }}>
                        <h2 style={{ color: '#ffa502', marginBottom: '10px' }}>
                            Stack Trace:
                        </h2>
                        <pre style={{
                            color: '#a0a0a0',
                            whiteSpace: 'pre-wrap',
                            fontSize: '12px',
                            maxHeight: '300px',
                            overflow: 'auto'
                        }}>
                            {this.state.error?.stack}
                        </pre>
                    </div>
                    {this.state.errorInfo && (
                        <div style={{
                            backgroundColor: '#0f1117',
                            padding: '20px',
                            borderRadius: '8px'
                        }}>
                            <h2 style={{ color: '#ffa502', marginBottom: '10px' }}>
                                Component Stack:
                            </h2>
                            <pre style={{
                                color: '#a0a0a0',
                                whiteSpace: 'pre-wrap',
                                fontSize: '12px',
                                maxHeight: '200px',
                                overflow: 'auto'
                            }}>
                                {this.state.errorInfo.componentStack}
                            </pre>
                        </div>
                    )}
                    <button
                        onClick={() => window.location.reload()}
                        style={{
                            marginTop: '20px',
                            padding: '12px 24px',
                            backgroundColor: '#3b82f6',
                            color: 'white',
                            border: 'none',
                            borderRadius: '8px',
                            cursor: 'pointer',
                            fontSize: '16px'
                        }}
                    >
                        🔄 Reload Page
                    </button>
                </div>
            );
        }

        return this.props.children;
    }
}

export default ErrorBoundary;
