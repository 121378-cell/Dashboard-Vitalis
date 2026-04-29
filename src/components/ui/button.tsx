// src/components/ui/button.tsx
import React from 'react';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'outline' | 'ghost';
  size?: 'default' | 'sm' | 'lg';
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className = '', variant = 'default', size = 'default', children, ...props }, ref) => {
    const baseClass = 'inline-flex items-center justify-center rounded-lg font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)] focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none';
    
    const variants = {
      default: 'bg-[var(--color-primary)] text-[var(--color-on-primary)] hover:brightness-110',
      outline: 'border border-[var(--color-outline-variant)] bg-[var(--color-surface-container)] hover:bg-[var(--color-surface-high)]',
      ghost: 'hover:bg-[var(--color-surface-variant)] hover:text-[var(--color-text)]',
    };
    
    const sizes = {
      default: 'h-10 px-4 py-2',
      sm: 'h-8 px-3 text-sm',
      lg: 'h-12 px-6 text-lg',
    };
    
    const classes = [
      baseClass,
      variants[variant],
      sizes[size],
      className,
    ].filter(Boolean).join(' ');
    
    return (
      <button
        className={classes}
        ref={ref}
        {...props}
      >
        {children}
      </button>
    );
  }
);

Button.displayName = 'Button';
