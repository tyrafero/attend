import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { authApi } from '../api/auth';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [activeTab, setActiveTab] = useState<'password' | 'pin'>('password');

  // Password form state
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // PIN form state
  const [oldPin, setOldPin] = useState('');
  const [newPin, setNewPin] = useState('');
  const [confirmPin, setConfirmPin] = useState('');

  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState<'success' | 'error'>('success');

  // Change password mutation
  const passwordMutation = useMutation({
    mutationFn: () => authApi.changePassword(oldPassword, newPassword),
    onSuccess: () => {
      setMessage('Password changed successfully!');
      setMessageType('success');
      setOldPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setTimeout(() => setMessage(''), 3000);
    },
    onError: (error: any) => {
      setMessage(error.response?.data?.error || error.response?.data?.old_password?.[0] || 'Failed to change password');
      setMessageType('error');
    },
  });

  // Change PIN mutation
  const pinMutation = useMutation({
    mutationFn: () => authApi.changePIN(oldPin, newPin),
    onSuccess: () => {
      setMessage('PIN changed successfully!');
      setMessageType('success');
      setOldPin('');
      setNewPin('');
      setConfirmPin('');
      setTimeout(() => setMessage(''), 3000);
    },
    onError: (error: any) => {
      setMessage(error.response?.data?.error || error.response?.data?.old_pin?.[0] || 'Failed to change PIN');
      setMessageType('error');
    },
  });

  const handlePasswordSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setMessage('');

    if (newPassword !== confirmPassword) {
      setMessage('New passwords do not match');
      setMessageType('error');
      return;
    }

    if (newPassword.length < 6) {
      setMessage('Password must be at least 6 characters');
      setMessageType('error');
      return;
    }

    passwordMutation.mutate();
  };

  const handlePinSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setMessage('');

    if (newPin !== confirmPin) {
      setMessage('New PINs do not match');
      setMessageType('error');
      return;
    }

    if (newPin.length < 4 || newPin.length > 6) {
      setMessage('PIN must be 4-6 digits');
      setMessageType('error');
      return;
    }

    if (!/^\d+$/.test(newPin)) {
      setMessage('PIN must contain only numbers');
      setMessageType('error');
      return;
    }

    pinMutation.mutate();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-md w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex justify-between items-center p-4 border-b">
          <h2 className="text-xl font-bold text-gray-900">Settings</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 text-2xl leading-none"
          >
            ×
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b">
          <button
            onClick={() => { setActiveTab('password'); setMessage(''); }}
            className={`flex-1 py-3 text-sm font-medium transition-colors ${
              activeTab === 'password'
                ? 'border-b-2 text-purple-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
            style={{ borderColor: activeTab === 'password' ? '#667eea' : 'transparent' }}
          >
            Change Password
          </button>
          <button
            onClick={() => { setActiveTab('pin'); setMessage(''); }}
            className={`flex-1 py-3 text-sm font-medium transition-colors ${
              activeTab === 'pin'
                ? 'border-b-2 text-purple-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
            style={{ borderColor: activeTab === 'pin' ? '#667eea' : 'transparent' }}
          >
            Change PIN
          </button>
        </div>

        {/* Content */}
        <div className="p-6">
          {/* Message */}
          {message && (
            <div
              className={`mb-4 p-3 rounded-lg text-sm ${
                messageType === 'error'
                  ? 'bg-red-50 text-red-700 border border-red-200'
                  : 'bg-green-50 text-green-700 border border-green-200'
              }`}
            >
              {message}
            </div>
          )}

          {activeTab === 'password' ? (
            <form onSubmit={handlePasswordSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Current Password
                </label>
                <input
                  type="password"
                  value={oldPassword}
                  onChange={(e) => setOldPassword(e.target.value)}
                  required
                  className="w-full px-4 py-3 bg-gray-100 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-purple-500"
                  placeholder="Enter current password"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  New Password
                </label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  className="w-full px-4 py-3 bg-gray-100 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-purple-500"
                  placeholder="Enter new password"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Confirm New Password
                </label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  className="w-full px-4 py-3 bg-gray-100 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-purple-500"
                  placeholder="Confirm new password"
                />
              </div>
              <button
                type="submit"
                disabled={passwordMutation.isPending}
                className="w-full text-white py-3 rounded-xl font-bold disabled:opacity-50"
                style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}
              >
                {passwordMutation.isPending ? 'Changing...' : 'Change Password'}
              </button>
            </form>
          ) : (
            <form onSubmit={handlePinSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Current PIN
                </label>
                <input
                  type="password"
                  value={oldPin}
                  onChange={(e) => setOldPin(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  required
                  maxLength={6}
                  className="w-full px-4 py-3 bg-gray-100 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-purple-500 text-center text-2xl tracking-widest"
                  placeholder="••••"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  New PIN (4-6 digits)
                </label>
                <input
                  type="password"
                  value={newPin}
                  onChange={(e) => setNewPin(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  required
                  maxLength={6}
                  className="w-full px-4 py-3 bg-gray-100 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-purple-500 text-center text-2xl tracking-widest"
                  placeholder="••••"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Confirm New PIN
                </label>
                <input
                  type="password"
                  value={confirmPin}
                  onChange={(e) => setConfirmPin(e.target.value.replace(/\D/g, '').slice(0, 6))}
                  required
                  maxLength={6}
                  className="w-full px-4 py-3 bg-gray-100 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-purple-500 text-center text-2xl tracking-widest"
                  placeholder="••••"
                />
              </div>
              <button
                type="submit"
                disabled={pinMutation.isPending}
                className="w-full text-white py-3 rounded-xl font-bold disabled:opacity-50"
                style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}
              >
                {pinMutation.isPending ? 'Changing...' : 'Change PIN'}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
