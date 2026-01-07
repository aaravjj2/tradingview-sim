import type { ReactNode } from 'react';

interface CardProps {
    title: string;
    icon?: string;
    children: ReactNode;
    action?: ReactNode;
    className?: string;
    help?: string;
}

export default function Card({ title, icon, children, action, className = '', help }: CardProps) {
    return (
        <div className={`bg-[#1a1f2e] rounded-xl overflow-hidden ${className}`}>
            {/* Header */}
            <div className="flex justify-between items-center px-4 py-3 border-b border-white/5">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    {icon && <span>{icon}</span>}
                    {title}
                    {help && (
                        <span
                            className="text-gray-500 cursor-help text-xs"
                            title={help}
                        >
                            ⓘ
                        </span>
                    )}
                </h3>
                {action && (
                    <div className="flex items-center gap-2 text-xs">
                        {action}
                    </div>
                )}
            </div>
            {/* Content */}
            <div className="p-4">
                {children}
            </div>
        </div>
    );
}

// Section Header component
export function SectionHeader({ title, subtitle }: { title: string; subtitle?: string }) {
    return (
        <div className="mb-4">
            <h2 className="text-lg font-bold text-white">{title}</h2>
            {subtitle && <p className="text-sm text-gray-400">{subtitle}</p>}
        </div>
    );
}

// Stat Box component
export function StatBox({
    label,
    value,
    sublabel,
    color = 'white',
    size = 'normal'
}: {
    label: string;
    value: string | number;
    sublabel?: string;
    color?: 'green' | 'red' | 'yellow' | 'blue' | 'purple' | 'white';
    size?: 'small' | 'normal' | 'large';
}) {
    const colorClasses = {
        green: 'text-green-400',
        red: 'text-red-400',
        yellow: 'text-yellow-400',
        blue: 'text-blue-400',
        purple: 'text-purple-400',
        white: 'text-white'
    };

    const sizeClasses = {
        small: 'text-lg',
        normal: 'text-2xl',
        large: 'text-3xl'
    };

    return (
        <div className="text-center">
            <div className="text-xs text-gray-400 uppercase tracking-wider mb-1">{label}</div>
            <div className={`font-bold ${colorClasses[color]} ${sizeClasses[size]}`}>
                {value}
            </div>
            {sublabel && <div className="text-xs text-gray-500 mt-1">{sublabel}</div>}
        </div>
    );
}
