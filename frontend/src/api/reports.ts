import apiClient from './client';

export interface DateRange {
  start_date: string;
  end_date: string;
}

export interface AttendanceReportSummary {
  total_records: number;
  total_hours: number;
  avg_hours_per_day: number;
  still_clocked_in: number;
}

export interface DailyBreakdown {
  date: string;
  total_hours: number;
  employees_count: number;
  avg_hours: number;
}

export interface EmployeeBreakdown {
  employee_id: string;
  employee_name: string;
  total_hours: number;
  days_worked: number;
  avg_hours: number;
}

export interface AttendanceRecord {
  id: number;
  date: string;
  employee_id: string;
  employee_name: string;
  first_clock_in: string | null;
  last_clock_out: string | null;
  final_hours: number;
  current_status: string;
  tap_count: number;
}

export interface AttendanceReport {
  date_range: DateRange;
  summary: AttendanceReportSummary;
  daily_breakdown: DailyBreakdown[];
  employee_breakdown: EmployeeBreakdown[];
  records: AttendanceRecord[];
  pagination: {
    page: number;
    page_size: number;
    total_records: number;
  };
}

export interface TILReportSummary {
  total_earned_early: number;
  total_earned_overtime: number;
  total_used: number;
  total_adjusted: number;
  pending_approvals: number;
}

export interface TILBalance {
  employee__employee_id: string;
  employee__employee_name: string;
  total_earned: number;
  total_used: number;
  current_balance: number;
}

export interface TILReport {
  date_range: DateRange;
  summary: TILReportSummary;
  by_type: Array<{ til_type: string; total_hours: number; count: number }>;
  by_employee: Array<{
    employee__employee_id: string;
    employee__employee_name: string;
    total_earned: number;
    total_used: number;
  }>;
  balances: TILBalance[];
  recent_records: Array<{
    id: number;
    employee__employee_name: string;
    til_type: string;
    status: string;
    hours: number;
    date: string;
    reason: string;
  }>;
}

export interface LeaveReportSummary {
  total_requests: number;
  approved: number;
  pending: number;
  rejected: number;
  total_days_approved: number;
}

export interface LeaveReport {
  date_range: DateRange;
  summary: LeaveReportSummary;
  by_type: Array<{
    leave_type: string;
    count: number;
    total_days: number;
    total_hours: number;
  }>;
  by_status: Array<{ status: string; count: number }>;
  by_employee: Array<{
    employee_id: string;
    employee_name: string;
    total_days: number;
    request_count: number;
  }>;
  recent_leaves: Array<{
    id: number;
    employee_name: string;
    leave_type: string;
    status: string;
    start_date: string;
    end_date: string;
    total_days: number;
  }>;
}

export interface TeamReport {
  date: string;
  team_size: number;
  today: {
    clocked_in: number;
    clocked_out: number;
    not_clocked_in: number;
  };
  this_week: {
    total_hours: number;
    avg_hours_per_day: number;
  };
  pending_approvals: {
    til: number;
    leave: number;
    total: number;
  };
  til_balances: Array<{
    employee__employee_id: string;
    employee__employee_name: string;
    current_balance: number;
  }>;
  upcoming_leave: Array<{
    employee_name: string;
    leave_type: string;
    start_date: string;
    end_date: string;
    total_days: number;
  }>;
  team_members: Array<{
    employee_id: string;
    employee_name: string;
    department: string | null;
    status_today: string;
    hours_today: number;
  }>;
}

export interface AttendanceTrend {
  date: string;
  total_hours: number;
  avg_hours: number;
  records: number;
}

export interface DepartmentComparison {
  department: string;
  code: string;
  total_hours: number;
  avg_hours: number;
  total_records: number;
  employees: number;
}

export interface ReportParams {
  start_date?: string;
  end_date?: string;
  preset?: 'this_week' | 'last_week' | 'this_month' | 'last_month' | 'last_quarter' | 'this_year';
  department?: number;
  employee?: string;
  page?: number;
  page_size?: number;
  format?: 'csv' | 'excel' | 'pdf';
  group_by?: 'day' | 'week' | 'month';
}

export const reportsApi = {
  // Attendance Reports
  getAttendanceReport: async (params: ReportParams = {}): Promise<AttendanceReport> => {
    const response = await apiClient.get('/api/reports/attendance/', { params });
    return response.data;
  },

  exportAttendance: async (params: ReportParams = {}): Promise<Blob> => {
    const response = await apiClient.get('/api/reports/attendance/export/', {
      params,
      responseType: 'blob',
    });
    return response.data;
  },

  // TIL Reports
  getTILReport: async (params: ReportParams = {}): Promise<TILReport> => {
    const response = await apiClient.get('/api/reports/til/', { params });
    return response.data;
  },

  exportTIL: async (params: ReportParams = {}): Promise<Blob> => {
    const response = await apiClient.get('/api/reports/til/export/', {
      params,
      responseType: 'blob',
    });
    return response.data;
  },

  // Leave Reports
  getLeaveReport: async (params: ReportParams = {}): Promise<LeaveReport> => {
    const response = await apiClient.get('/api/reports/leaves/', { params });
    return response.data;
  },

  exportLeave: async (params: ReportParams = {}): Promise<Blob> => {
    const response = await apiClient.get('/api/reports/leaves/export/', {
      params,
      responseType: 'blob',
    });
    return response.data;
  },

  // Team Report (Managers)
  getTeamReport: async (): Promise<TeamReport> => {
    const response = await apiClient.get('/api/reports/team/');
    return response.data;
  },

  // Analytics
  getAttendanceTrends: async (params: ReportParams = {}): Promise<{ data: AttendanceTrend[] }> => {
    const response = await apiClient.get('/api/reports/analytics/attendance-trends/', { params });
    return response.data;
  },

  getDepartmentComparison: async (params: ReportParams = {}): Promise<{ departments: DepartmentComparison[] }> => {
    const response = await apiClient.get('/api/reports/analytics/department-comparison/', { params });
    return response.data;
  },
};
