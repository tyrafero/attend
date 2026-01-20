import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { ClockInOut } from '../components/ClockInOut';
import { SettingsModal } from '../components/SettingsModal';
import { useQuery } from '@tanstack/react-query';
import { attendanceApi } from '../api/attendance';
import { tilApi } from '../api/til';

export function DashboardPage() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const [showSettings, setShowSettings] = useState(false);

  const isAuthenticated = !!user?.employee_profile;

  // Get attendance summary for last 30 days
  const { data: attendanceSummary, isLoading } = useQuery({
    queryKey: ['attendance', 'summary'],
    queryFn: () => {
      const endDate = new Date().toISOString().split('T')[0];
      const startDate = new Date(Date.now() - 30 * 24 * 60 * 60 * 1000)
        .toISOString()
        .split('T')[0];
      return attendanceApi.getMySummary(startDate, endDate);
    },
    enabled: isAuthenticated,
  });

  // Get TIL balance
  const { data: tilBalance } = useQuery({
    queryKey: ['til', 'balance'],
    queryFn: tilApi.getMyBalance,
    enabled: isAuthenticated,
  });

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  // Calculate total hours for the period
  const totalHours = attendanceSummary?.reduce((sum, record) => sum + Number(record.final_hours || 0), 0) || 0;

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
                <h1 className="text-xl font-bold text-gray-900">
                  {user?.employee_profile?.employee_name}
                </h1>
                <p className="text-xs text-gray-500">
                  {user?.employee_profile?.department_name || 'Employee'} •{' '}
                  {user?.employee_profile?.role === 'HR_ADMIN'
                    ? 'HR Admin'
                    : user?.employee_profile?.role === 'MANAGER'
                    ? 'Manager'
                    : 'Employee'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
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
              {(user?.employee_profile?.role === 'MANAGER' || user?.employee_profile?.role === 'HR_ADMIN') && (
                <>
                  <a
                    href="/team"
                    className="text-sm px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors"
                    style={{ color: '#667eea' }}
                  >
                    Team
                  </a>
                  <a
                    href="/shifts"
                    className="text-sm px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors"
                    style={{ color: '#667eea' }}
                  >
                    Shifts
                  </a>
                  <a
                    href="/reports"
                    className="text-sm px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors"
                    style={{ color: '#667eea' }}
                  >
                    Reports
                  </a>
                </>
              )}
              {user?.employee_profile?.role === 'HR_ADMIN' && (
                <a
                  href="/admin"
                  className="text-sm px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors font-medium"
                  style={{ color: '#764ba2' }}
                >
                  Admin
                </a>
              )}
              <button
                onClick={() => setShowSettings(true)}
                className="text-sm px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors"
                style={{ color: '#667eea' }}
              >
                ⚙️ Settings
              </button>
              <a
                href="/"
                className="text-sm px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors"
                style={{ color: '#667eea' }}
              >
                Kiosk Mode
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

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Stats Row */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
          <div className="bg-white rounded-xl shadow-lg p-4">
            <p className="text-gray-500 text-xs uppercase tracking-wide">Today's Status</p>
            <p className="text-2xl font-bold text-gray-900">
              {attendanceSummary?.[0]?.current_status === 'IN' ? '🟢 IN' : '⚪ OUT'}
            </p>
          </div>
          <div className="bg-white rounded-xl shadow-lg p-4">
            <p className="text-gray-500 text-xs uppercase tracking-wide">Today's Hours</p>
            <p className="text-2xl font-bold" style={{ color: '#667eea' }}>
              {attendanceSummary?.[0]?.final_hours || '0.00'}h
            </p>
          </div>
          <div className="bg-white rounded-xl shadow-lg p-4">
            <p className="text-gray-500 text-xs uppercase tracking-wide">This Month</p>
            <p className="text-2xl font-bold" style={{ color: '#667eea' }}>
              {totalHours.toFixed(1)}h
            </p>
          </div>
          <div className="bg-white rounded-xl shadow-lg p-4">
            <p className="text-gray-500 text-xs uppercase tracking-wide">Days Worked</p>
            <p className="text-2xl font-bold text-gray-900">
              {attendanceSummary?.filter(r => Number(r.final_hours) > 0).length || 0}
            </p>
          </div>
          <div className="bg-white rounded-xl shadow-lg p-4">
            <p className="text-gray-500 text-xs uppercase tracking-wide">TIL Balance</p>
            <p className="text-2xl font-bold" style={{ color: Number(tilBalance?.current_balance || 0) > 0 ? '#10b981' : '#667eea' }}>
              {tilBalance?.current_balance || '0.00'}h
            </p>
            <p className="text-xs text-gray-400 mt-1">
              Earned: {tilBalance?.total_earned || '0'}h | Used: {tilBalance?.total_used || '0'}h
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Clock In/Out Card */}
          <div className="lg:col-span-1">
            <ClockInOut />
          </div>

          {/* Recent Attendance Card */}
          <div className="lg:col-span-2">
            <div className="bg-white rounded-xl shadow-lg p-6">
              <h2 className="text-lg font-bold mb-4 text-gray-900">Attendance History</h2>

              {isLoading ? (
                <div className="text-center py-8 text-gray-500">Loading...</div>
              ) : attendanceSummary && attendanceSummary.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="min-w-full">
                    <thead>
                      <tr className="border-b border-gray-200">
                        <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">
                          Date
                        </th>
                        <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">
                          In
                        </th>
                        <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">
                          Out
                        </th>
                        <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">
                          Hours
                        </th>
                        <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">
                          Status
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {attendanceSummary.map((record, index) => (
                        <tr
                          key={record.id}
                          className={index % 2 === 0 ? 'bg-gray-50' : 'bg-white'}
                        >
                          <td className="px-3 py-3 text-sm text-gray-900 font-medium">
                            {new Date(record.date).toLocaleDateString('en-AU', {
                              weekday: 'short',
                              day: 'numeric',
                              month: 'short',
                            })}
                          </td>
                          <td className="px-3 py-3 text-sm text-gray-700">
                            {record.first_clock_in || '-'}
                          </td>
                          <td className="px-3 py-3 text-sm text-gray-700">
                            {record.last_clock_out || '-'}
                          </td>
                          <td className="px-3 py-3 text-sm font-bold" style={{ color: '#667eea' }}>
                            {record.final_hours}h
                          </td>
                          <td className="px-3 py-3 text-sm">
                            <span
                              className={`px-2 py-1 rounded-full text-xs font-semibold ${
                                record.current_status === 'IN'
                                  ? 'bg-green-100 text-green-700'
                                  : 'bg-gray-100 text-gray-600'
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
              ) : (
                <p className="text-gray-500 text-center py-8">No attendance records found</p>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Settings Modal */}
      <SettingsModal isOpen={showSettings} onClose={() => setShowSettings(false)} />
    </div>
  );
}
