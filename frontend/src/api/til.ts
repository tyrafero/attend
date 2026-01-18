import apiClient from './client';

export interface TILBalance {
  id: number;
  employee: number;
  employee_name: string;
  employee_id: string;
  total_earned: string;
  total_used: string;
  current_balance: string;
  last_calculated_at: string;
}

export interface TILRecord {
  id: number;
  employee: number;
  employee_name: string;
  til_type: string;
  til_type_display: string;
  status: string;
  status_display: string;
  hours: string;
  date: string;
  reason: string;
  approved_by: number | null;
  approved_by_name: string | null;
  approved_at: string | null;
  rejection_reason: string;
  created_at: string;
}

export interface ShiftAssignment {
  id: number;
  employee: number;
  employee_name: string;
  shift: number;
  shift_name: string;
  shift_start: string;
  shift_end: string;
  date: string;
  custom_start_time: string | null;
  custom_end_time: string | null;
  pre_approved_early_start: boolean;
  pre_approved_overtime: boolean;
  approved_early_minutes: number;
  approved_overtime_hours: string;
  approved_by: number | null;
  approved_by_name: string | null;
  approved_at: string | null;
  notes: string;
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

export const tilApi = {
  // Get my TIL balance
  getMyBalance: async (): Promise<TILBalance> => {
    const response = await apiClient.get('/api/til/balance/');
    return response.data;
  },

  // Get TIL records
  getRecords: async (): Promise<TILRecord[]> => {
    const response = await apiClient.get('/api/til/records/');
    // Handle paginated response (DRF returns { count, next, previous, results })
    if (response.data && Array.isArray(response.data.results)) {
      return response.data.results;
    }
    // Handle non-paginated response
    return Array.isArray(response.data) ? response.data : [];
  },

  // Create TIL request
  createRecord: async (data: {
    employee: number;
    til_type: string;
    hours: number;
    date: string;
    reason: string;
  }): Promise<TILRecord> => {
    const response = await apiClient.post('/api/til/records/', data);
    return response.data;
  },

  // Approve TIL
  approve: async (id: number): Promise<{ message: string }> => {
    const response = await apiClient.post(`/api/til/records/${id}/approve/`);
    return response.data;
  },

  // Reject TIL
  reject: async (id: number, reason: string): Promise<{ message: string }> => {
    const response = await apiClient.post(`/api/til/records/${id}/reject/`, { reason });
    return response.data;
  },
};

export const shiftApi = {
  // Get all shifts
  getShifts: async (): Promise<Shift[]> => {
    const response = await apiClient.get('/api/shifts/');
    return response.data;
  },

  // Get shift assignments
  getAssignments: async (params?: { date?: string; employee?: number }): Promise<ShiftAssignment[]> => {
    const response = await apiClient.get('/api/shift-assignments/', { params });
    // Handle paginated response
    if (response.data && Array.isArray(response.data.results)) {
      return response.data.results;
    }
    return Array.isArray(response.data) ? response.data : [];
  },

  // Create shift assignment
  createAssignment: async (data: {
    employee: number;
    shift: number;
    date: string;
    custom_start_time?: string;
    custom_end_time?: string;
    pre_approved_early_start?: boolean;
    pre_approved_overtime?: boolean;
    approved_early_minutes?: number;
    approved_overtime_hours?: number;
    notes?: string;
  }): Promise<ShiftAssignment> => {
    const response = await apiClient.post('/api/shift-assignments/', data);
    return response.data;
  },

  // Update shift assignment
  updateAssignment: async (id: number, data: Partial<ShiftAssignment>): Promise<ShiftAssignment> => {
    const response = await apiClient.patch(`/api/shift-assignments/${id}/`, data);
    return response.data;
  },

  // Delete shift assignment
  deleteAssignment: async (id: number): Promise<void> => {
    await apiClient.delete(`/api/shift-assignments/${id}/`);
  },
};
