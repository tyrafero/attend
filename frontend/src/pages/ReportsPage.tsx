import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '../stores/authStore';
import {
  reportsApi,
  type ReportParams,
  type AttendanceReport,
  type TILReport,
  type LeaveReport,
  type TeamReport,
} from '../api/reports';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

type ReportType = 'attendance' | 'til' | 'leave' | 'team';
type PresetType = 'this_week' | 'last_week' | 'this_month' | 'last_month' | 'last_quarter' | 'this_year';

const COLORS = ['#667eea', '#764ba2', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6'];

const LEAVE_TYPE_LABELS: Record<string, string> = {
  ANNUAL: 'Annual',
  SICK: 'Sick',
  UNPAID: 'Unpaid',
  TIL: 'TIL',
};

export function ReportsPage() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [reportType, setReportType] = useState<ReportType>('attendance');
  const [preset, setPreset] = useState<PresetType>('this_month');
  const [isExporting, setIsExporting] = useState(false);

  const isManager = user?.employee_profile?.role === 'MANAGER' || user?.employee_profile?.role === 'HR_ADMIN';

  const params: ReportParams = { preset };

  // Fetch attendance report
  const { data: attendanceReport, isLoading: attendanceLoading } = useQuery({
    queryKey: ['reports', 'attendance', preset],
    queryFn: () => reportsApi.getAttendanceReport(params),
    enabled: reportType === 'attendance',
  });

  // Fetch TIL report
  const { data: tilReport, isLoading: tilLoading } = useQuery({
    queryKey: ['reports', 'til', preset],
    queryFn: () => reportsApi.getTILReport(params),
    enabled: reportType === 'til',
  });

  // Fetch leave report
  const { data: leaveReport, isLoading: leaveLoading } = useQuery({
    queryKey: ['reports', 'leave', preset],
    queryFn: () => reportsApi.getLeaveReport(params),
    enabled: reportType === 'leave',
  });

  // Fetch team report
  const { data: teamReport, isLoading: teamLoading } = useQuery({
    queryKey: ['reports', 'team'],
    queryFn: () => reportsApi.getTeamReport(),
    enabled: reportType === 'team' && isManager,
  });

  // Fetch attendance trends for chart
  const { data: trendsData } = useQuery({
    queryKey: ['reports', 'trends', preset],
    queryFn: () => reportsApi.getAttendanceTrends({ ...params, group_by: 'day' }),
    enabled: reportType === 'attendance',
  });

  // Fetch department comparison
  const { data: deptComparison } = useQuery({
    queryKey: ['reports', 'department-comparison', preset],
    queryFn: () => reportsApi.getDepartmentComparison(params),
    enabled: reportType === 'attendance' && isManager,
  });

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleExport = async (format: 'csv' | 'excel' | 'pdf') => {
    setIsExporting(true);
    try {
      let blob: Blob;
      let filename: string;

      switch (reportType) {
        case 'attendance':
          blob = await reportsApi.exportAttendance({ ...params, format });
          filename = `attendance_report.${format === 'excel' ? 'xlsx' : format}`;
          break;
        case 'til':
          blob = await reportsApi.exportTIL({ ...params, format: 'csv' });
          filename = 'til_report.csv';
          break;
        case 'leave':
          blob = await reportsApi.exportLeave({ ...params, format: 'csv' });
          filename = 'leave_report.csv';
          break;
        default:
          return;
      }

      // Download the file
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Export failed:', error);
      alert('Export failed. Please try again.');
    } finally {
      setIsExporting(false);
    }
  };

  const isLoading = attendanceLoading || tilLoading || leaveLoading || teamLoading;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-4">
              <img
                src="https://www.digitalcinema.com.au/media/logo/stores/1/dc-logo-300px.png"
                alt="Digital Cinema"
                className="h-10"
              />
              <h1 className="text-xl font-bold text-gray-900">Reports & Analytics</h1>
            </div>
            <div className="flex items-center gap-3">
              <a
                href="/dashboard"
                className="text-sm px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors"
                style={{ color: '#667eea' }}
              >
                Dashboard
              </a>
              <a
                href="/leave"
                className="text-sm px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors"
                style={{ color: '#667eea' }}
              >
                Leave
              </a>
              <a
                href="/til"
                className="text-sm px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors"
                style={{ color: '#667eea' }}
              >
                TIL
              </a>
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

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Report Controls */}
        <div className="bg-white rounded-xl shadow-sm p-4 mb-6">
          <div className="flex flex-wrap gap-4 items-center justify-between">
            {/* Report Type Selector */}
            <div className="flex gap-2">
              <button
                onClick={() => setReportType('attendance')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  reportType === 'attendance'
                    ? 'text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
                style={reportType === 'attendance' ? { background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' } : {}}
              >
                Attendance
              </button>
              <button
                onClick={() => setReportType('til')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  reportType === 'til'
                    ? 'text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
                style={reportType === 'til' ? { background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' } : {}}
              >
                TIL
              </button>
              <button
                onClick={() => setReportType('leave')}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  reportType === 'leave'
                    ? 'text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
                style={reportType === 'leave' ? { background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' } : {}}
              >
                Leave
              </button>
              {isManager && (
                <button
                  onClick={() => setReportType('team')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    reportType === 'team'
                      ? 'text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                  style={reportType === 'team' ? { background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' } : {}}
                >
                  Team
                </button>
              )}
            </div>

            {/* Date Range Preset */}
            {reportType !== 'team' && (
              <div className="flex gap-2 items-center">
                <label className="text-sm text-gray-600">Period:</label>
                <select
                  value={preset}
                  onChange={(e) => setPreset(e.target.value as PresetType)}
                  className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  <option value="this_week">This Week</option>
                  <option value="last_week">Last Week</option>
                  <option value="this_month">This Month</option>
                  <option value="last_month">Last Month</option>
                  <option value="last_quarter">Last Quarter</option>
                  <option value="this_year">This Year</option>
                </select>
              </div>
            )}

            {/* Export Buttons */}
            {reportType !== 'team' && (
              <div className="flex gap-2">
                <button
                  onClick={() => handleExport('csv')}
                  disabled={isExporting}
                  className="px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
                >
                  Export CSV
                </button>
                {reportType === 'attendance' && (
                  <>
                    <button
                      onClick={() => handleExport('excel')}
                      disabled={isExporting}
                      className="px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
                    >
                      Export Excel
                    </button>
                    <button
                      onClick={() => handleExport('pdf')}
                      disabled={isExporting}
                      className="px-3 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50"
                    >
                      Export PDF
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center items-center py-20">
            <div className="animate-spin rounded-full h-12 w-12 border-4 border-purple-500 border-t-transparent"></div>
          </div>
        ) : (
          <>
            {/* Attendance Report */}
            {reportType === 'attendance' && attendanceReport && (
              <AttendanceReportView
                report={attendanceReport}
                trends={trendsData?.data || []}
                deptComparison={deptComparison?.departments || []}
                isManager={isManager}
              />
            )}

            {/* TIL Report */}
            {reportType === 'til' && tilReport && (
              <TILReportView report={tilReport} />
            )}

            {/* Leave Report */}
            {reportType === 'leave' && leaveReport && (
              <LeaveReportView report={leaveReport} />
            )}

            {/* Team Report */}
            {reportType === 'team' && teamReport && isManager && (
              <TeamReportView report={teamReport} />
            )}
          </>
        )}
      </main>
    </div>
  );
}

// Attendance Report Component
function AttendanceReportView({
  report,
  trends,
  deptComparison,
  isManager,
}: {
  report: AttendanceReport;
  trends: Array<{ date: string; total_hours: number; avg_hours: number; records: number }>;
  deptComparison: Array<{ department: string; total_hours: number; avg_hours: number; employees: number }>;
  isManager: boolean;
}) {
  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl shadow-sm p-4">
          <p className="text-gray-500 text-xs uppercase">Total Records</p>
          <p className="text-2xl font-bold text-gray-900">{report.summary.total_records}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-4">
          <p className="text-gray-500 text-xs uppercase">Total Hours</p>
          <p className="text-2xl font-bold" style={{ color: '#667eea' }}>
            {report.summary.total_hours.toFixed(1)}h
          </p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-4">
          <p className="text-gray-500 text-xs uppercase">Avg Hours/Day</p>
          <p className="text-2xl font-bold" style={{ color: '#764ba2' }}>
            {report.summary.avg_hours_per_day.toFixed(1)}h
          </p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-4">
          <p className="text-gray-500 text-xs uppercase">Still Clocked In</p>
          <p className="text-2xl font-bold text-green-600">{report.summary.still_clocked_in}</p>
        </div>
      </div>

      {/* Hours Trend Chart */}
      {trends.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold mb-4">Hours Trend</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={trends}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tickFormatter={(value) => new Date(value).toLocaleDateString('en-AU', { day: 'numeric', month: 'short' })}
              />
              <YAxis />
              <Tooltip
                labelFormatter={(value) => new Date(value).toLocaleDateString('en-AU', { weekday: 'short', day: 'numeric', month: 'short' })}
              />
              <Legend />
              <Line type="monotone" dataKey="total_hours" stroke="#667eea" name="Total Hours" strokeWidth={2} />
              <Line type="monotone" dataKey="avg_hours" stroke="#10b981" name="Avg Hours" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Department Comparison (Managers only) */}
      {isManager && deptComparison.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold mb-4">Department Comparison</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={deptComparison}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="department" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Bar dataKey="total_hours" fill="#667eea" name="Total Hours" />
              <Bar dataKey="avg_hours" fill="#10b981" name="Avg Hours" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Employee Breakdown (Managers only) */}
      {isManager && report.employee_breakdown.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold mb-4">Employee Breakdown</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Employee</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Total Hours</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Days Worked</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Avg Hours/Day</th>
                </tr>
              </thead>
              <tbody>
                {report.employee_breakdown.slice(0, 10).map((emp, idx) => (
                  <tr key={emp.employee_id} className={idx % 2 === 0 ? 'bg-gray-50' : ''}>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{emp.employee_name}</td>
                    <td className="px-4 py-3 text-sm text-right" style={{ color: '#667eea' }}>
                      {emp.total_hours.toFixed(1)}h
                    </td>
                    <td className="px-4 py-3 text-sm text-right text-gray-700">{emp.days_worked}</td>
                    <td className="px-4 py-3 text-sm text-right text-gray-700">{emp.avg_hours.toFixed(1)}h</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Recent Records */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h3 className="text-lg font-semibold mb-4">Recent Records</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="border-b">
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Date</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Employee</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Clock In</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Clock Out</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Hours</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase">Status</th>
              </tr>
            </thead>
            <tbody>
              {report.records.slice(0, 20).map((record, idx) => (
                <tr key={record.id} className={idx % 2 === 0 ? 'bg-gray-50' : ''}>
                  <td className="px-4 py-3 text-sm text-gray-900">
                    {new Date(record.date).toLocaleDateString('en-AU', { day: 'numeric', month: 'short' })}
                  </td>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">{record.employee_name}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">{record.first_clock_in || '-'}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">{record.last_clock_out || '-'}</td>
                  <td className="px-4 py-3 text-sm text-right" style={{ color: '#667eea' }}>
                    {record.final_hours}h
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-semibold ${
                        record.current_status === 'IN' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {record.current_status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// TIL Report Component
function TILReportView({ report }: { report: TILReport }) {
  const tilTypeData = report.by_type.map((t, idx) => ({
    name: t.til_type.replace('EARNED_', '').replace('_', ' '),
    value: Math.abs(t.total_hours),
    color: COLORS[idx % COLORS.length],
  }));

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="bg-white rounded-xl shadow-sm p-4">
          <p className="text-gray-500 text-xs uppercase">Earned (Early)</p>
          <p className="text-2xl font-bold text-green-600">{report.summary.total_earned_early.toFixed(1)}h</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-4">
          <p className="text-gray-500 text-xs uppercase">Earned (OT)</p>
          <p className="text-2xl font-bold text-green-600">{report.summary.total_earned_overtime.toFixed(1)}h</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-4">
          <p className="text-gray-500 text-xs uppercase">Used</p>
          <p className="text-2xl font-bold text-orange-600">{report.summary.total_used.toFixed(1)}h</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-4">
          <p className="text-gray-500 text-xs uppercase">Adjusted</p>
          <p className="text-2xl font-bold" style={{ color: '#667eea' }}>
            {report.summary.total_adjusted.toFixed(1)}h
          </p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-4">
          <p className="text-gray-500 text-xs uppercase">Pending</p>
          <p className="text-2xl font-bold text-yellow-600">{report.summary.pending_approvals}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* TIL Distribution Chart */}
        {tilTypeData.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h3 className="text-lg font-semibold mb-4">TIL Distribution</h3>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={tilTypeData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                  label={({ name, value }) => `${name}: ${value.toFixed(1)}h`}
                >
                  {tilTypeData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* TIL Balances */}
        {report.balances.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h3 className="text-lg font-semibold mb-4">TIL Balances</h3>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={report.balances.slice(0, 8)} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis dataKey="employee__employee_name" type="category" width={100} tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="current_balance" fill="#667eea" name="Balance" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* Recent TIL Records */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h3 className="text-lg font-semibold mb-4">Recent TIL Records</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="border-b">
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Date</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Employee</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Type</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Hours</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase">Status</th>
              </tr>
            </thead>
            <tbody>
              {report.recent_records.map((record, idx) => (
                <tr key={record.id} className={idx % 2 === 0 ? 'bg-gray-50' : ''}>
                  <td className="px-4 py-3 text-sm text-gray-900">
                    {new Date(record.date).toLocaleDateString('en-AU', { day: 'numeric', month: 'short' })}
                  </td>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">{record.employee__employee_name}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">{record.til_type.replace('EARNED_', '').replace('_', ' ')}</td>
                  <td className="px-4 py-3 text-sm text-right" style={{ color: record.hours > 0 ? '#10b981' : '#f59e0b' }}>
                    {record.hours > 0 ? '+' : ''}{record.hours}h
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-semibold ${
                        record.status === 'APPROVED'
                          ? 'bg-green-100 text-green-700'
                          : record.status === 'PENDING'
                          ? 'bg-yellow-100 text-yellow-700'
                          : 'bg-red-100 text-red-700'
                      }`}
                    >
                      {record.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// Leave Report Component
function LeaveReportView({ report }: { report: LeaveReport }) {
  const leaveTypeData = report.by_type.map((t, idx) => ({
    name: LEAVE_TYPE_LABELS[t.leave_type] || t.leave_type,
    value: t.total_days,
    count: t.count,
    color: COLORS[idx % COLORS.length],
  }));

  const statusData = report.by_status.map((s) => ({
    name: s.status,
    value: s.count,
    color: s.status === 'APPROVED' ? '#10b981' : s.status === 'PENDING' ? '#f59e0b' : s.status === 'REJECTED' ? '#ef4444' : '#9ca3af',
  }));

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
        <div className="bg-white rounded-xl shadow-sm p-4">
          <p className="text-gray-500 text-xs uppercase">Total Requests</p>
          <p className="text-2xl font-bold text-gray-900">{report.summary.total_requests}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-4">
          <p className="text-gray-500 text-xs uppercase">Approved</p>
          <p className="text-2xl font-bold text-green-600">{report.summary.approved}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-4">
          <p className="text-gray-500 text-xs uppercase">Pending</p>
          <p className="text-2xl font-bold text-yellow-600">{report.summary.pending}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-4">
          <p className="text-gray-500 text-xs uppercase">Rejected</p>
          <p className="text-2xl font-bold text-red-600">{report.summary.rejected}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-4">
          <p className="text-gray-500 text-xs uppercase">Days Approved</p>
          <p className="text-2xl font-bold" style={{ color: '#667eea' }}>
            {report.summary.total_days_approved}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Leave by Type Chart */}
        {leaveTypeData.length > 0 && (
          <div className="bg-white rounded-xl shadow-sm p-6">
            <h3 className="text-lg font-semibold mb-4">Leave by Type</h3>
            <ResponsiveContainer width="100%" height={250}>
              <PieChart>
                <Pie
                  data={leaveTypeData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={5}
                  dataKey="value"
                  label={({ name, value }) => `${name}: ${value}d`}
                >
                  {leaveTypeData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}

        {/* Leave by Status */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold mb-4">Leave by Status</h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={statusData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="value" name="Requests">
                {statusData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Recent Leaves */}
      <div className="bg-white rounded-xl shadow-sm p-6">
        <h3 className="text-lg font-semibold mb-4">Recent Leave Requests</h3>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="border-b">
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Employee</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Type</th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Dates</th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Days</th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-gray-500 uppercase">Status</th>
              </tr>
            </thead>
            <tbody>
              {report.recent_leaves.map((leave, idx) => (
                <tr key={leave.id} className={idx % 2 === 0 ? 'bg-gray-50' : ''}>
                  <td className="px-4 py-3 text-sm font-medium text-gray-900">{leave.employee_name}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">{LEAVE_TYPE_LABELS[leave.leave_type] || leave.leave_type}</td>
                  <td className="px-4 py-3 text-sm text-gray-700">
                    {new Date(leave.start_date).toLocaleDateString('en-AU', { day: 'numeric', month: 'short' })} -{' '}
                    {new Date(leave.end_date).toLocaleDateString('en-AU', { day: 'numeric', month: 'short' })}
                  </td>
                  <td className="px-4 py-3 text-sm text-right" style={{ color: '#667eea' }}>
                    {leave.total_days}
                  </td>
                  <td className="px-4 py-3 text-center">
                    <span
                      className={`px-2 py-1 rounded-full text-xs font-semibold ${
                        leave.status === 'APPROVED'
                          ? 'bg-green-100 text-green-700'
                          : leave.status === 'PENDING'
                          ? 'bg-yellow-100 text-yellow-700'
                          : leave.status === 'REJECTED'
                          ? 'bg-red-100 text-red-700'
                          : 'bg-gray-100 text-gray-600'
                      }`}
                    >
                      {leave.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// Team Report Component
function TeamReportView({ report }: { report: TeamReport }) {
  return (
    <div className="space-y-6">
      {/* Today's Overview */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-xl shadow-sm p-4">
          <p className="text-gray-500 text-xs uppercase">Team Size</p>
          <p className="text-2xl font-bold text-gray-900">{report.team_size}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-4">
          <p className="text-gray-500 text-xs uppercase">Clocked In</p>
          <p className="text-2xl font-bold text-green-600">{report.today.clocked_in}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-4">
          <p className="text-gray-500 text-xs uppercase">Clocked Out</p>
          <p className="text-2xl font-bold text-gray-600">{report.today.clocked_out}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-4">
          <p className="text-gray-500 text-xs uppercase">Not Clocked In</p>
          <p className="text-2xl font-bold text-orange-600">{report.today.not_clocked_in}</p>
        </div>
      </div>

      {/* Week Stats & Pending Approvals */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-xl shadow-sm p-4">
          <p className="text-gray-500 text-xs uppercase">This Week - Total Hours</p>
          <p className="text-2xl font-bold" style={{ color: '#667eea' }}>
            {report.this_week.total_hours.toFixed(1)}h
          </p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-4">
          <p className="text-gray-500 text-xs uppercase">Pending TIL Approvals</p>
          <p className="text-2xl font-bold text-yellow-600">{report.pending_approvals.til}</p>
        </div>
        <div className="bg-white rounded-xl shadow-sm p-4">
          <p className="text-gray-500 text-xs uppercase">Pending Leave Approvals</p>
          <p className="text-2xl font-bold text-yellow-600">{report.pending_approvals.leave}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Team Status Today */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold mb-4">Team Status Today</h3>
          <div className="space-y-3 max-h-80 overflow-y-auto">
            {report.team_members.map((member) => (
              <div
                key={member.employee_id}
                className="flex items-center justify-between p-3 rounded-lg bg-gray-50"
              >
                <div>
                  <p className="font-medium text-gray-900">{member.employee_name}</p>
                  <p className="text-xs text-gray-500">{member.department || 'No Department'}</p>
                </div>
                <div className="text-right">
                  <span
                    className={`px-2 py-1 rounded-full text-xs font-semibold ${
                      member.status_today === 'IN'
                        ? 'bg-green-100 text-green-700'
                        : member.status_today === 'OUT'
                        ? 'bg-gray-100 text-gray-600'
                        : 'bg-orange-100 text-orange-700'
                    }`}
                  >
                    {member.status_today === 'NOT_CLOCKED' ? 'NOT IN' : member.status_today}
                  </span>
                  {member.hours_today > 0 && (
                    <p className="text-sm mt-1" style={{ color: '#667eea' }}>
                      {member.hours_today.toFixed(1)}h
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* TIL Balances */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold mb-4">Team TIL Balances</h3>
          {report.til_balances.length > 0 ? (
            <div className="space-y-3 max-h-80 overflow-y-auto">
              {report.til_balances.map((balance) => (
                <div
                  key={balance.employee__employee_id}
                  className="flex items-center justify-between p-3 rounded-lg bg-gray-50"
                >
                  <p className="font-medium text-gray-900">{balance.employee__employee_name}</p>
                  <p
                    className="font-bold"
                    style={{ color: Number(balance.current_balance) > 0 ? '#10b981' : '#667eea' }}
                  >
                    {balance.current_balance}h
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-500 text-center py-4">No TIL balances</p>
          )}
        </div>
      </div>

      {/* Upcoming Leave */}
      {report.upcoming_leave.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-lg font-semibold mb-4">Upcoming Leave (Next 2 Weeks)</h3>
          <div className="overflow-x-auto">
            <table className="min-w-full">
              <thead>
                <tr className="border-b">
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Employee</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Type</th>
                  <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Dates</th>
                  <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 uppercase">Days</th>
                </tr>
              </thead>
              <tbody>
                {report.upcoming_leave.map((leave, idx) => (
                  <tr key={idx} className={idx % 2 === 0 ? 'bg-gray-50' : ''}>
                    <td className="px-4 py-3 text-sm font-medium text-gray-900">{leave.employee_name}</td>
                    <td className="px-4 py-3 text-sm text-gray-700">{LEAVE_TYPE_LABELS[leave.leave_type] || leave.leave_type}</td>
                    <td className="px-4 py-3 text-sm text-gray-700">
                      {new Date(leave.start_date).toLocaleDateString('en-AU', { day: 'numeric', month: 'short' })} -{' '}
                      {new Date(leave.end_date).toLocaleDateString('en-AU', { day: 'numeric', month: 'short' })}
                    </td>
                    <td className="px-4 py-3 text-sm text-right" style={{ color: '#667eea' }}>
                      {leave.total_days}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
