import apiClient from './client';
import type { ClockActionResponse, CurrentStatus, DailySummary } from '../types';

export interface Employee {
  id: number;
  employee_id: string;
  employee_name: string;
  email: string;
  department: number;
  department_name: string;
  role: string;
  manager: number | null;
  manager_name: string | null;
  is_active: boolean;
}

export const employeeApi = {
  // Get all employees (for managers/HR)
  getEmployees: async (): Promise<Employee[]> => {
    const response = await apiClient.get('/api/employees/');
    return response.data;
  },

  // Get team members (for managers)
  getTeam: async (): Promise<Employee[]> => {
    const response = await apiClient.get('/api/employees/team/');
    return response.data;
  },

  // Get current user's profile
  getMe: async (): Promise<Employee> => {
    const response = await apiClient.get('/api/employees/me/');
    return response.data;
  },
};

export const attendanceApi = {
  // Clock in/out
  clock: async (data?: { pin?: string; nfc_id?: string }): Promise<ClockActionResponse> => {
    const response = await apiClient.post('/api/attendance/clock/', data || {});
    return response.data;
  },

  // Get current status
  getCurrentStatus: async (): Promise<CurrentStatus> => {
    const response = await apiClient.get('/api/attendance/me/current/');
    return response.data;
  },

  // Get my attendance summary
  getMySummary: async (startDate?: string, endDate?: string): Promise<DailySummary[]> => {
    const params: any = {};
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;

    const response = await apiClient.get('/api/attendance/me/summary/', { params });
    return response.data;
  },
};
