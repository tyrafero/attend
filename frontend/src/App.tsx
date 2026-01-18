import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { LoginPage } from './pages/LoginPage';
import { KioskPage } from './pages/KioskPage';
import { DashboardPage } from './pages/DashboardPage';
import { ShiftManagementPage } from './pages/ShiftManagementPage';
import { TILPage } from './pages/TILPage';
import { LeavePage } from './pages/LeavePage';
import { ProtectedRoute } from './components/ProtectedRoute';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          {/* Attendance Clock In/Out - Main Page */}
          <Route path="/" element={<KioskPage />} />

          {/* Admin/Manager Login */}
          <Route path="/login" element={<LoginPage />} />

          {/* Protected Routes */}
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <DashboardPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/shifts"
            element={
              <ProtectedRoute>
                <ShiftManagementPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/til"
            element={
              <ProtectedRoute>
                <TILPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/leave"
            element={
              <ProtectedRoute>
                <LeavePage />
              </ProtectedRoute>
            }
          />

          {/* 404 - redirect to main attendance page */}
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
