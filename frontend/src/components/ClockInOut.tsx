import { useState, useEffect } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { attendanceApi } from '../api/attendance';
import { useAuthStore } from '../stores/authStore';

export function ClockInOut() {
  const { user } = useAuthStore();
  const queryClient = useQueryClient();
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState<'success' | 'error'>('success');
  const [currentTime, setCurrentTime] = useState(new Date());

  // Update clock every second
  useEffect(() => {
    const timer = setInterval(() => setCurrentTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  // Get current status with polling
  const { data: currentStatus, isLoading: statusLoading, refetch: refetchStatus } = useQuery({
    queryKey: ['attendance', 'current'],
    queryFn: attendanceApi.getCurrentStatus,
    refetchInterval: 30000, // Poll every 30 seconds
    staleTime: 0, // Always consider data stale
  });

  // Clock in/out mutation
  const clockMutation = useMutation({
    mutationFn: () => attendanceApi.clock(),
    onSuccess: async (data) => {
      setMessage(data.message);
      setMessageType('success');

      // Force refetch status immediately
      await refetchStatus();

      // Also invalidate all attendance queries
      queryClient.invalidateQueries({ queryKey: ['attendance'] });

      setTimeout(() => setMessage(''), 3000);
    },
    onError: (error: any) => {
      setMessage(error.response?.data?.error || 'Failed to clock in/out');
      setMessageType('error');
      setTimeout(() => setMessage(''), 5000);
    },
  });

  const handleClock = () => {
    clockMutation.mutate();
  };

  const isCurrentlyIn = currentStatus?.current_status === 'IN';

  return (
    <div className="bg-white rounded-xl shadow-lg p-6">
      {/* Current Time */}
      <div className="text-center mb-4">
        <p className="text-4xl font-bold text-gray-900">
          {currentTime.toLocaleTimeString('en-AU', { hour: '2-digit', minute: '2-digit' })}
        </p>
        <p className="text-sm text-gray-500">
          {currentTime.toLocaleDateString('en-AU', {
            weekday: 'long',
            day: 'numeric',
            month: 'long',
            year: 'numeric',
          })}
        </p>
      </div>

      {/* Current Status */}
      <div className="text-center mb-4">
        {statusLoading ? (
          <div className="animate-pulse bg-gray-100 h-8 rounded-full w-32 mx-auto"></div>
        ) : (
          <span
            className={`inline-flex items-center px-4 py-2 rounded-full text-sm font-semibold ${
              isCurrentlyIn
                ? 'bg-green-100 text-green-700'
                : 'bg-gray-100 text-gray-600'
            }`}
          >
            <span
              className={`w-2 h-2 rounded-full mr-2 ${
                isCurrentlyIn ? 'bg-green-500' : 'bg-gray-400'
              }`}
            ></span>
            {isCurrentlyIn ? 'Currently Clocked In' : 'Currently Clocked Out'}
          </span>
        )}
      </div>

      {/* Today's Info */}
      {currentStatus && (
        <div className="bg-gray-50 rounded-lg p-4 mb-4 space-y-2">
          {currentStatus.first_clock_in && (
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">First Clock In:</span>
              <span className="font-medium text-gray-900">{currentStatus.first_clock_in}</span>
            </div>
          )}
          {currentStatus.last_clock_out && (
            <div className="flex justify-between text-sm">
              <span className="text-gray-500">Last Clock Out:</span>
              <span className="font-medium text-gray-900">{currentStatus.last_clock_out}</span>
            </div>
          )}
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Hours Worked:</span>
            <span className="font-bold text-lg" style={{ color: '#667eea' }}>
              {currentStatus.hours_worked || '0.00'}h
            </span>
          </div>
        </div>
      )}

      {/* Message */}
      {message && (
        <div
          className={`mb-4 p-3 rounded-lg text-center text-sm font-medium ${
            messageType === 'error'
              ? 'bg-red-50 text-red-700 border border-red-200'
              : 'bg-green-50 text-green-700 border border-green-200'
          }`}
        >
          {message}
        </div>
      )}

      {/* Clock Button */}
      <button
        onClick={handleClock}
        disabled={clockMutation.isPending}
        className={`w-full py-4 px-6 rounded-xl text-white font-bold text-lg transition-all transform hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none`}
        style={{
          background: !isCurrentlyIn
            ? 'linear-gradient(135deg, #51cf66 0%, #40c057 100%)'
            : 'linear-gradient(135deg, #ff6b6b 0%, #fa5252 100%)',
        }}
      >
        {clockMutation.isPending
          ? 'Processing...'
          : !isCurrentlyIn
          ? '✓ Clock In'
          : '✗ Clock Out'}
      </button>

      {/* Employee Info */}
      <div className="mt-4 pt-4 border-t border-gray-100 text-center">
        <p className="text-sm text-gray-500">
          {user?.employee_profile?.employee_name} ({user?.employee_profile?.employee_id})
        </p>
      </div>
    </div>
  );
}
