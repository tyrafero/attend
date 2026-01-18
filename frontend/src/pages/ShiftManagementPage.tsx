import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { shiftApi, type Shift, type ShiftAssignment } from '../api/til';
import { employeeApi } from '../api/attendance';

export function ShiftManagementPage() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);
  const [showAssignModal, setShowAssignModal] = useState(false);
  const [assignForm, setAssignForm] = useState({
    employee: '',
    shift: '',
    date: selectedDate,
    pre_approved_overtime: false,
    approved_overtime_hours: '',
    notes: '',
  });

  // Check if user is manager or HR
  const isAuthorized = user?.employee_profile?.role === 'MANAGER' || user?.employee_profile?.role === 'HR_ADMIN';

  // Fetch shifts
  const { data: shifts, isLoading: shiftsLoading } = useQuery({
    queryKey: ['shifts'],
    queryFn: shiftApi.getShifts,
  });

  // Fetch shift assignments
  const { data: assignments, isLoading: assignmentsLoading } = useQuery({
    queryKey: ['shift-assignments', selectedDate],
    queryFn: () => shiftApi.getAssignments({ date: selectedDate }),
  });

  // Fetch employees (for assignment form)
  const { data: employees } = useQuery({
    queryKey: ['employees'],
    queryFn: employeeApi.getEmployees,
  });

  // Create assignment mutation
  const createAssignment = useMutation({
    mutationFn: shiftApi.createAssignment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shift-assignments'] });
      setShowAssignModal(false);
      setAssignForm({
        employee: '',
        shift: '',
        date: selectedDate,
        pre_approved_overtime: false,
        approved_overtime_hours: '',
        notes: '',
      });
    },
  });

  // Delete assignment mutation
  const deleteAssignment = useMutation({
    mutationFn: shiftApi.deleteAssignment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['shift-assignments'] });
    },
  });

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleAssignSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createAssignment.mutate({
      employee: Number(assignForm.employee),
      shift: Number(assignForm.shift),
      date: assignForm.date,
      pre_approved_overtime: assignForm.pre_approved_overtime,
      approved_overtime_hours: assignForm.pre_approved_overtime ? Number(assignForm.approved_overtime_hours) : undefined,
      notes: assignForm.notes || undefined,
    });
  };

  if (!isAuthorized) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
        <div className="bg-white rounded-xl shadow-lg p-8 text-center">
          <h1 className="text-2xl font-bold text-red-600 mb-4">Access Denied</h1>
          <p className="text-gray-600 mb-4">You do not have permission to access this page.</p>
          <button
            onClick={() => navigate('/dashboard')}
            className="px-4 py-2 rounded-lg text-white font-medium"
            style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}
          >
            Back to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
      {/* Header */}
      <header className="bg-white shadow-lg">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-4">
              <img
                src="https://www.digitalcinema.com.au/media/logo/stores/1/dc-logo-300px.png"
                alt="Digital Cinema"
                className="h-10"
              />
              <div>
                <h1 className="text-xl font-bold text-gray-900">Shift Management</h1>
                <p className="text-xs text-gray-500">
                  {user?.employee_profile?.role === 'HR_ADMIN' ? 'HR Admin' : 'Manager'} View
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => navigate('/dashboard')}
                className="text-sm px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors"
                style={{ color: '#667eea' }}
              >
                Dashboard
              </button>
              <button
                onClick={handleLogout}
                className="text-white px-4 py-2 rounded-lg hover:opacity-90 transition-colors text-sm font-medium"
                style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Shift Templates */}
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h2 className="text-lg font-bold mb-4 text-gray-900">Shift Templates</h2>
            {shiftsLoading ? (
              <p className="text-gray-500">Loading...</p>
            ) : (
              <div className="space-y-3">
                {shifts?.map((shift: Shift) => (
                  <div key={shift.id} className="p-3 bg-gray-50 rounded-lg">
                    <div className="flex justify-between items-start">
                      <div>
                        <p className="font-semibold text-gray-900">{shift.name}</p>
                        <p className="text-sm text-gray-600">
                          {shift.start_time.slice(0, 5)} - {shift.end_time.slice(0, 5)}
                        </p>
                      </div>
                      <span className="text-xs px-2 py-1 bg-purple-100 text-purple-700 rounded-full">
                        {shift.scheduled_hours}h
                      </span>
                    </div>
                    <div className="mt-2 text-xs text-gray-500">
                      <span>Grace: {shift.early_arrival_grace_minutes}min early</span>
                      {shift.department_name && (
                        <span className="ml-2">| {shift.department_name}</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Shift Assignments */}
          <div className="lg:col-span-2 bg-white rounded-xl shadow-lg p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold text-gray-900">Shift Assignments</h2>
              <div className="flex items-center gap-3">
                <input
                  type="date"
                  value={selectedDate}
                  onChange={(e) => setSelectedDate(e.target.value)}
                  className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
                <button
                  onClick={() => setShowAssignModal(true)}
                  className="px-4 py-2 rounded-lg text-white text-sm font-medium"
                  style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}
                >
                  + Assign Shift
                </button>
              </div>
            </div>

            {assignmentsLoading ? (
              <p className="text-gray-500">Loading...</p>
            ) : assignments && assignments.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Employee</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Shift</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Time</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">OT Approved</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {assignments.map((assignment: ShiftAssignment, index: number) => (
                      <tr key={assignment.id} className={index % 2 === 0 ? 'bg-gray-50' : 'bg-white'}>
                        <td className="px-3 py-3 text-sm text-gray-900 font-medium">
                          {assignment.employee_name}
                        </td>
                        <td className="px-3 py-3 text-sm text-gray-700">
                          {assignment.shift_name}
                        </td>
                        <td className="px-3 py-3 text-sm text-gray-700">
                          {assignment.shift_start?.slice(0, 5)} - {assignment.shift_end?.slice(0, 5)}
                        </td>
                        <td className="px-3 py-3 text-sm">
                          {assignment.pre_approved_overtime ? (
                            <span className="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs">
                              {assignment.approved_overtime_hours}h
                            </span>
                          ) : (
                            <span className="text-gray-400">-</span>
                          )}
                        </td>
                        <td className="px-3 py-3 text-sm">
                          <button
                            onClick={() => {
                              if (confirm('Delete this shift assignment?')) {
                                deleteAssignment.mutate(assignment.id);
                              }
                            }}
                            className="text-red-600 hover:text-red-800 text-xs"
                          >
                            Delete
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-gray-500 text-center py-8">No shift assignments for this date</p>
            )}
          </div>
        </div>
      </main>

      {/* Assign Shift Modal */}
      {showAssignModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Assign Shift</h3>
            <form onSubmit={handleAssignSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Employee</label>
                <select
                  value={assignForm.employee}
                  onChange={(e) => setAssignForm({ ...assignForm, employee: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  required
                >
                  <option value="">Select employee...</option>
                  {employees?.map((emp) => (
                    <option key={emp.id} value={emp.id}>
                      {emp.employee_name} ({emp.employee_id})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Shift</label>
                <select
                  value={assignForm.shift}
                  onChange={(e) => setAssignForm({ ...assignForm, shift: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  required
                >
                  <option value="">Select shift...</option>
                  {shifts?.map((shift: Shift) => (
                    <option key={shift.id} value={shift.id}>
                      {shift.name} ({shift.start_time.slice(0, 5)} - {shift.end_time.slice(0, 5)})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
                <input
                  type="date"
                  value={assignForm.date}
                  onChange={(e) => setAssignForm({ ...assignForm, date: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  required
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="preApprovedOT"
                  checked={assignForm.pre_approved_overtime}
                  onChange={(e) => setAssignForm({ ...assignForm, pre_approved_overtime: e.target.checked })}
                  className="rounded border-gray-300"
                />
                <label htmlFor="preApprovedOT" className="text-sm text-gray-700">Pre-approve overtime</label>
              </div>
              {assignForm.pre_approved_overtime && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Approved OT Hours</label>
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    max="8"
                    value={assignForm.approved_overtime_hours}
                    onChange={(e) => setAssignForm({ ...assignForm, approved_overtime_hours: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                    placeholder="e.g., 2"
                  />
                </div>
              )}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Notes (optional)</label>
                <textarea
                  value={assignForm.notes}
                  onChange={(e) => setAssignForm({ ...assignForm, notes: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  rows={2}
                  placeholder="Any special instructions..."
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowAssignModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createAssignment.isPending}
                  className="flex-1 px-4 py-2 rounded-lg text-white font-medium"
                  style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}
                >
                  {createAssignment.isPending ? 'Assigning...' : 'Assign'}
                </button>
              </div>
              {createAssignment.isError && (
                <p className="text-red-600 text-sm text-center">Failed to assign shift. Please try again.</p>
              )}
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
