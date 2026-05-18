import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter, useNavigate } from 'react-router-dom';
import { ReadinessDashboard } from '../ReadinessDashboard';
import type { DailyReadinessStatus } from '../../types';

vi.mock('../../hooks/useDashboardData', () => ({
  useDailyReadiness: vi.fn(),
  useRunDailyLoop: vi.fn(),
}));

vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
    circle: (props: any) => <circle {...props} />,
  },
}));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

import { useDailyReadiness, useRunDailyLoop } from '../../hooks/useDashboardData';

const mockUseDailyReadiness = useDailyReadiness as unknown as ReturnType<typeof vi.fn>;
const mockUseRunDailyLoop = useRunDailyLoop as unknown as ReturnType<typeof vi.fn>;

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <BrowserRouter>{children}</BrowserRouter>
);

describe('ReadinessDashboard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockClear();
    vi.useFakeTimers({ shouldAdvanceTime: true });

    let rafStartTime = 0;
    vi.stubGlobal('requestAnimationFrame', (cb: (time: number) => void) => {
      rafStartTime = performance.now();
      const handle = setTimeout(() => cb(rafStartTime + 800), 0) as unknown as number;
      return handle;
    });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders loading skeleton when isLoading is true', () => {
    (mockUseDailyReadiness as ReturnType<typeof vi.fn>).mockReturnValue({
      data: undefined,
      isLoading: true,
    });
    (mockUseRunDailyLoop as ReturnType<typeof vi.fn>).mockReturnValue({
      mutateAsync: vi.fn(),
    });

    render(<ReadinessDashboard />, { wrapper });

    expect(document.querySelector('.animate-pulse')).toBeTruthy();
  });

  it('renders no-data state with update button when has_data is false', async () => {
    (mockUseDailyReadiness as ReturnType<typeof vi.fn>).mockReturnValue({
      data: { has_data: false },
      isLoading: false,
    });
    (mockUseRunDailyLoop as ReturnType<typeof vi.fn>).mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({}),
    });

    render(<ReadinessDashboard />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/No hay datos de readiness/i)).toBeTruthy();
    });
    expect(screen.getByText(/Actualizar datos/i)).toBeTruthy();
  });

  it('calls runLoop.mutateAsync when update button is clicked', async () => {
    const mutateAsync = vi.fn().mockResolvedValue({});
    (mockUseDailyReadiness as ReturnType<typeof vi.fn>).mockReturnValue({
      data: { has_data: false },
      isLoading: false,
    });
    (mockUseRunDailyLoop as ReturnType<typeof vi.fn>).mockReturnValue({ mutateAsync });

    render(<ReadinessDashboard />, { wrapper });

    const button = screen.getByText(/Actualizar datos/i);
    fireEvent.click(button);

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalled();
    });
  });

  it('renders readiness score and category when data is available', async () => {
    const mockData: DailyReadinessStatus = {
      has_data: true,
      readiness_score: 75,
      readiness_category: 'Moderate',
      readiness_color: 'yellow',
      components: {
        body_battery: { value: 65, score: 22.75, weight: '35%' },
        resting_hr: { value: 52, score: 25, weight: '30%', vs_baseline: -2 },
        sleep: { value: 7.2, score: 18, weight: '25%' },
        stress: { value: 35, score: 8, weight: '10%' },
      },
      insights: [],
    };

    (mockUseDailyReadiness as ReturnType<typeof vi.fn>).mockReturnValue({
      data: mockData,
      isLoading: false,
    });
    (mockUseRunDailyLoop as ReturnType<typeof vi.fn>).mockReturnValue({
      mutateAsync: vi.fn(),
    });

    render(<ReadinessDashboard />, { wrapper });

    vi.advanceTimersByTime(800);

    await waitFor(() => {
      expect(screen.getByText('75')).toBeTruthy();
    });
    expect(screen.getByText('Moderate')).toBeTruthy();
  });

  it('renders adaptation message when suggestion is not "mantener"', async () => {
    const mockData: DailyReadinessStatus = {
      has_data: true,
      readiness_score: 55,
      readiness_category: 'Low',
      readiness_color: 'red',
      adaptation: {
        made: true,
        suggestion: 'bajar_intensidad',
        note: 'Tu cuerpo necesita recuperación',
      },
      components: {
        body_battery: { value: 40, score: 14, weight: '35%' },
        resting_hr: { value: 60, score: 20, weight: '30%', vs_baseline: 5 },
        sleep: { value: 5.5, score: 12, weight: '25%' },
        stress: { value: 60, score: 5, weight: '10%' },
      },
      insights: [],
    };

    (mockUseDailyReadiness as ReturnType<typeof vi.fn>).mockReturnValue({
      data: mockData,
      isLoading: false,
    });
    (mockUseRunDailyLoop as ReturnType<typeof vi.fn>).mockReturnValue({
      mutateAsync: vi.fn(),
    });

    render(<ReadinessDashboard />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText(/Bajar intensidad/i)).toBeTruthy();
    });
  });

  it('renders insights when available', async () => {
    const mockData: DailyReadinessStatus = {
      has_data: true,
      readiness_score: 80,
      readiness_category: 'High',
      readiness_color: 'green',
      insights: [
        {
          id: '1',
          priority: 'high',
          title: 'Buen sueño detectado',
          message: '7.5h de sueño mejora tu readiness',
        },
      ],
      components: {
        body_battery: { value: 85, score: 30, weight: '35%' },
        resting_hr: { value: 48, score: 28, weight: '30%', vs_baseline: -3 },
        sleep: { value: 7.5, score: 20, weight: '25%' },
        stress: { value: 20, score: 9, weight: '10%' },
      },
    };

    (mockUseDailyReadiness as ReturnType<typeof vi.fn>).mockReturnValue({
      data: mockData,
      isLoading: false,
    });
    (mockUseRunDailyLoop as ReturnType<typeof vi.fn>).mockReturnValue({
      mutateAsync: vi.fn(),
    });

    render(<ReadinessDashboard />, { wrapper });

    await waitFor(() => {
      expect(screen.getByText('Buen sueño detectado')).toBeTruthy();
    });
  });

  it('navigates to /plan when link is clicked', async () => {
    const mockData: DailyReadinessStatus = {
      has_data: true,
      readiness_score: 70,
      readiness_category: 'Moderate',
      readiness_color: 'blue',
      components: {
        body_battery: { value: 70, score: 24.5, weight: '35%' },
        resting_hr: { value: 54, score: 26, weight: '30%', vs_baseline: 0 },
        sleep: { value: 6.8, score: 17, weight: '25%' },
        stress: { value: 40, score: 7, weight: '10%' },
      },
      insights: [],
    };

    (mockUseDailyReadiness as ReturnType<typeof vi.fn>).mockReturnValue({
      data: mockData,
      isLoading: false,
    });
    (mockUseRunDailyLoop as ReturnType<typeof vi.fn>).mockReturnValue({
      mutateAsync: vi.fn(),
    });

    render(<ReadinessDashboard />, { wrapper });

    const link = screen.getByText(/Ver plan de entrenamiento/i);
    fireEvent.click(link);

    await waitFor(() => {
      expect(mockNavigate).toHaveBeenCalledWith('/plan');
    });
  });
});