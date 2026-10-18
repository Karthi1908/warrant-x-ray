import React, { useEffect, useRef } from 'react';
import { cn } from '../../lib/utils';
import type { ChatMessage } from '../../state/chat';
import { AssistantMessage } from './AssistantMessage';
import { Bot, User } from 'lucide-react';

export interface MessageListProps {
  messages: ChatMessage[];
  onCitationClick?: (evidenceId: string) => void;
  className?: string;
}

export const MessageList: React.FC<MessageListProps> = ({
  messages,
  onCitationClick,
  className,
}) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div
        className={cn(
          'flex flex-1 flex-col items-center justify-center p-6 text-center text-muted-foreground',
          className
        )}
      >
        <div className="h-10 w-10 rounded-full bg-primary/10 flex items-center justify-center text-primary mb-3">
          <Bot className="h-5 w-5" />
        </div>
        <p className="text-sm font-medium text-foreground">Warrant X-Ray Copilot</p>
        <p className="text-xs text-muted-foreground mt-1 max-w-xs">
          Select a sample question below or type your inquiry. All metrics are computed
          deterministically; advice requests are refused.
        </p>
      </div>
    );
  }

  return (
    <div className={cn('flex-1 overflow-y-auto space-y-4 p-4', className)}>
      {messages.map((msg) => {
        if (msg.role === 'user') {
          return (
            <div key={msg.id} className="flex justify-end space-x-2">
              <div className="max-w-[85%] rounded-xl bg-primary text-primary-foreground px-3.5 py-2 text-sm shadow-sm">
                <p className="whitespace-pre-wrap">{msg.content}</p>
              </div>
              <div className="h-7 w-7 rounded-full bg-muted flex items-center justify-center text-muted-foreground shrink-0 mt-1">
                <User className="h-4 w-4" />
              </div>
            </div>
          );
        }

        return (
          <div key={msg.id} className="flex space-x-2">
            <div className="h-7 w-7 rounded-full bg-primary/20 flex items-center justify-center text-primary shrink-0 mt-1">
              <Bot className="h-4 w-4" />
            </div>
            <div className="flex-1 max-w-[90%]">
              <AssistantMessage
                content={msg.content}
                isPartial={msg.isPartial}
                isVerified={msg.isVerified}
                onCitationClick={onCitationClick}
              />
            </div>
          </div>
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
};
