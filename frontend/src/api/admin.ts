import apiClient from './client';

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
  default_shift: number | null;
  default_shift_name: string | null;
  is_active: boolean;
  username: string;
  created_at: string;
  updated_at: string;
}

export interface Department {
  id: number;
  code: string;
  name: string;
  description: string;
  manager: number | null;
  manager_name: string | null;
  employee_count: number;
  is_active: boolean;
  created_at: string;
}

export interface Shift {
  id: number;
  code: string;
  name: string;
  start_time: string;
  end_time: string;
  scheduled_hours: string;
  break_duration_hours: string;
  early_arrival_grace_minutes: number;
  late_departure_grace_minutes: number;
  department: number | null;
  department_name: string | null;
  is_active: boolean;
}

export interface CreateEmployeeData {
  employee_id: string;
  employee_name: string;
  email: string;
  department: number;
  role: string;
  manager?: number | null;
  default_shift?: number | null;
  username: string;
  password: string;
  pin: string;
}

export interface UpdateEmployeeData {
  employee_name?: string;
  email?: string;
  department?: number;
  role?: string;
  manager?: number | null;
  default_shift?: number | null;
  is_active?: boolean;
  new_password?: string;
  new_pin?: string;
}

export interface UpdateDepartmentData {
  name?: string;
  description?: string;
  manager?: number | null;
  is_active?: boolean;
}

export interface DailyRecord {
  id: number;
  date: string;
  first_clock_in: string | null;
  last_clock_out: string | null;
  raw_hours: number;
  final_hours: number;
  status: string;
}

export interface EmployeeTimesheet {
  employee_id: string;
  employee_name: string;
  department: string | null;
  role: string;
  email: string | null;
  default_shift: string | null;
  total_hours: number;
  days_worked: number;
  daily_records: DailyRecord[];
}

export interface TeamTimesheetResponse {
  start_date: string;
  end_date: string;
  team_count: number;
  timesheet: EmployeeTimesheet[];
}

// Helper to extract array from paginated response
const extractResults = <T>(data: any): T[] => {
  if (data && Array.isArray(data.results)) {
    return data.results;
  }
  return Array.isArray(data) ? data : [];
};

export const adminApi = {
  // Employees
  getEmployees: async (params?: { department?: number; role?: string; show_inactive?: boolean }): Promise<Employee[]> => {
    const response = await apiClient.get('/api/employees/', { params });
    return extractResults<Employee>(response.data);
  },

  getEmployee: async (id: number): Promise<Employee> => {
    const response = await apiClient.get(`/api/employees/${id}/`);
    return response.data;
  },

  createEmployee: async (data: CreateEmployeeData): Promise<Employee> => {
    const response = await apiClient.post('/api/employees/', data);
    return response.data;
  },

  updateEmployee: async (id: number, data: UpdateEmployeeData): Promise<Employee> => {
    const response = await apiClient.patch(`/api/employees/${id}/`, data);
    return response.data;
  },

  deleteEmployee: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/employees/${id}/`);
  },

  getManagers: async (): Promise<Employee[]> => {
    const response = await apiClient.get('/api/employees/managers/');
    return extractResults<Employee>(response.data);
  },

  getTeam: async (): Promise<Employee[]> => {
    const response = await apiClient.get('/api/employees/team/');
    return extractResults<Employee>(response.data);
  },

  getTeamTimesheet: async (startDate: string, endDate: string): Promise<TeamTimesheetResponse> => {
    const response = await apiClient.get('/api/employees/team_timesheet/', {
      params: { start_date: startDate, end_date: endDate }
    });
    return response.data;
  },

  // Departments
  getDepartments: async (): Promise<Department[]> => {
    const response = await apiClient.get('/api/departments/');
    return extractResults<Department>(response.data);
  },

  getDepartment: async (id: number): Promise<Department> => {
    const response = await apiClient.get(`/api/departments/${id}/`);
    return response.data;
  },

  updateDepartment: async (id: number, data: UpdateDepartmentData): Promise<Department> => {
    const response = await apiClient.patch(`/api/departments/${id}/`, data);
    return response.data;
  },

  // Shifts
  getShifts: async (): Promise<Shift[]> => {
    const response = await apiClient.get('/api/shifts/');
    return extractResults<Shift>(response.data);
  },

  getShift: async (id: number): Promise<Shift> => {
    const response = await apiClient.get(`/api/shifts/${id}/`);
    return response.data;
  },

  createShift: async (data: Partial<Shift>): Promise<Shift> => {
    const response = await apiClient.post('/api/shifts/', data);
    return response.data;
  },

  updateShift: async (id: number, data: Partial<Shift>): Promise<Shift> => {
    const response = await apiClient.patch(`/api/shifts/${id}/`, data);
    return response.data;
  },

  deleteShift: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/shifts/${id}/`);
  },
};
