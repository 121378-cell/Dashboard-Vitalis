import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Chat } from '../Chat';
import type { Message } from '../../types';

const mockOnSendMessage = vi.fn();

const defaultQuickActions = [
  { label: '¿Cómo estoy?', prompt: '¿Cómo estoy hoy? Dame un análisis de mi estado actual.' },
  { label: '¿Qué entreno?', prompt: '¿Qué debería entrenar hoy?' },
  { label: 'Generar plan', prompt: 'Generar un plan de entrenamiento' },
];

const wrapper = ({ children }: { children: React.ReactNode }) => <>{children}</>;

describe('Chat', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockOnSendMessage.mockClear();
  });

  it('renders welcome message when chatHistory is empty', async () => {
    render(
      <Chat
        messages={[]}
        onSendMessage={mockOnSendMessage}
        loading={false}
        quickActions={defaultQuickActions}
      />,
      { wrapper }
    );

    await waitFor(() => {
      expect(screen.getByText(/Hola, soy ATLAS/i)).toBeTruthy();
    });
  });

  it('renders quick action buttons', async () => {
    render(
      <Chat
        messages={[]}
        onSendMessage={mockOnSendMessage}
        loading={false}
        quickActions={defaultQuickActions}
      />,
      { wrapper }
    );

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /¿Cómo estoy?/i })).toBeTruthy();
      expect(screen.getByRole('button', { name: /¿Qué entreno?/i })).toBeTruthy();
      expect(screen.getByRole('button', { name: /Generar plan/i })).toBeTruthy();
    });
  });

  it('calls onSendMessage with quick action prompt when quick action is clicked', async () => {
    render(
      <Chat
        messages={[]}
        onSendMessage={mockOnSendMessage}
        loading={false}
        quickActions={defaultQuickActions}
      />,
      { wrapper }
    );

    await waitFor(() => {
      const quickAction = screen.getByRole('button', { name: /¿Cómo estoy?/i });
      fireEvent.click(quickAction);
    });

    await waitFor(() => {
      expect(mockOnSendMessage).toHaveBeenCalledWith(
        '¿Cómo estoy hoy? Dame un análisis de mi estado actual.'
      );
    });
  });

  it('displays user and assistant messages when chatHistory has messages', async () => {
    const messages: Message[] = [
      { role: 'user', content: '¿Cómo estoy hoy?' },
      { role: 'assistant', content: 'Tu readiness está en 75/100', provider: 'gemini' }
    ];

    render(
      <Chat
        messages={messages}
        onSendMessage={mockOnSendMessage}
        loading={false}
        quickActions={defaultQuickActions}
      />,
      { wrapper }
    );

    await waitFor(() => {
      expect(screen.getByText('¿Cómo estoy hoy?')).toBeTruthy();
      expect(screen.getByText('Tu readiness está en 75/100')).toBeTruthy();
    });
  });

  it('calls onSendMessage when user types and sends message', async () => {
    render(
      <Chat
        messages={[]}
        onSendMessage={mockOnSendMessage}
        loading={false}
        quickActions={defaultQuickActions}
      />,
      { wrapper }
    );

    await waitFor(() => {
      const textarea = screen.getByPlaceholderText(/Escribe tu mensaje/i);
      fireEvent.change(textarea, { target: { value: '¿Qué entreno hoy?' } });
    });

    const button = screen.getByRole('button', { name: 'Enviar mensaje' }) as HTMLElement;
    fireEvent.click(button);

    await waitFor(() => {
      expect(mockOnSendMessage).toHaveBeenCalledWith('¿Qué entreno hoy?');
    });
  });

  it('shows loading state when loading is true', async () => {
    render(
      <Chat
        messages={[]}
        onSendMessage={mockOnSendMessage}
        loading={true}
        quickActions={defaultQuickActions}
      />,
      { wrapper }
    );

    await waitFor(() => {
      expect(screen.getByText(/ATLAS está procesando/i)).toBeTruthy();
    });
  });
});
