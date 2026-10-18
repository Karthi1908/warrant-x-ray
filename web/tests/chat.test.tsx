import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { CitationChip } from '../src/features/chat/CitationChip';
import { Composer } from '../src/features/chat/Composer';
import { SamplePrompts } from '../src/features/chat/SamplePrompts';
import { ToolTrace } from '../src/features/chat/ToolTrace';

describe('Chat Feature Components', () => {
  describe('CitationChip', () => {
    it('renders citation ID and handles click', () => {
      const onClick = vi.fn();
      render(<CitationChip evidenceId="E1" summary="Maybank Warrant Card" onClick={onClick} />);

      const chip = screen.getByText('[E1]');
      expect(chip).toBeDefined();

      fireEvent.click(chip);
      expect(onClick).toHaveBeenCalledWith('E1');
    });
  });

  describe('Composer', () => {
    it('enforces character limit and triggers onSend', () => {
      const onSend = vi.fn();
      render(<Composer onSend={onSend} isStreaming={false} />);

      const input = screen.getByPlaceholderText(/Ask about warrant holding costs/i);
      const sendBtn = screen.getByRole('button', { name: /send/i });

      fireEvent.change(input, { target: { value: 'What is the spread on 115510?' } });
      fireEvent.click(sendBtn);

      expect(onSend).toHaveBeenCalledWith('What is the spread on 115510?');
    });

    it('disables input during active streaming', () => {
      render(<Composer onSend={vi.fn()} isStreaming={true} onCancel={vi.fn()} />);
      const stopBtn = screen.getByRole('button', { name: /stop/i });
      expect(stopBtn).toBeDefined();
    });
  });

  describe('SamplePrompts', () => {
    it('renders preset sample prompts and triggers onSelect', () => {
      const onSelect = vi.fn();
      render(<SamplePrompts onSelect={onSelect} />);

      const sampleBtn = screen.getByText(/Holding cost for 115510/i);
      expect(sampleBtn).toBeDefined();

      fireEvent.click(sampleBtn);
      expect(onSelect).toHaveBeenCalled();
    });
  });

  describe('ToolTrace', () => {
    it('renders active tool execution status text', () => {
      render(
        <ToolTrace
          traces={[
            { name: 'get_warrant_card', text: 'Fetching warrant quotes and recomputing risk metrics...' },
          ]}
        />
      );
      expect(
        screen.getByText('Fetching warrant quotes and recomputing risk metrics...')
      ).toBeDefined();
    });
  });
});
