import { useState } from 'react';

interface QuickStartProps {
    onDismiss: () => void;
}

export default function QuickStart({ onDismiss }: QuickStartProps) {
    const [currentStep, setCurrentStep] = useState(0);

    const steps = [
        {
            icon: '📊',
            title: 'Charts View',
            description: 'See real-time price charts with your option payoff overlay',
            action: 'Click "Charts" tab'
        },
        {
            icon: '🔬',
            title: 'Analytics Dashboard',
            description: 'IV Smile, HV vs IV, Max Pain, and Monte Carlo simulations',
            action: 'Click "Analytics" tab'
        },
        {
            icon: '🎯',
            title: 'Position Sizing',
            description: 'Calculate optimal position size with Kelly Criterion',
            action: 'Click "Kelly" button'
        },
        {
            icon: '🤖',
            title: 'Trading Bot',
            description: 'Automate your trading strategy with paper or live mode',
            action: 'Click "Bot" button'
        }
    ];

    return (
        <div className="bg-gradient-to-r from-blue-900/30 to-purple-900/30 border border-blue-500/30 rounded-xl p-4 mb-6">
            <div className="flex justify-between items-start mb-4">
                <div className="flex items-center gap-2">
                    <span className="text-2xl">🚀</span>
                    <div>
                        <h3 className="font-semibold text-white">Quick Start Guide</h3>
                        <p className="text-xs text-gray-400">New here? Let us show you around!</p>
                    </div>
                </div>
                <button
                    onClick={onDismiss}
                    className="text-gray-400 hover:text-white text-sm"
                >
                    ✕ Dismiss
                </button>
            </div>

            {/* Step indicators */}
            <div className="flex gap-2 mb-4">
                {steps.map((_, i) => (
                    <button
                        key={i}
                        onClick={() => setCurrentStep(i)}
                        className={`w-8 h-1 rounded-full transition-all ${i === currentStep ? 'bg-blue-500' : 'bg-white/20'
                            }`}
                    />
                ))}
            </div>

            {/* Current step */}
            <div className="flex items-start gap-4">
                <span className="text-3xl">{steps[currentStep].icon}</span>
                <div className="flex-1">
                    <h4 className="font-semibold text-white">{steps[currentStep].title}</h4>
                    <p className="text-sm text-gray-300 mt-1">{steps[currentStep].description}</p>
                    <p className="text-xs text-blue-400 mt-2">→ {steps[currentStep].action}</p>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
                        disabled={currentStep === 0}
                        className="px-3 py-1 bg-white/10 rounded text-sm disabled:opacity-30"
                    >
                        ← Back
                    </button>
                    {currentStep < steps.length - 1 ? (
                        <button
                            onClick={() => setCurrentStep(currentStep + 1)}
                            className="px-3 py-1 bg-blue-600 rounded text-sm hover:bg-blue-500"
                        >
                            Next →
                        </button>
                    ) : (
                        <button
                            onClick={onDismiss}
                            className="px-3 py-1 bg-green-600 rounded text-sm hover:bg-green-500"
                        >
                            Get Started! ✓
                        </button>
                    )}
                </div>
            </div>
        </div>
    );
}
