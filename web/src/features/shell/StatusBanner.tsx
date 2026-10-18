import React from 'react';
import { cn } from '../../lib/utils';
import { AlertCircle, AlertTriangle, CheckCircle, Info, X } from 'lucide-react';

export type StatusBannerType = 'info' | 'warning' | 'error' | 'success';

export interface StatusBannerProps {
  type?: StatusBannerType;
  message: string;
  onDismiss?: () => void;
  className?: string;
}

export const StatusBanner: React.FC<StatusBannerProps> = ({
  type = 'info',
  message,
  onDismiss,
  className,
}) => {
  const getTypeConfig = () => {
    switch (type) {
      case 'warning':
        return {
          icon: AlertTriangle,
          classes: 'bg-amber-500/10 text-amber-500 border-amber-500/20',
        };
      case 'error':
        return {
          icon: AlertCircle,
          classes: 'bg-destructive/10 text-destructive border-destructive/20',
        };
      case 'success':
        return {
          icon: CheckCircle,
          classes: 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20',
        };
      case 'info':
      default:
        return {
          icon: Info,
          classes: 'bg-primary/10 text-primary border-primary/20',
        };
    }
  };

  const config = getTypeConfig();
  const Icon = config.icon;

  return (
    <div
      role="alert"
      className={cn(
        'flex items-center justify-between border-b px-4 py-2 text-xs font-medium',
        config.classes,
        className
      )}
    >
      <div className="flex items-center space-x-2">
        <Icon className="h-4 w-4 shrink-0" />
        <span>{message}</span>
      </div>
      {onDismiss && (
        <button
          type="button"
          onClick={onDismiss}
          className="p-1 opacity-70 hover:opacity-100 transition-opacity"
          aria-label="Dismiss banner"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}
    </div>
  );
};
