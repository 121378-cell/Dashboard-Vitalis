import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { Chat } from '../Chat';
import type { Message, ChatContextMeta } from '../../types';

const mockMessages: Message[] = [];
const mockAddChatMessage = vi.fn();

vi.mock('../../services/aiService', () => ({
  callAI: vi.fn(),
  getWelcomeMessage: vi.fn(),
}));

vi.mock('../../store/atlasStore', () => ({
  useAtlasStore: vi.fn(() => {
    return (selector: (state: { chatHistory: Message[]; addChatMessage: typeof mockAddChatMessage }) => unknown) => 
      selector({ chatHistory: mockMessages, addChatMessage: mockAddChatMessage });
  }),
}));

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

import { callAI, getWelcomeMessage } from '../../services/aiService';

const mockCallAI = callAI as unknown as { mockResolvedValue: (val: any) => void; mockRejectedValue: (val: any) => void };
const mockGetWelcomeMessage = getWelcomeMessage as unknown as { mockResolvedValue: (val: any) => void; mockRejectedValue: (val: any) => void };

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>{children}</BrowserRouter>
);

describe('Chat', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockMessages.length = 0;
    mockGetWelcomeMessage.mockResolvedValue({
      message: '¡Hola! Soy ATLAS, tu Director Deportivo.',
    });
  });

  it('renders welcome message when chatHistory is empty', async () => {
    render(<Chat />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/¡Hola! Soy ATLAS/i)).toBeTruthy();
    });
  });

  it('fetches welcome message on mount', async () => {
    mockGetWelcomeMessage.mockResolvedValue({
      message: 'Welcome to ATLAS',
    });

    render(<Chat />, { wrapper });

    await waitFor(() => {
      expect(mockGetWelcomeMessage).toHaveBeenCalled();
    });
  });

  it('shows fallback welcome message when API fails', async () => {
    mockGetWelcomeMessage.mockRejectedValue(new Error('API Error'));

    render(<Chat />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/Sergi/i)).toBeTruthy();
    });
  });

  it('renders quick action buttons', async () => {
    render(<Chat />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/¿Cómo estoy?/i)).toBeTruthy();
      expect(screen.getByText(/¿Qué entreno?/i)).toBeTruthy();
      expect(screen.getByText(/Generar plan/i)).toBeTruthy();
    });
  });

  it('calls addChatMessage with quick action when quick action is clicked', async () => {
    mockCallAI.mockResolvedValue({
      content: 'Respuesta del coach',
      provider: 'gemini',
    });

    render(<Chat />, { wrapper });

    await waitFor(() => {
      const quickAction = screen.getByText(/¿Cómo estoy?/i);
      fireEvent.click(quickAction);
    });

    await waitFor(() => {
      expect(mockAddChatMessage).toHaveBeenCalledWith({
        role: 'user',
        content: '¿Cómo estoy hoy? Dame un análisis de mi estado actual.',
      });
    });
  });

  it('displays user and assistant messages when chatHistory has messages', async () => {
    mockMessages.push(
      { role: 'user', content: '¿Cómo estoy hoy?' },
      { role: 'assistant', content: 'Tu readiness está en 75/100', provider: 'gemini' }
    );

    render(<Chat />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('¿Cómo estoy hoy?')).toBeTruthy();
      expect(screen.getByText('Tu readiness está en 75/100')).toBeTruthy();
    });
  });

  it('calls callAI when user types and sends message', async () => {
    mockCallAI.mockResolvedValue({
      content: 'Mensaje de respuesta de ATLAS',
      provider: 'gemini',
      context_meta: {
        data_freshness: '2h',
        plan_active: true,
        plan_progress: '3/4',
        unread_insights: 1,
        readiness_score: 78,
        readiness_color: 'green',
      } as ChatContextMeta,
    });

    render(<Chat />, { wrapper });

    await waitFor(() => {
      const textarea = screen.getByPlaceholderText(/Escribe tu mensaje/i);
      fireEvent.change(textarea, { target: { value: '¿Qué entreno hoy?' } });
    });

    const button = screen.getByRole('button', { name: '' }) || 
                   screen.getByRole('button', { hidden: true }) ||
                   Array.from(screen.getAllByRole('button')).pop();
    
    if (button) {
      fireEvent.click(button);
    }

    await waitFor(() => {
      expect(mockCallAI).toHaveBeenCalled();
    });
  });

  it('adds error message to chat when callAI fails', async () => {
    mockCallAI.mockRejectedValue(new Error('Network error'));

    render(<Chat />, { wrapper });

    await waitFor(() => {
      const textarea = screen.getByPlaceholderText(/Escribe tu mensaje/i);
      fireEvent.change(textarea, { target: { value: 'Test message' } });
    });

    const button = screen.getByRole('button', { name: '' }) ||
                   Array.from(screen.getAllByRole('button')).pop();
    
    if (button) {
      fireEvent.click(button);
    }

    await waitFor(() => {
      expect(mockAddChatMessage).toHaveBeenCalledWith({
        role: 'assistant',
        content: 'Lo siento, no pude procesar tu mensaje. Inténtalo de nuevo.',
      });
    });
  });

  it('renders context indicator with readiness score when contextMeta is set', async () => {
    mockCallAI.mockResolvedValue({
      content: 'Respuesta',
      provider: 'groq',
      context_meta: {
        data_freshness: '1h',
        plan_active: true,
        plan_progress: '2/4',
        unread_insights: 2,
        readiness_score: 72,
        readiness_color: 'blue',
      } as ChatContextMeta,
    });

    render(<Chat />, { wrapper });

    await waitFor(() => {
      const textarea = screen.getByPlaceholderText(/Escribe tu mensaje/i);
      fireEvent.change(textarea, { target: { value: 'Test' } });
    });

    const button = screen.getByRole('button', { name: '' }) ||
                   Array.from(screen.getAllByRole('button')).pop();
    
    if (button) {
      fireEvent.click(button);
    }

    await waitFor(() => {
      expect(screen.getByText(/Readiness: 72\/100/i)).toBeTruthy();
    }, { timeout: 3000 });
  });
});