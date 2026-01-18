import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { tilApi, type TILRecord } from '../api/til';

export function TILPage() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [showRequestModal, setShowRequestModal] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [selectedRecord, setSelectedRecord] = useState<TILRecord | null>(null);
  const [rejectReason, setRejectReason] = useState('');
  const [requestForm, setRequestForm] = useState({
    til_type: 'USED',
    hours: '',
    date: new Date().toISOString().split('T')[0],
    reason: '',
  });

  const isManager = user?.employee_profile?.role === 'MANAGER' || user?.employee_profile?.role === 'HR_ADMIN';
  const isAuthenticated = !!user?.employee_profile;

  // Fetch TIL balance (only when authenticated)
  const { data: tilBalance } = useQuery({
    queryKey: ['til', 'balance'],
    queryFn: tilApi.getMyBalance,
    enabled: isAuthenticated,
  });

  // Fetch TIL records (only when authenticated)
  const { data: tilRecords, isLoading } = useQuery({
    queryKey: ['til', 'records'],
    queryFn: tilApi.getRecords,
    enabled: isAuthenticated,
  });

  // Create TIL request
  const createRequest = useMutation({
    mutationFn: tilApi.createRecord,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['til'] });
      setShowRequestModal(false);
      setRequestForm({ til_type: 'USED', hours: '', date: new Date().toISOString().split('T')[0], reason: '' });
    },
  });

  // Approve TIL
  const approveTIL = useMutation({
    mutationFn: tilApi.approve,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['til'] });
    },
  });

  // Reject TIL
  const rejectTIL = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) => tilApi.reject(id, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['til'] });
      setShowRejectModal(false);
      setRejectReason('');
      setSelectedRecord(null);
    },
  });

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleRequestSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    createRequest.mutate({
      employee: user?.employee_profile?.id || 0,
      til_type: requestForm.til_type,
      hours: Number(requestForm.hours),
      date: requestForm.date,
      reason: requestForm.reason,
    });
  };

  const handleReject = () => {
    if (selectedRecord) {
      rejectTIL.mutate({ id: selectedRecord.id, reason: rejectReason });
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'APPROVED': return 'bg-green-100 text-green-700';
      case 'REJECTED': return 'bg-red-100 text-red-700';
      case 'PENDING': return 'bg-yellow-100 text-yellow-700';
      default: return 'bg-gray-100 text-gray-700';
    }
  };

  const getTypeColor = (type: string) => {
    if (type === 'EARNED_OT' || type === 'EARNED_EARLY') {
      return 'bg-blue-100 text-blue-700';
    }
    if (type === 'USED') {
      return 'bg-purple-100 text-purple-700';
    }
    return 'bg-gray-100 text-gray-700'; // ADJUSTED or unknown
  };

  // Filter pending records for managers (ensure tilRecords is an array)
  const records = Array.isArray(tilRecords) ? tilRecords : [];
  const pendingRecords = records.filter(r => r.status === 'PENDING');

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
                <h1 className="text-xl font-bold text-gray-900">Time in Lieu</h1>
                <p className="text-xs text-gray-500">Manage your TIL balance</p>
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
        {/* Balance Card */}
        <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
          <div className="flex justify-between items-center">
            <div>
              <h2 className="text-lg font-bold text-gray-900 mb-2">Your TIL Balance</h2>
              <div className="flex items-baseline gap-2">
                <span className="text-4xl font-bold" style={{ color: '#667eea' }}>
                  {tilBalance?.current_balance || '0.00'}
                </span>
                <span className="text-gray-500">hours available</span>
              </div>
              <div className="mt-2 text-sm text-gray-500">
                <span className="text-green-600">Earned: {tilBalance?.total_earned || '0'}h</span>
                <span className="mx-2">|</span>
                <span className="text-red-600">Used: {tilBalance?.total_used || '0'}h</span>
              </div>
            </div>
            <button
              onClick={() => setShowRequestModal(true)}
              className="px-6 py-3 rounded-lg text-white font-medium"
              style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}
            >
              Request TIL
            </button>
          </div>
        </div>

        {/* Pending Approvals (Managers Only) */}
        {isManager && pendingRecords.length > 0 && (
          <div className="bg-white rounded-xl shadow-lg p-6 mb-6">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Pending Approvals</h2>
            <div className="space-y-3">
              {pendingRecords.map((record) => (
                <div key={record.id} className="flex items-center justify-between p-4 bg-yellow-50 rounded-lg border border-yellow-200">
                  <div>
                    <p className="font-semibold text-gray-900">{record.employee_name}</p>
                    <p className="text-sm text-gray-600">
                      <span className={`px-2 py-0.5 rounded-full text-xs ${getTypeColor(record.til_type)}`}>
                        {record.til_type_display}
                      </span>
                      <span className="ml-2">{record.hours}h on {new Date(record.date).toLocaleDateString()}</span>
                    </p>
                    <p className="text-sm text-gray-500 mt-1">{record.reason}</p>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => approveTIL.mutate(record.id)}
                      disabled={approveTIL.isPending}
                      className="px-4 py-2 bg-green-600 text-white rounded-lg text-sm font-medium hover:bg-green-700"
                    >
                      Approve
                    </button>
                    <button
                      onClick={() => {
                        setSelectedRecord(record);
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

        {/* TIL History */}
        <div className="bg-white rounded-xl shadow-lg p-6">
          <h2 className="text-lg font-bold text-gray-900 mb-4">TIL History</h2>
          {isLoading ? (
            <p className="text-gray-500 text-center py-8">Loading...</p>
          ) : records.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead>
                  <tr className="border-b border-gray-200">
                    <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Date</th>
                    {isManager && (
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Employee</th>
                    )}
                    <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Type</th>
                    <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Hours</th>
                    <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Reason</th>
                    <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Status</th>
                    <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Approved By</th>
                  </tr>
                </thead>
                <tbody>
                  {records.map((record, index) => (
                    <tr key={record.id} className={index % 2 === 0 ? 'bg-gray-50' : 'bg-white'}>
                      <td className="px-3 py-3 text-sm text-gray-900 font-medium">
                        {new Date(record.date).toLocaleDateString('en-AU', {
                          day: 'numeric',
                          month: 'short',
                          year: 'numeric',
                        })}
                      </td>
                      {isManager && (
                        <td className="px-3 py-3 text-sm text-gray-700">{record.employee_name}</td>
                      )}
                      <td className="px-3 py-3 text-sm">
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${getTypeColor(record.til_type)}`}>
                          {record.til_type_display}
                        </span>
                      </td>
                      <td className="px-3 py-3 text-sm font-bold" style={{ color: '#667eea' }}>
                        {record.hours}h
                      </td>
                      <td className="px-3 py-3 text-sm text-gray-600 max-w-xs truncate" title={record.reason}>
                        {record.reason}
                      </td>
                      <td className="px-3 py-3 text-sm">
                        <span className={`px-2 py-1 rounded-full text-xs font-semibold ${getStatusColor(record.status)}`}>
                          {record.status_display}
                        </span>
                      </td>
                      <td className="px-3 py-3 text-sm text-gray-600">
                        {record.approved_by_name || '-'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="text-gray-500 text-center py-8">No TIL records found</p>
          )}
        </div>
      </main>

      {/* Request TIL Modal */}
      {showRequestModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Request Time in Lieu</h3>
            <form onSubmit={handleRequestSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Type</label>
                <select
                  value={requestForm.til_type}
                  onChange={(e) => setRequestForm({ ...requestForm, til_type: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  required
                >
                  <option value="USED">Use TIL (take time off)</option>
                  <option value="EARNED_OT">Earn TIL - Overtime</option>
                  <option value="EARNED_EARLY">Earn TIL - Early Start</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Hours</label>
                <input
                  type="number"
                  step="0.5"
                  min="0.5"
                  max="24"
                  value={requestForm.hours}
                  onChange={(e) => setRequestForm({ ...requestForm, hours: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  placeholder="e.g., 2"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
                <input
                  type="date"
                  value={requestForm.date}
                  onChange={(e) => setRequestForm({ ...requestForm, date: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  required
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Reason</label>
                <textarea
                  value={requestForm.reason}
                  onChange={(e) => setRequestForm({ ...requestForm, reason: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  rows={3}
                  placeholder="Explain why you're requesting this TIL..."
                  required
                />
              </div>
              <div className="flex gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowRequestModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={createRequest.isPending}
                  className="flex-1 px-4 py-2 rounded-lg text-white font-medium"
                  style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}
                >
                  {createRequest.isPending ? 'Submitting...' : 'Submit Request'}
                </button>
              </div>
              {createRequest.isError && (
                <p className="text-red-600 text-sm text-center">Failed to submit request. Please try again.</p>
              )}
            </form>
          </div>
        </div>
      )}

      {/* Reject Modal */}
      {showRejectModal && selectedRecord && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md mx-4">
            <h3 className="text-lg font-bold text-gray-900 mb-4">Reject TIL Request</h3>
            <p className="text-sm text-gray-600 mb-4">
              Rejecting request from <strong>{selectedRecord.employee_name}</strong> for {selectedRecord.hours}h on{' '}
              {new Date(selectedRecord.date).toLocaleDateString()}
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
                  setSelectedRecord(null);
                }}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={handleReject}
                disabled={rejectTIL.isPending || !rejectReason.trim()}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg font-medium hover:bg-red-700 disabled:opacity-50"
              >
                {rejectTIL.isPending ? 'Rejecting...' : 'Confirm Reject'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
