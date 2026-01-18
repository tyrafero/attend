import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { leaveApi, type LeaveRecord } from '../api/leave';
import { tilApi } from '../api/til';

export function LeavePage() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [showApplyModal, setShowApplyModal] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [selectedLeave, setSelectedLeave] = useState<LeaveRecord | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [applyForm, setApplyForm] = useState({
    leave_type: 'ANNUAL',
    start_date: new Date().toISOString().split('T')[0],
    end_date: new Date().toISOString().split('T')[0],
    reason: '',
  });

  const isManager = user?.employee_profile?.role === 'MANAGER' || user?.employee_profile?.role === 'HR_ADMIN';
  const isAuthenticated = !!user?.employee_profile;

  // Fetch leave records
  const { data: leaveRecords, isLoading } = useQuery({
    queryKey: ['leaves'],
    queryFn: leaveApi.getLeaves,
    enabled: isAuthenticated,
  });

  // Fetch pending leaves (for managers)
  const { data: pendingLeaves } = useQuery({
    queryKey: ['leaves', 'pending'],
    queryFn: leaveApi.getPending,
    enabled: isAuthenticated && isManager,
  });

  // Fetch TIL balance (for TIL leave type)
  const { data: tilBalance } = useQuery({
    queryKey: ['til', 'balance'],
    queryFn: tilApi.getMyBalance,
    enabled: isAuthenticated,
  });

  // Apply for leave
  const applyLeave = useMutation({
    mutationFn: leaveApi.createLeave,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leaves'] });
      setShowApplyModal(false);
      setApplyForm({
        leave_type: 'ANNUAL',
        start_date: new Date().toISOString().split('T')[0],
        end_date: new Date().toISOString().split('T')[0],
        reason: '',
      });
    },
  });

  // Approve leave
  const approveLeave = useMutation({
    mutationFn: ({ id, comments }: { id: number; comments?: string }) => leaveApi.approve(id, comments),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leaves'] });
    },
  });

  // Reject leave
  const rejectLeave = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) => leaveApi.reject(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leaves'] });
      setShowRejectModal(false);
      setRejectReason('');
      setSelectedLeave(null);
    },
  });

  // Cancel leave
  const cancelLeave = useMutation({
    mutationFn: leaveApi.cancel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leaves'] });
    },
  });

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleApplySubmit = (e: React.FormEvent) => {
    e.preventDefault();
    applyLeave.mutate(applyForm);
  };

  const handleReject = () => {
    if (selectedLeave) {
      rejectLeave.mutate({ id: selectedLeave.id, reason: rejectReason });
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'APPROVED': return 'bg-green-100 text-green-700';
      case 'REJECTED': return 'bg-red-100 text-red-700';
      case 'PENDING': return 'bg-yellow-100 text-yellow-700';
      case 'CANCELLED': return 'bg-gray-100 text-gray-500';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'ANNUAL': return 'bg-blue-100 text-blue-700';
      case 'SICK': return 'bg-red-100 text-red-700';
      case 'TIL': return 'bg-purple-100 text-purple-700';
      case 'UNPAID': return 'bg-gray-100 text-gray-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  const records = Array.isArray(leaveRecords) ? leaveRecords : [];
  const pending = Array.isArray(pendingLeaves) ? pendingLeaves : [];

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
                <h1 className="text-xl font-bold text-gray-900">Leave Management</h1>
                <p className="text-xs text-gray-500">Apply for and manage leave</p>
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
        {/* Apply for Leave Card */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-lg font-bold text-gray-900 mb-2">Apply for Leave</h2>
              {tilBalance && (
                <p className="text-sm text-gray-500">
                  TIL Balance: <span className="font-semibold" style={{ color: '#667eea' }}>{tilBalance.current_balance}h</span>
                </p>
              )}
            </div>
            <button
              onClick={() => setShowApplyModal(true)}
              className="px-6 py-3 rounded-lg text-white font-medium"
              style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}
            >
              Apply for Leave
            </button>
          </div>
        </div>

        {/* Pending Approvals (Managers Only) */}
        {isManager && pending.length > 0 && (
          <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Pending Approvals ({pending.length})</h2>
            <div className="space-y-3">
              {pending.map((leave) => (
                <div key={leave.id} className="flex items-center justify-between p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                  <div>
                    <p className="font-semibold text-gray-900">{leave.employee_name}</p>
                    <p className="text-sm text-gray-600">
                      <span className={`px-2 py-0.5 rounded-full text-xs ${getTypeColor(leave.leave_type)}`}>
                        {leave.leave_type_display}
                      </span>
                      <span className="ml-2">
                        {new Date(leave.start_date).toLocaleDateString()} - {new Date(leave.end_date).toLocaleDateString()}
                      </span>
                      <span className="ml-2 text-gray-500">({leave.total_days} days)</span>
                    </p>
                    {leave.reason && <p className="text-sm text-gray-500 mt-1">{leave.reason}</p>}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => approveLeave.mutate({ id: leave.id })}
                      disabled={approveLeave.isPending}
                      className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => {
                        setSelectedLeave(leave);
                        setShowRejectModal(true);
                      }}
                      className="px-4 py-2 bg-red-600 text-white rounded-lg text-sm font-medium hover:bg-red-700"
                    >
                      Reject
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Leave History */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">Leave History</h2>
          {isLoading ? (
            <p className="text-gray-500 text-center py-8">Loading...</p>
          ) : records.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    {isManager && <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Employee</th>}
                    <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Type</th>
                    <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Dates</th>
                    <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Days</th>
                    <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Reason</th>
                    <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Status</th>
                    <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {records.map((leave, index) => (
                    <tr key={leave.id} className={index % 2 === 0 ? 'bg-gray-50' : 'bg-white'}>
                      {isManager && <td className="px-3 py-3 text-sm text-gray-900">{leave.employee_name}</td>}
                      <td className="px-3 py-3 text-sm">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getTypeColor(leave.leave_type)}`}>
                          {leave.leave_type_display}
                        </span>
                      </td>
                      <td className="px-3 py-3 text-sm text-gray-700">
                        {new Date(leave.start_date).toLocaleDateString()} - {new Date(leave.end_date).toLocaleDateString()}
                      </td>
                      <td className="px-3 py-3 text-sm font-bold" style={{ color: '#667eea' }}>
                        {leave.total_days}
                      </td>
                      <td className="px-3 py-3 text-sm text-gray-600 max-w-xs truncate" title={leave.reason}>
                        {leave.reason || '-'}
                      </td>
                      <td className="px-3 py-3 text-sm">
                        <span className={`px-2 py-1 rounded-full text-xs font-semibold ${getStatusColor(leave.status)}`}>
                          {leave.status_display}
                        </span>
                        {leave.rejection_reason && (
                          <p className="text-xs text-red-500 mt-1" title={leave.rejection_reason}>
                            {leave.rejection_reason.substring(0, 30)}...
                          </p>
                        )}
                      </td>
                      <td className="px-3 py-3 text-sm">
                        {leave.status === 'PENDING' && leave.employee_id === user?.employee_profile?.employee_id && (
                          <button
                            onClick={() => {
                              if (confirm('Cancel this leave request?')) {
                                cancelLeave.mutate(leave.id);
                              }
                            }}
                            className="text-red-600 hover:text-red-800 text-xs"
                          >
                            Cancel
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">No leave records found</p>
          )}
        </div>
      </main>

      {/* Apply Leave Modal */}
      {showApplyModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Apply for Leave</h3>
            <form onSubmit={handleApplySubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Leave Type</label>
                <select
                  value={applyForm.leave_type}
                  onChange={(e) => setApplyForm({ ...applyForm, leave_type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  required
                >
                  <option value="ANNUAL">Annual Leave</option>
                  <option value="SICK">Sick Leave</option>
                  <option value="UNPAID">Unpaid Leave</option>
                  <option value="TIL">Time in Lieu (TIL Balance: {tilBalance?.current_balance || 0}h)</option>
                </select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Start Date</label>
                  <input
                    type="date"
                    value={applyForm.start_date}
                    onChange={(e) => setApplyForm({ ...applyForm, start_date: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">End Date</label>
                  <input
                    type="date"
                    value={applyForm.end_date}
                    onChange={(e) => setApplyForm({ ...applyForm, end_date: e.target.value })}
                    min={applyForm.start_date}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                    required
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Reason (optional)</label>
                <textarea
                  value={applyForm.reason}
                  onChange={(e) => setApplyForm({ ...applyForm, reason: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  rows={3}
                  placeholder="Reason for leave..."
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowApplyModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={applyLeave.isPending}
                  className="flex-1 px-4 py-2 rounded-lg text-white font-medium"
                  style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}
                >
                  {applyLeave.isPending ? 'Submitting...' : 'Submit'}
                </button>
              </div>
              {applyLeave.isError && (
                <p className="text-red-600 text-sm text-center">Failed to submit leave request. Please try again.</p>
              )}
            </form>
          </div>
        </div>
      )}

      {/* Reject Modal */}
      {showRejectModal && selectedLeave && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Reject Leave Request</h3>
            <p className="text-sm text-gray-600 mb-4">
              Rejecting leave request from <strong>{selectedLeave.employee_name}</strong> for{' '}
              {selectedLeave.total_days} days ({new Date(selectedLeave.start_date).toLocaleDateString()} - {new Date(selectedLeave.end_date).toLocaleDateString()})
            </p>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-1">Reason for rejection</label>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                rows={3}
                placeholder="Explain why this request is being rejected..."
                required
              />
            </div>
            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => {
                  setShowRejectModal(false);
                  setRejectReason('');
                  setSelectedLeave(null);
                }}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleReject}
                disabled={rejectLeave.isPending || !rejectReason.trim()}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 disabled:opacity-50"
              >
                {rejectLeave.isPending ? 'Rejecting...' : 'Confirm Reject'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
