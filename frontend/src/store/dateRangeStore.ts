import { create } from 'zustand';

interface DateRangeState {
  start: string | null; // ISO YYYY-MM-DD
  end: string | null;
  setRange: (start: string | null, end: string | null) => void;
  clear: () => void;
}

export const useDateRangeStore = create<DateRangeState>((set) => ({
  start: null,
  end: null,
  setRange: (start, end) => set({ start, end }),
  clear: () => set({ start: null, end: null }),
}));
