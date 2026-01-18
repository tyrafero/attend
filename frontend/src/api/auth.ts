import apiClient from './client';
import type { LoginResponse } from '../types';

export const authApi = {
  // Username/password login
  login: async (username: string, password: string): Promise<LoginResponse> => {
    const response = await apiClient.post('/api/auth/login/', { username, password });
    return response.data;
  },

  // PIN login (kiosk mode)
  loginWithPIN: async (pin: string): Promise<LoginResponse> => {
    const response = await apiClient.post('/api/auth/login/pin/', { pin });
    return response.data;
  },

  // Logout (blacklist refresh token)
  logout: async (refreshToken: string): Promise<void> => {
    await apiClient.post('/api/auth/logout/', { refresh: refreshToken });
  },

  // Get current user
  getCurrentUser: async () => {
    const response = await apiClient.get('/api/auth/me/');
    return response.data;
  },

  // Change PIN
  changePIN: async (oldPin: string, newPin: string) => {
    const response = await apiClient.post('/api/auth/change-pin/', {
      old_pin: oldPin,
      new_pin: newPin,
    });
    return response.data;
  },

  // Change password
  changePassword: async (oldPassword: string, newPassword: string) => {
    const response = await apiClient.post('/api/auth/change-password/', {
      old_password: oldPassword,
      new_password: newPassword,
    });
    return response.data;
  },
};
