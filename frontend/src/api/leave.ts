import apiClient from './client';

export interface LeaveRecord {
  id: number;
  employee_profile: number;
  employee_id: string;
  employee_name: string;
  leave_type: string;
  leave_type_display: string;
  start_date: string;
  end_date: string;
  reason: string;
  status: string;
  status_display: string;
  approved_by: number | null;
  approved_by_name: string | null;
  approved_at: string | null;
  rejection_reason: string;
  manager_comments: string;
  hours_per_day: string;
  total_days: number;
  total_hours: string;
  created_at: string;
  updated_at: string;
}

export const leaveApi = {
  // Get all leave records (filtered by role)
  getLeaves: async (): Promise<LeaveRecord[]> => {
    const response = await apiClient.get('/api/leaves/');
    // Handle paginated response
    if (response.data && Array.isArray(response.data.results)) {
      return response.data.results;
    }
    return Array.isArray(response.data) ? response.data : [];
  },

  // Get pending leave requests (managers only)
  getPending: async (): Promise<LeaveRecord[]> => {
    const response = await apiClient.get('/api/leaves/pending/');
    return Array.isArray(response.data) ? response.data : [];
  },

  // Get a single leave record
  getLeave: async (id: number): Promise<LeaveRecord> => {
    const response = await apiClient.get(`/api/leaves/${id}/`);
    return response.data;
  },

  // Create a new leave request
  createLeave: async (data: {
    leave_type: string;
    start_date: string;
    end_date: string;
    reason?: string;
  }): Promise<LeaveRecord> => {
    const response = await apiClient.post('/api/leaves/', data);
    return response.data;
  },

  // Approve a leave request (managers only)
  approve: async (id: number, comments?: string): Promise<{ message: string }> => {
    const response = await apiClient.post(`/api/leaves/${id}/approve/`, { comments });
    return response.data;
  },

  // Reject a leave request (managers only)
  reject: async (id: number, reason: string): Promise<{ message: string }> => {
    const response = await apiClient.post(`/api/leaves/${id}/reject/`, { reason });
    return response.data;
  },

  // Cancel a leave request (by employee)
  cancel: async (id: number): Promise<{ message: string }> => {
    const response = await apiClient.post(`/api/leaves/${id}/cancel/`);
    return response.data;
  },
};
