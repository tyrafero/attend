import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { useQuery, useMutation } from '@tanstack/react-query';
import { adminApi, type EmployeeTimesheet, type DailyRecord } from '../api/admin';
import { attendanceApi } from '../api/attendance';

export function TeamPage() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();

  // Date range state (default to current week)
  const today = new Date();
  const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);
  const [startDate, setStartDate] = useState(weekAgo.toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState(today.toISOString().split('T')[0]);

  // Selected employee for detail modal
  const [selectedEmployee, setSelectedEmployee] = useState<EmployeeTimesheet | null>(null);

  const isManager = user?.employee_profile?.role === 'MANAGER' || user?.employee_profile?.role === 'HR_ADMIN';

  // Fetch team timesheet
  const { data: timesheetData, isLoading, refetch } = useQuery({
    queryKey: ['team', 'timesheet', startDate, endDate],
    queryFn: () => adminApi.getTeamTimesheet(startDate, endDate),
    enabled: isManager,
  });

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // Quick date range presets
  const setDateRange = (days: number) => {
    const end = new Date();
    const start = new Date(end.getTime() - days * 24 * 60 * 60 * 1000);
    setStartDate(start.toISOString().split('T')[0]);
    setEndDate(end.toISOString().split('T')[0]);
  };

  // Export to CSV
  const exportCSV = () => {
    if (!timesheetData?.timesheet) return;

    const headers = ['Employee ID', 'Name', 'Department', 'Days Worked', 'Total Hours'];
    const rows = timesheetData.timesheet.map(emp => [
      emp.employee_id,
      emp.employee_name,
      emp.department || '',
      emp.days_worked.toString(),
      emp.total_hours.toFixed(2)
    ]);

    const csvContent = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `team-timesheet-${startDate}-to-${endDate}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Export detailed CSV with daily records
  const exportDetailedCSV = () => {
    if (!timesheetData?.timesheet) return;

    const headers = ['Employee ID', 'Name', 'Date', 'Clock In', 'Clock Out', 'Hours'];
    const rows: string[][] = [];

    timesheetData.timesheet.forEach(emp => {
      emp.daily_records.forEach(record => {
        rows.push([
          emp.employee_id,
          emp.employee_name,
          record.date,
          record.first_clock_in?.slice(0, 5) || '',
          record.last_clock_out?.slice(0, 5) || '',
          record.final_hours.toFixed(2)
        ]);
      });
    });

    const csvContent = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `team-timesheet-detailed-${startDate}-to-${endDate}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!isManager) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
        <div className="bg-white rounded-xl shadow-lg p-8 text-center">
          <h1 className="text-2xl font-bold text-red-600 mb-4">Access Denied</h1>
          <p className="text-gray-600 mb-4">Only Managers can access this page.</p>
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
                <h1 className="text-xl font-bold text-gray-900">Team Timesheet</h1>
                <p className="text-xs text-gray-500">
                  {user?.employee_profile?.department_name} - {timesheetData?.team_count || 0} team members
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
        {/* Filters and Actions */}
        <div className="bg-white rounded-xl shadow-lg p-4 mb-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            {/* Date Range */}
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-600">From:</label>
                <input
                  type="date"
                  value={startDate}
                  onChange={(e) => setStartDate(e.target.value)}
                  className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>
              <div className="flex items-center gap-2">
                <label className="text-sm text-gray-600">To:</label>
                <input
                  type="date"
                  value={endDate}
                  onChange={(e) => setEndDate(e.target.value)}
                  className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                />
              </div>
              <button
                onClick={() => refetch()}
                className="px-3 py-1.5 bg-purple-100 text-purple-700 rounded-lg text-sm hover:bg-purple-200 transition-colors"
              >
                Apply
              </button>
            </div>

            {/* Quick Presets */}
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-500">Quick:</span>
              <button onClick={() => setDateRange(7)} className="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded">7 Days</button>
              <button onClick={() => setDateRange(14)} className="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded">14 Days</button>
              <button onClick={() => setDateRange(30)} className="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded">30 Days</button>
            </div>

            {/* Export Buttons */}
            <div className="flex items-center gap-2">
              <button
                onClick={exportCSV}
                className="px-3 py-1.5 bg-green-100 text-green-700 rounded-lg text-sm hover:bg-green-200 transition-colors flex items-center gap-1"
              >
                <span>CSV</span>
              </button>
              <button
                onClick={exportDetailedCSV}
                className="px-3 py-1.5 bg-blue-100 text-blue-700 rounded-lg text-sm hover:bg-blue-200 transition-colors flex items-center gap-1"
              >
                <span>Detailed CSV</span>
              </button>
            </div>
          </div>
        </div>

        {/* Timesheet Table */}
        <div className="bg-white rounded-xl shadow-lg overflow-hidden">
          {isLoading ? (
            <div className="p-8 text-center text-gray-500">Loading timesheet...</div>
          ) : !timesheetData?.timesheet?.length ? (
            <div className="p-8 text-center text-gray-500">No team members found</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Employee</th>
                    <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">Department</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wider">Days Worked</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wider">Total Hours</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wider">Avg Hours/Day</th>
                    <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {timesheetData.timesheet.map((emp, idx) => (
                    <tr
                      key={emp.employee_id}
                      className={`${idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'} hover:bg-purple-50 cursor-pointer transition-colors`}
                      onClick={() => setSelectedEmployee(emp)}
                    >
                      <td className="px-4 py-3">
                        <div>
                          <p className="font-medium text-gray-900">{emp.employee_name}</p>
                          <p className="text-xs text-gray-500">{emp.employee_id}</p>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-700">{emp.department || '-'}</td>
                      <td className="px-4 py-3 text-center">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          {emp.days_worked} days
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                          emp.total_hours >= 40 ? 'bg-green-100 text-green-800' :
                          emp.total_hours >= 20 ? 'bg-yellow-100 text-yellow-800' :
                          'bg-gray-100 text-gray-800'
                        }`}>
                          {emp.total_hours.toFixed(1)}h
                        </span>
                      </td>
                      <td className="px-4 py-3 text-center text-sm text-gray-700">
                        {emp.days_worked > 0 ? (emp.total_hours / emp.days_worked).toFixed(1) : '0'}h
                      </td>
                      <td className="px-4 py-3 text-center">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedEmployee(emp);
                          }}
                          className="text-purple-600 hover:text-purple-800 text-sm font-medium"
                        >
                          View Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
                {/* Summary Row */}
                <tfoot className="bg-gray-100">
                  <tr>
                    <td className="px-4 py-3 font-semibold text-gray-900">Total</td>
                    <td className="px-4 py-3"></td>
                    <td className="px-4 py-3 text-center font-semibold">
                      {timesheetData.timesheet.reduce((sum, e) => sum + e.days_worked, 0)} days
                    </td>
                    <td className="px-4 py-3 text-center font-semibold">
                      {timesheetData.timesheet.reduce((sum, e) => sum + e.total_hours, 0).toFixed(1)}h
                    </td>
                    <td className="px-4 py-3"></td>
                    <td className="px-4 py-3"></td>
                  </tr>
                </tfoot>
              </table>
            </div>
          )}
        </div>
      </main>

      {/* Employee Detail Modal */}
      {selectedEmployee && (
        <EmployeeDetailModal
          employee={selectedEmployee}
          startDate={startDate}
          endDate={endDate}
          onClose={() => setSelectedEmployee(null)}
          onRefresh={() => refetch()}
        />
      )}
    </div>
  );
}

// Employee Detail Modal Component
function EmployeeDetailModal({
  employee,
  startDate,
  endDate,
  onClose,
  onRefresh,
}: {
  employee: EmployeeTimesheet;
  startDate: string;
  endDate: string;
  onClose: () => void;
  onRefresh: () => void;
}) {
  const [editingRecord, setEditingRecord] = useState<DailyRecord | null>(null);
  const [showAddEntry, setShowAddEntry] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Update timesheet mutation
  const updateTimesheet = useMutation({
    mutationFn: (data: { id: number; first_clock_in: string; last_clock_out: string; reason: string }) =>
      attendanceApi.updateDailySummary(data.id, {
        first_clock_in: data.first_clock_in,
        last_clock_out: data.last_clock_out,
        reason: data.reason,
      }),
    onSuccess: () => {
      setMessage({ type: 'success', text: 'Timesheet updated successfully' });
      setEditingRecord(null);
      onRefresh();
      setTimeout(() => setMessage(null), 3000);
    },
    onError: () => {
      setMessage({ type: 'error', text: 'Failed to update timesheet' });
    },
  });

  // Create manual entry mutation
  const createEntry = useMutation({
    mutationFn: attendanceApi.createManualEntry,
    onSuccess: () => {
      setMessage({ type: 'success', text: 'Manual entry created successfully' });
      setShowAddEntry(false);
      onRefresh();
      setTimeout(() => setMessage(null), 3000);
    },
    onError: () => {
      setMessage({ type: 'error', text: 'Failed to create entry' });
    },
  });

  // Export individual employee's timesheet
  const exportEmployeeCSV = () => {
    const headers = ['Date', 'Clock In', 'Clock Out', 'Raw Hours', 'Final Hours', 'Status'];
    const rows = employee.daily_records.map(record => [
      record.date,
      record.first_clock_in?.slice(0, 5) || '',
      record.last_clock_out?.slice(0, 5) || '',
      record.raw_hours.toFixed(2),
      record.final_hours.toFixed(2),
      record.status
    ]);

    const csvContent = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${employee.employee_id}-timesheet-${startDate}-to-${endDate}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" onClick={onClose}>
      <div
        className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div className="bg-gradient-to-r from-purple-600 to-indigo-600 px-6 py-4">
          <div className="flex justify-between items-start">
            <div className="text-white">
              <h2 className="text-xl font-bold">{employee.employee_name}</h2>
              <p className="text-purple-200 text-sm">ID: {employee.employee_id}</p>
            </div>
            <button
              onClick={onClose}
              className="text-white/80 hover:text-white text-2xl leading-none"
            >
              &times;
            </button>
          </div>
        </div>

        {/* Message Banner */}
        {message && (
          <div className={`px-6 py-3 ${message.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'}`}>
            {message.text}
          </div>
        )}

        {/* Employee Info */}
        <div className="px-6 py-4 bg-gray-50 border-b">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-gray-500">Department</p>
              <p className="font-medium">{employee.department || '-'}</p>
            </div>
            <div>
              <p className="text-gray-500">Role</p>
              <p className="font-medium">{employee.role}</p>
            </div>
            <div>
              <p className="text-gray-500">Email</p>
              <p className="font-medium">{employee.email || '-'}</p>
            </div>
            <div>
              <p className="text-gray-500">Default Shift</p>
              <p className="font-medium">{employee.default_shift || '-'}</p>
            </div>
          </div>
        </div>

        {/* Summary Stats */}
        <div className="px-6 py-4 border-b">
          <div className="grid grid-cols-3 gap-4">
            <div className="bg-blue-50 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-blue-700">{employee.days_worked}</p>
              <p className="text-xs text-blue-600">Days Worked</p>
            </div>
            <div className="bg-green-50 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-green-700">{employee.total_hours.toFixed(1)}h</p>
              <p className="text-xs text-green-600">Total Hours</p>
            </div>
            <div className="bg-purple-50 rounded-lg p-3 text-center">
              <p className="text-2xl font-bold text-purple-700">
                {employee.days_worked > 0 ? (employee.total_hours / employee.days_worked).toFixed(1) : '0'}h
              </p>
              <p className="text-xs text-purple-600">Avg Hours/Day</p>
            </div>
          </div>
        </div>

        {/* Daily Records Table */}
        <div className="px-6 py-4 overflow-y-auto" style={{ maxHeight: '300px' }}>
          <div className="flex justify-between items-center mb-3">
            <h3 className="font-semibold text-gray-900">Daily Attendance ({startDate} to {endDate})</h3>
            <div className="flex gap-2">
              <button
                onClick={() => setShowAddEntry(true)}
                className="px-3 py-1 bg-purple-100 text-purple-700 rounded text-sm hover:bg-purple-200"
              >
                + Add Entry
              </button>
              <button
                onClick={exportEmployeeCSV}
                className="px-3 py-1 bg-green-100 text-green-700 rounded text-sm hover:bg-green-200"
              >
                Export CSV
              </button>
            </div>
          </div>

          {employee.daily_records.length === 0 ? (
            <p className="text-gray-500 text-center py-4">No attendance records for this period</p>
          ) : (
            <table className="min-w-full">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-3 py-2 text-left text-xs font-semibold text-gray-500 uppercase">Date</th>
                  <th className="px-3 py-2 text-center text-xs font-semibold text-gray-500 uppercase">Clock In</th>
                  <th className="px-3 py-2 text-center text-xs font-semibold text-gray-500 uppercase">Clock Out</th>
                  <th className="px-3 py-2 text-center text-xs font-semibold text-gray-500 uppercase">Raw Hours</th>
                  <th className="px-3 py-2 text-center text-xs font-semibold text-gray-500 uppercase">Final Hours</th>
                  <th className="px-3 py-2 text-center text-xs font-semibold text-gray-500 uppercase">Status</th>
                  <th className="px-3 py-2 text-center text-xs font-semibold text-gray-500 uppercase">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {employee.daily_records.map((record, idx) => (
                  <tr key={record.date} className={idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'}>
                    <td className="px-3 py-2 text-sm text-gray-900">
                      {new Date(record.date).toLocaleDateString('en-AU', { weekday: 'short', day: '2-digit', month: 'short' })}
                    </td>
                    <td className="px-3 py-2 text-center text-sm text-gray-700">
                      {record.first_clock_in?.slice(0, 5) || '-'}
                    </td>
                    <td className="px-3 py-2 text-center text-sm text-gray-700">
                      {record.last_clock_out?.slice(0, 5) || '-'}
                    </td>
                    <td className="px-3 py-2 text-center text-sm text-gray-700">
                      {record.raw_hours.toFixed(1)}h
                    </td>
                    <td className="px-3 py-2 text-center text-sm font-medium text-gray-900">
                      {record.final_hours.toFixed(1)}h
                    </td>
                    <td className="px-3 py-2 text-center">
                      <span className={`px-2 py-0.5 rounded-full text-xs ${
                        record.status === 'IN' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                      }`}>
                        {record.status}
                      </span>
                    </td>
                    <td className="px-3 py-2 text-center">
                      <button
                        onClick={() => setEditingRecord(record)}
                        className="text-purple-600 hover:text-purple-800 text-sm"
                        title="Edit"
                      >
                        Edit
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-4 bg-gray-50 border-t flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
          >
            Close
          </button>
        </div>
      </div>

      {/* Edit Record Modal */}
      {editingRecord && (
        <EditTimesheetModal
          record={editingRecord}
          onClose={() => setEditingRecord(null)}
          onSave={(data) => updateTimesheet.mutate({ ...data, id: editingRecord.id })}
          isLoading={updateTimesheet.isPending}
        />
      )}

      {/* Add Entry Modal */}
      {showAddEntry && (
        <AddEntryModal
          employeeId={employee.employee_id}
          onClose={() => setShowAddEntry(false)}
          onSave={(data) => createEntry.mutate(data)}
          isLoading={createEntry.isPending}
        />
      )}
    </div>
  );
}

// Edit Timesheet Modal Component
function EditTimesheetModal({
  record,
  onClose,
  onSave,
  isLoading,
}: {
  record: DailyRecord;
  onClose: () => void;
  onSave: (data: { first_clock_in: string; last_clock_out: string; reason: string }) => void;
  isLoading: boolean;
}) {
  const [clockIn, setClockIn] = useState(record.first_clock_in?.slice(0, 5) || '');
  const [clockOut, setClockOut] = useState(record.last_clock_out?.slice(0, 5) || '');
  const [reason, setReason] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({ first_clock_in: clockIn, last_clock_out: clockOut, reason });
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-[60]" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-bold text-gray-900 mb-4">Edit Timesheet Entry</h3>
        <p className="text-sm text-gray-500 mb-4">
          Editing: {new Date(record.date).toLocaleDateString('en-AU', { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' })}
        </p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Clock In</label>
              <input
                type="time"
                value={clockIn}
                onChange={(e) => setClockIn(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Clock Out</label>
              <input
                type="time"
                value={clockOut}
                onChange={(e) => setClockOut(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                required
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Reason for Edit *</label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              rows={3}
              placeholder="Explain why this edit is being made..."
              required
            />
          </div>
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || !reason.trim()}
              className="flex-1 px-4 py-2 rounded-lg text-white font-medium disabled:opacity-50"
              style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}
            >
              {isLoading ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// Add Entry Modal Component
function AddEntryModal({
  employeeId,
  onClose,
  onSave,
  isLoading,
}: {
  employeeId: string;
  onClose: () => void;
  onSave: (data: { employee_id: string; date: string; first_clock_in: string; last_clock_out: string; reason: string }) => void;
  isLoading: boolean;
}) {
  const [date, setDate] = useState(new Date().toISOString().split('T')[0]);
  const [clockIn, setClockIn] = useState('08:30');
  const [clockOut, setClockOut] = useState('17:00');
  const [reason, setReason] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSave({ employee_id: employeeId, date, first_clock_in: clockIn, last_clock_out: clockOut, reason });
  };

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-[60]" onClick={onClose}>
      <div className="bg-white rounded-xl shadow-2xl p-6 w-full max-w-md mx-4" onClick={(e) => e.stopPropagation()}>
        <h3 className="text-lg font-bold text-gray-900 mb-4">Add Manual Entry</h3>
        <p className="text-sm text-gray-500 mb-4">Create a timesheet entry for a missing day</p>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Date</label>
            <input
              type="date"
              value={date}
              onChange={(e) => setDate(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              required
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Clock In</label>
              <input
                type="time"
                value={clockIn}
                onChange={(e) => setClockIn(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Clock Out</label>
              <input
                type="time"
                value={clockOut}
                onChange={(e) => setClockOut(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                required
              />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Reason for Manual Entry *</label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
              rows={3}
              placeholder="Explain why this manual entry is being created..."
              required
            />
          </div>
          <div className="flex gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || !reason.trim()}
              className="flex-1 px-4 py-2 rounded-lg text-white font-medium disabled:opacity-50"
              style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}
            >
              {isLoading ? 'Creating...' : 'Create Entry'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
