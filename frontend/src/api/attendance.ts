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
    // Handle paginated response (DRF returns { count, next, previous, results })
    if (response.data && Array.isArray(response.data.results)) {
      return response.data.results;
    }
    return Array.isArray(response.data) ? response.data : [];
  },

  // Get team members (for managers)
  getTeam: async (): Promise<Employee[]> => {
    const response = await apiClient.get('/api/employees/team/');
    // Handle paginated response
    if (response.data && Array.isArray(response.data.results)) {
      return response.data.results;
    }
    return Array.isArray(response.data) ? response.data : [];
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

  // Get team member's attendance (for managers)
  getTeamAttendance: async (employeeId: string, startDate?: string, endDate?: string): Promise<DailySummary[]> => {
    const params: any = { employee_id: employeeId };
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;

    const response = await apiClient.get('/api/daily-summaries/', { params });
    // Handle paginated response
    if (response.data && Array.isArray(response.data.results)) {
      return response.data.results;
    }
    return Array.isArray(response.data) ? response.data : [];
  },

  // Update daily summary (managers only)
  updateDailySummary: async (id: number, data: {
    first_clock_in?: string;
    last_clock_out?: string;
    reason: string;
  }) => {
    const response = await apiClient.patch(`/api/daily-summaries/${id}/`, data);
    return response.data;
  },

  // Create manual entry (managers only)
  createManualEntry: async (data: {
    employee_id: string;
    date: string;
    first_clock_in: string;
    last_clock_out: string;
    reason: string;
  }) => {
    const response = await apiClient.post('/api/daily-summaries/create_manual_entry/', data);
    return response.data;
  },
};
