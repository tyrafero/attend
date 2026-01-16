import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';

export function LoginPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const login = useAuthStore((state) => state.login);
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login(username, password);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || err.response?.data?.non_field_errors?.[0] || 'Login failed. Please check your credentials.');
    } finally {
      setIsLoading(false);
    }
  };

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
        <h1 className="text-2xl font-bold text-center text-gray-800 mb-1">Manager Login</h1>
        <p className="text-gray-500 text-center mb-5 text-sm">Sign in to access the dashboard</p>

        {/* Error Message */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 text-red-600 rounded-lg text-center text-sm">
            {error}
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
              Username
            </label>
            <input
              id="username"
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              className="w-full px-4 py-3 bg-gray-100 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-purple-500 transition-colors"
              placeholder="Enter your username"
              disabled={isLoading}
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-4 py-3 bg-gray-100 border-2 border-gray-200 rounded-xl focus:outline-none focus:border-purple-500 transition-colors"
              placeholder="Enter your password"
              disabled={isLoading}
            />
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="w-full text-white py-4 px-4 rounded-xl hover:opacity-90 focus:outline-none disabled:bg-gray-400 disabled:cursor-not-allowed transition-all text-lg font-bold mt-2"
            style={{ background: isLoading ? '#999' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}
          >
            {isLoading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>

        {/* Back to Attendance Link */}
        <div className="mt-5 text-center">
          <a
            href="/"
            className="text-sm hover:underline"
            style={{ color: '#667eea' }}
          >
            ← Back to Attendance
          </a>
        </div>
      </div>
    </div>
  );
}
