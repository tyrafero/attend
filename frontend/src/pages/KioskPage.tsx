import { useState, useEffect } from 'react';
import { attendanceApi } from '../api/attendance';
import type { ClockActionResponse } from '../types';

export function KioskPage() {
  const [pin, setPin] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [success, setSuccess] = useState<ClockActionResponse | null>(null);

  // Clear any existing JWT session when entering kiosk mode
  useEffect(() => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    localStorage.removeItem('user');
  }, []);

  const handlePinInput = (digit: string) => {
    if (pin.length < 6) {
      setPin(pin + digit);
      setError('');
    }
  };

  const handleClear = () => {
    setPin('');
    setError('');
  };

  const handleBackspace = () => {
    setPin(pin.slice(0, -1));
    setError('');
  };

  const handleSubmit = async () => {
    if (pin.length < 4) {
      setError('Please enter your PIN');
      return;
    }

    setError('');
    setIsLoading(true);

    try {
      const response = await attendanceApi.clock({ pin });
      setSuccess(response);
    } catch (err: any) {
      const errorMsg = err.response?.data?.detail
        || err.response?.data?.non_field_errors?.[0]
        || err.response?.data?.pin?.[0]
        || 'Invalid PIN. Please try again.';
      setError(errorMsg);
      setPin('');
    } finally {
      setIsLoading(false);
    }
  };

  // Auto-redirect after success
  useEffect(() => {
    if (success) {
      const timer = setTimeout(() => {
        setSuccess(null);
        setPin('');
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [success]);

  // Keyboard support
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (success) return;

      if (e.key >= '0' && e.key <= '9') {
        handlePinInput(e.key);
      } else if (e.key === 'Backspace') {
        handleBackspace();
      } else if (e.key === 'Escape') {
        handleClear();
      } else if (e.key === 'Enter' && pin.length >= 4) {
        handleSubmit();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [pin, success]);

  // Success Screen
  if (success) {
    const isClockIn = success.action === 'IN';
    return (
      <div className="min-h-screen flex items-center justify-center p-2" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
        <div className="bg-white rounded-2xl shadow-2xl p-6 max-w-md w-full text-center">
          {/* Success Icon */}
          <div
            className="text-7xl mb-4"
            style={{ color: isClockIn ? '#51cf66' : '#ff6b6b' }}
          >
            ✓
          </div>

          {/* Employee Name */}
          <div className="text-2xl font-bold text-gray-800 mb-2">
            {success.employee_name}
          </div>

          {/* Action Text */}
          <div
            className="text-xl mb-6"
            style={{ color: isClockIn ? '#51cf66' : '#ff6b6b' }}
          >
            Clocked {success.action}
          </div>

          {/* Time Info */}
          <div className="bg-gray-50 rounded-lg p-4">
            <p className="text-gray-600 mb-2">
              <strong>Time:</strong> {success.time}
            </p>
            <p className="text-gray-600 mb-2">
              <strong>Date:</strong> {new Date(success.timestamp).toLocaleDateString()}
            </p>
            {success.hours_worked && (
              <div className="mt-3">
                <p className="text-gray-600"><strong>Today's Hours:</strong></p>
                <div className="text-3xl font-bold mt-1" style={{ color: '#667eea' }}>
                  {success.hours_worked} hours
                </div>
              </div>
            )}
          </div>

          <p className="text-gray-400 text-sm mt-4">Returning in 3 seconds...</p>
        </div>
      </div>
    );
  }

  // PIN Entry Screen
  return (
    <div className="min-h-screen flex items-center justify-center p-2" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
      <div className="bg-white rounded-2xl shadow-2xl p-6 max-w-md w-full">
        {/* Logo */}
        <div className="text-center mb-4">
          <img
            src="https://www.digitalcinema.com.au/media/logo/stores/1/dc-logo-300px.png"
            alt="Digital Cinema"
            className="h-14 mx-auto mb-3"
          />
        </div>

        {/* Header */}
        <h1 className="text-2xl font-bold text-center text-gray-800 mb-1">Welcome!</h1>
        <p className="text-gray-500 text-center mb-5 text-sm">Enter your PIN to clock in or out</p>

        {/* Error Message */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 rounded-lg text-center text-sm">
            {error}
          </div>
        )}

        {/* PIN Display */}
        <div
          className="bg-gray-100 border-2 border-gray-200 rounded-xl p-4 text-center mb-4 min-h-[50px] flex items-center justify-center"
          style={{ letterSpacing: '10px', fontSize: '22px' }}
        >
          {'•'.repeat(pin.length)}
        </div>

        {/* Keypad */}
        <div className="grid grid-cols-3 gap-3 mb-4">
          {['1', '2', '3', '4', '5', '6', '7', '8', '9'].map((digit) => (
            <button
              key={digit}
              onClick={() => handlePinInput(digit)}
              disabled={isLoading}
              className="bg-gray-100 hover:bg-gray-200 active:scale-95 rounded-xl p-4 text-xl font-bold text-gray-700 transition-all disabled:opacity-50"
            >
              {digit}
            </button>
          ))}
          <button
            onClick={handleClear}
            disabled={isLoading}
            className="bg-gray-100 hover:bg-gray-200 active:scale-95 rounded-xl p-4 text-base font-bold text-gray-700 transition-all disabled:opacity-50"
          >
            Clear
          </button>
          <button
            onClick={() => handlePinInput('0')}
            disabled={isLoading}
            className="bg-gray-100 hover:bg-gray-200 active:scale-95 rounded-xl p-4 text-xl font-bold text-gray-700 transition-all disabled:opacity-50"
          >
            0
          </button>
          <button
            onClick={handleBackspace}
            disabled={isLoading}
            className="bg-gray-100 hover:bg-gray-200 active:scale-95 rounded-xl p-4 text-xl font-bold text-gray-700 transition-all disabled:opacity-50"
          >
            ⌫
          </button>
        </div>

        {/* Submit Button */}
        <button
          onClick={handleSubmit}
          disabled={isLoading || pin.length < 4}
          className="w-full text-white py-4 px-4 rounded-xl hover:opacity-90 focus:outline-none disabled:bg-gray-400 disabled:cursor-not-allowed transition-all text-lg font-bold"
          style={{ background: isLoading ? '#999' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}
        >
          {isLoading ? 'Processing...' : 'Clock In/Out'}
        </button>

        {/* Admin Login Link */}
        <div className="mt-5 text-center">
          <a
            href="/login"
            className="text-sm hover:underline"
            style={{ color: '#667eea' }}
          >
            Manager/Admin Login →
          </a>
        </div>
      </div>
    </div>
  );
}
