import React, { useState, useRef, useEffect } from 'react';
import { cn } from '../../lib/utils';
import { Send, Square } from 'lucide-react';

export interface ComposerProps {
  onSend: (message: string) => void;
  isStreaming: boolean;
  onCancel?: () => void;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

const MAX_CHARS = 1000;

export const Composer: React.FC<ComposerProps> = ({
  onSend,
  isStreaming,
  onCancel,
  placeholder = 'Ask about warrant holding costs, break-evens, or risks...',
  disabled = false,
  className,
}) => {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const charCount = value.length;
  const isOverLimit = charCount > MAX_CHARS;
  const canSend = value.trim().length > 0 && !isOverLimit && !isStreaming && !disabled;

  const handleSend = () => {
    if (!canSend) return;
    const trimmed = value.trim();
    setValue('');
    onSend(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [value]);

  return (
    <div className={cn('relative rounded-xl border border-border bg-card p-2 shadow-sm', className)}>
      <textarea
        ref={textareaRef}
        rows={2}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={isStreaming || disabled}
        maxLength={MAX_CHARS}
        className={cn(
          'w-full resize-none bg-transparent px-2 py-1 text-sm outline-none placeholder:text-muted-foreground/60',
          'disabled:cursor-not-allowed disabled:opacity-60'
        )}
      />

      <div className="flex items-center justify-between border-t border-border/40 pt-2 px-1 text-xs">
        <span
          className={cn(
            'font-mono text-[11px]',
            isOverLimit ? 'text-destructive font-semibold' : 'text-muted-foreground'
          )}
        >
          {charCount} / {MAX_CHARS}
        </span>

        <div className="flex items-center space-x-2">
          {isStreaming ? (
            <button
              type="button"
              onClick={onCancel}
              className="inline-flex items-center space-x-1.5 rounded-lg bg-destructive/10 px-3 py-1.5 font-medium text-destructive hover:bg-destructive/20 transition-colors"
              aria-label="Stop generation"
            >
              <Square className="h-3.5 w-3.5 fill-current" />
              <span>Stop</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSend}
              disabled={!canSend}
              className={cn(
                'inline-flex items-center space-x-1.5 rounded-lg px-3 py-1.5 font-medium transition-colors',
                canSend
                  ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                  : 'bg-muted text-muted-foreground cursor-not-allowed'
              )}
              aria-label="Send message"
            >
              <Send className="h-3.5 w-3.5" />
              <span>Send</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
};
