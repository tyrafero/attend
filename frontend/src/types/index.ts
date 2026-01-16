// API Response Types

export interface EmployeeProfile {
  id: number;
  employee_id: string;
  employee_name: string;
  email: string;
  department: number;
  department_name?: string;
  role: 'EMPLOYEE' | 'MANAGER' | 'HR_ADMIN';
  manager?: number;
  manager_name?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface User {
  id: number;
  username: string;
  email: string;
  first_name: string;
  last_name: string;
  employee_profile?: EmployeeProfile;
}

export interface LoginResponse {
  user: User;
  access: string;
  refresh: string;
  message?: string;
}

export interface Department {
  id: number;
  code: string;
  name: string;
  description: string;
  manager?: number;
  manager_name?: string;
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
  scheduled_hours: number;
  break_duration_hours: number;
  early_arrival_grace_minutes: number;
  late_departure_grace_minutes: number;
  department?: number;
  department_name?: string;
  is_active: boolean;
  created_at: string;
}

export interface DailySummary {
  id: number;
  date: string;
  employee_id: string;
  employee_name: string;
  first_clock_in: string | null;
  last_clock_out: string | null;
  raw_hours: number;
  break_deduction: number;
  final_hours: number;
  current_status: 'IN' | 'OUT';
  tap_count: number;
}

export interface AttendanceTap {
  id: number;
  timestamp: string;
  employee_id: string;
  employee_name: string;
  action: 'IN' | 'OUT';
  notes: string;
  created_at: string;
}

export interface ClockActionResponse {
  success: boolean;
  action: 'IN' | 'OUT';
  employee_id: string;
  employee_name: string;
  timestamp: string;
  time: string;
  hours_worked: string | null;
  authenticated_via: 'jwt' | 'pin' | 'nfc';
  message: string;
}

export interface CurrentStatus {
  employee_id: string;
  employee_name: string;
  date: string;
  current_status: 'IN' | 'OUT';
  first_clock_in: string | null;
  last_clock_out: string | null;
  hours_worked: number;
  tap_count: number;
}

export interface ApiError {
  detail?: string;
  [key: string]: any;
}
