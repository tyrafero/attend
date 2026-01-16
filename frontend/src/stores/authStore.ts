import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authApi } from '../api/auth';
import type { User } from '../types';

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  isAuthenticated: boolean;

  login: (username: string, password: string) => Promise<void>;
  loginWithPIN: (pin: string) => Promise<void>;
  logout: () => Promise<void>;
  setTokens: (access: string, refresh: string) => void;

  isManager: () => boolean;
  isHRAdmin: () => boolean;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,

      login: async (username: string, password: string) => {
        try {
          const response = await authApi.login(username, password);

          // Store tokens in localStorage (for axios interceptor)
          localStorage.setItem('accessToken', response.access);
          localStorage.setItem('refreshToken', response.refresh);
          localStorage.setItem('user', JSON.stringify(response.user));

          set({
            user: response.user,
            accessToken: response.access,
            refreshToken: response.refresh,
            isAuthenticated: true,
          });
        } catch (error) {
          throw error;
        }
      },

      loginWithPIN: async (pin: string) => {
        try {
          const response = await authApi.loginWithPIN(pin);

          // Store tokens in localStorage
          localStorage.setItem('accessToken', response.access);
          localStorage.setItem('refreshToken', response.refresh);
          localStorage.setItem('user', JSON.stringify(response.user));

          set({
            user: response.user,
            accessToken: response.access,
            refreshToken: response.refresh,
            isAuthenticated: true,
          });
        } catch (error) {
          throw error;
        }
      },

      logout: async () => {
        const refreshToken = get().refreshToken;

        try {
          if (refreshToken) {
            await authApi.logout(refreshToken);
          }
        } catch (error) {
          console.error('Logout error:', error);
        } finally {
          // Clear all storage
          localStorage.removeItem('accessToken');
          localStorage.removeItem('refreshToken');
          localStorage.removeItem('user');

          set({
            user: null,
            accessToken: null,
            refreshToken: null,
            isAuthenticated: false,
          });
        }
      },

      setTokens: (access: string, refresh: string) => {
        localStorage.setItem('accessToken', access);
        localStorage.setItem('refreshToken', refresh);

        set({
          accessToken: access,
          refreshToken: refresh,
        });
      },

      isManager: () => {
        const user = get().user;
        return user?.employee_profile?.role === 'MANAGER' || user?.employee_profile?.role === 'HR_ADMIN';
      },

      isHRAdmin: () => {
        const user = get().user;
        return user?.employee_profile?.role === 'HR_ADMIN';
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
