import { useState, type ReactNode } from 'react';

interface TooltipProps {
    children: ReactNode;
    content: string;
    position?: 'top' | 'bottom' | 'left' | 'right';
}

export default function Tooltip({ children, content, position = 'top' }: TooltipProps) {
    const [show, setShow] = useState(false);

    const positionClasses = {
        top: 'bottom-full left-1/2 -translate-x-1/2 mb-2',
        bottom: 'top-full left-1/2 -translate-x-1/2 mt-2',
        left: 'right-full top-1/2 -translate-y-1/2 mr-2',
        right: 'left-full top-1/2 -translate-y-1/2 ml-2'
    };

    return (
        <div
            className="relative inline-block"
            onMouseEnter={() => setShow(true)}
            onMouseLeave={() => setShow(false)}
        >
            {children}
            {show && (
                <div className={`absolute ${positionClasses[position]} z-50 px-3 py-2 text-xs text-white bg-gray-900 rounded-lg shadow-lg whitespace-nowrap border border-white/10`}>
                    {content}
                    {/* Arrow */}
                    <div className={`absolute w-2 h-2 bg-gray-900 transform rotate-45 ${position === 'top' ? 'top-full left-1/2 -translate-x-1/2 -mt-1' :
                        position === 'bottom' ? 'bottom-full left-1/2 -translate-x-1/2 -mb-1' :
                            position === 'left' ? 'left-full top-1/2 -translate-y-1/2 -ml-1' :
                                'right-full top-1/2 -translate-y-1/2 -mr-1'
                        }`} />
                </div>
            )}
        </div>
    );
}
