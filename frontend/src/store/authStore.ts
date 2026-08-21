import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type UserRole = 'State Epidemiologist' | 'LGA Health Officer' | 'Field Worker' | 'Data Analyst';

interface User {
  email: string;
  role: UserRole;
  name: string;
  id?: number;
}

interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  login: (email: string, role: UserRole) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      isAuthenticated: true,
      user: {
        email: 'yaks@nasrda.gov.ng',
        role: 'State Epidemiologist',
        name: 'Yakubu Tanimu Umar',
        id: 1,
      },
      login: (email: string, role: UserRole) => {
        const name = email.split('@')[0].replace(/[._]/g, ' ');
        const capitalizedName = name
          .split(' ')
          .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
          .join(' ');

        set({
          isAuthenticated: true,
          user: { email, role, name: capitalizedName },
        });
      },
      logout: () => {
        set({
          isAuthenticated: false,
          user: null,
        });
      },
    }),
    {
      name: 'cholera-auth-storage',
    }
  )
);
