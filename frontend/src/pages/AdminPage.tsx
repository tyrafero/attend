import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminApi, type Employee, type Department, type Shift, type CreateEmployeeData, type UpdateEmployeeData } from '../api/admin';

type Tab = 'employees' | 'departments' | 'shifts';

export function AdminPage() {
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [activeTab, setActiveTab] = useState<Tab>('employees');
  const [showEmployeeModal, setShowEmployeeModal] = useState(false);
  const [editingEmployee, setEditingEmployee] = useState<Employee | null>(null);
  const [showDeptModal, setShowDeptModal] = useState(false);
  const [editingDept, setEditingDept] = useState<Department | null>(null);

  // Check authorization
  const isHRAdmin = user?.employee_profile?.role === 'HR_ADMIN';

  // Fetch data
  const { data: employees, isLoading: employeesLoading } = useQuery({
    queryKey: ['admin', 'employees'],
    queryFn: () => adminApi.getEmployees({ show_inactive: true }),
  });

  const { data: departments } = useQuery({
    queryKey: ['admin', 'departments'],
    queryFn: adminApi.getDepartments,
  });

  const { data: shifts } = useQuery({
    queryKey: ['admin', 'shifts'],
    queryFn: adminApi.getShifts,
  });

  const { data: managers } = useQuery({
    queryKey: ['admin', 'managers'],
    queryFn: adminApi.getManagers,
    enabled: isHRAdmin,
  });

  // Mutations
  const createEmployee = useMutation({
    mutationFn: adminApi.createEmployee,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'employees'] });
      setShowEmployeeModal(false);
    },
  });

  const updateEmployee = useMutation({
    mutationFn: ({ id, data }: { id: number; data: UpdateEmployeeData }) =>
      adminApi.updateEmployee(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'employees'] });
      setShowEmployeeModal(false);
      setEditingEmployee(null);
    },
  });

  const updateDepartment = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { manager?: number | null } }) =>
      adminApi.updateDepartment(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'departments'] });
      setShowDeptModal(false);
      setEditingDept(null);
    },
  });

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  if (!isHRAdmin) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}>
        <div className="bg-white rounded-xl shadow-lg p-8 text-center">
          <h1 className="text-2xl font-bold text-red-600 mb-4">Access Denied</h1>
          <p className="text-gray-600 mb-4">Only HR Admins can access this page.</p>
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
                <h1 className="text-xl font-bold text-gray-900">Admin Panel</h1>
                <p className="text-xs text-gray-500">Manage Employees, Departments & Shifts</p>
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

      {/* Tabs */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6">
        <div className="flex gap-2 bg-white/20 p-1 rounded-lg w-fit">
          {(['employees', 'departments', 'shifts'] as Tab[]).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                activeTab === tab
                  ? 'bg-white text-gray-900 shadow'
                  : 'text-white hover:bg-white/20'
              }`}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {/* Employees Tab */}
        {activeTab === 'employees' && (
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-lg font-bold text-gray-900">Employees ({employees?.length || 0})</h2>
              <button
                onClick={() => {
                  setEditingEmployee(null);
                  setShowEmployeeModal(true);
                }}
                className="px-4 py-2 rounded-lg text-white text-sm font-medium"
                style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}
              >
                + Add Employee
              </button>
            </div>

            {employeesLoading ? (
              <p className="text-gray-500 text-center py-8">Loading...</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full">
                  <thead>
                    <tr className="border-b border-gray-200">
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">ID</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Name</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Username</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Department</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Role</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Manager</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Status</th>
                      <th className="px-3 py-3 text-left text-xs font-semibold text-gray-500 uppercase">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {employees?.map((emp, idx) => (
                      <tr key={emp.id} className={idx % 2 === 0 ? 'bg-gray-50' : 'bg-white'}>
                        <td className="px-3 py-3 text-sm text-gray-700">{emp.employee_id}</td>
                        <td className="px-3 py-3 text-sm font-medium text-gray-900">{emp.employee_name}</td>
                        <td className="px-3 py-3 text-sm text-gray-700">{emp.username}</td>
                        <td className="px-3 py-3 text-sm text-gray-700">{emp.department_name}</td>
                        <td className="px-3 py-3 text-sm">
                          <span className={`px-2 py-1 rounded-full text-xs ${
                            emp.role === 'HR_ADMIN' ? 'bg-purple-100 text-purple-700' :
                            emp.role === 'MANAGER' ? 'bg-blue-100 text-blue-700' :
                            'bg-gray-100 text-gray-700'
                          }`}>
                            {emp.role === 'HR_ADMIN' ? 'HR Admin' : emp.role === 'MANAGER' ? 'Manager' : 'Employee'}
                          </span>
                        </td>
                        <td className="px-3 py-3 text-sm text-gray-700">{emp.manager_name || '-'}</td>
                        <td className="px-3 py-3 text-sm">
                          <span className={`px-2 py-1 rounded-full text-xs ${
                            emp.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'
                          }`}>
                            {emp.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                        <td className="px-3 py-3 text-sm">
                          <button
                            onClick={() => {
                              setEditingEmployee(emp);
                              setShowEmployeeModal(true);
                            }}
                            className="text-purple-600 hover:text-purple-800 mr-2"
                          >
                            Edit
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* Departments Tab */}
        {activeTab === 'departments' && (
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Departments</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {departments?.map((dept) => (
                <div key={dept.id} className="border border-gray-200 rounded-lg p-4">
                  <div className="flex justify-between items-start mb-2">
                    <div>
                      <p className="font-semibold text-gray-900">{dept.name}</p>
                      <p className="text-xs text-gray-500">{dept.code}</p>
                    </div>
                    <span className="text-xs px-2 py-1 bg-purple-100 text-purple-700 rounded-full">
                      {dept.employee_count} staff
                    </span>
                  </div>
                  <div className="mt-3 pt-3 border-t border-gray-100">
                    <p className="text-xs text-gray-500">Manager</p>
                    <p className="text-sm font-medium text-gray-900">
                      {dept.manager_name || 'Not assigned'}
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      setEditingDept(dept);
                      setShowDeptModal(true);
                    }}
                    className="mt-3 text-sm text-purple-600 hover:text-purple-800"
                  >
                    Assign Manager
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Shifts Tab */}
        {activeTab === 'shifts' && (
          <div className="bg-white rounded-xl shadow-lg p-6">
            <h2 className="text-lg font-bold text-gray-900 mb-4">Shifts</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {shifts?.map((shift) => (
                <div key={shift.id} className="border border-gray-200 rounded-lg p-4">
                  <p className="font-semibold text-gray-900">{shift.name}</p>
                  <p className="text-sm text-gray-600 mt-1">
                    {shift.start_time?.slice(0, 5)} - {shift.end_time?.slice(0, 5)}
                  </p>
                  <div className="mt-3 grid grid-cols-2 gap-2 text-xs">
                    <div>
                      <p className="text-gray-500">Hours</p>
                      <p className="font-medium">{shift.scheduled_hours}h</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Break</p>
                      <p className="font-medium">{shift.break_duration_hours}h</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Early Grace</p>
                      <p className="font-medium">{shift.early_arrival_grace_minutes} min</p>
                    </div>
                    <div>
                      <p className="text-gray-500">Late Grace</p>
                      <p className="font-medium">{shift.late_departure_grace_minutes} min</p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>

      {/* Employee Modal */}
      {showEmployeeModal && (
        <EmployeeModal
          employee={editingEmployee}
          departments={departments || []}
          shifts={shifts || []}
          managers={managers || []}
          onClose={() => {
            setShowEmployeeModal(false);
            setEditingEmployee(null);
          }}
          onSave={(data) => {
            if (editingEmployee) {
              updateEmployee.mutate({ id: editingEmployee.id, data: data as UpdateEmployeeData });
            } else {
              createEmployee.mutate(data as CreateEmployeeData);
            }
          }}
          isLoading={createEmployee.isPending || updateEmployee.isPending}
          error={createEmployee.error || updateEmployee.error}
        />
      )}

      {/* Department Manager Modal */}
      {showDeptModal && editingDept && (
        <DepartmentModal
          department={editingDept}
          managers={managers || []}
          onClose={() => {
            setShowDeptModal(false);
            setEditingDept(null);
          }}
          onSave={(managerId) => {
            updateDepartment.mutate({ id: editingDept.id, data: { manager: managerId } });
          }}
          isLoading={updateDepartment.isPending}
        />
      )}
    </div>
  );
}

// Employee Modal Component
function EmployeeModal({
  employee,
  departments,
  shifts,
  managers,
  onClose,
  onSave,
  isLoading,
  error,
}: {
  employee: Employee | null;
  departments: Department[];
  shifts: Shift[];
  managers: Employee[];
  onClose: () => void;
  onSave: (data: CreateEmployeeData | UpdateEmployeeData) => void;
  isLoading: boolean;
  error: Error | null;
}) {
  const [form, setForm] = useState({
    employee_id: employee?.employee_id || '',
    employee_name: employee?.employee_name || '',
    email: employee?.email || '',
    department: employee?.department?.toString() || '',
    role: employee?.role || 'EMPLOYEE',
    manager: employee?.manager?.toString() || '',
    default_shift: employee?.default_shift?.toString() || '',
    is_active: employee?.is_active ?? true,
    username: '',
    password: '',
    pin: '',
    new_password: '',
    new_pin: '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (employee) {
      // Update existing employee
      const data: UpdateEmployeeData = {
        employee_name: form.employee_name,
        email: form.email,
        department: Number(form.department),
        role: form.role,
        manager: form.manager ? Number(form.manager) : null,
        default_shift: form.default_shift ? Number(form.default_shift) : null,
        is_active: form.is_active,
      };
      if (form.new_password) data.new_password = form.new_password;
      if (form.new_pin) data.new_pin = form.new_pin;
      onSave(data);
    } else {
      // Create new employee
      onSave({
        employee_id: form.employee_id,
        employee_name: form.employee_name,
        email: form.email,
        department: Number(form.department),
        role: form.role,
        manager: form.manager ? Number(form.manager) : null,
        default_shift: form.default_shift ? Number(form.default_shift) : null,
        username: form.username,
        password: form.password,
        pin: form.pin,
      });
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-4">
            {employee ? 'Edit Employee' : 'Add New Employee'}
          </h3>

          <form onSubmit={handleSubmit} className="space-y-4">
            {!employee && (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Employee ID *</label>
                    <input
                      type="text"
                      value={form.employee_id}
                      onChange={(e) => setForm({ ...form, employee_id: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                      required
                      placeholder="EMP001"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Username *</label>
                    <input
                      type="text"
                      value={form.username}
                      onChange={(e) => setForm({ ...form, username: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                      required
                      placeholder="johndoe"
                    />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Password *</label>
                    <input
                      type="password"
                      value={form.password}
                      onChange={(e) => setForm({ ...form, password: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                      required
                      minLength={6}
                      placeholder="Min 6 chars"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">PIN *</label>
                    <input
                      type="password"
                      value={form.pin}
                      onChange={(e) => setForm({ ...form, pin: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                      required
                      minLength={4}
                      maxLength={6}
                      placeholder="4-6 digits"
                    />
                  </div>
                </div>
              </>
            )}

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Full Name *</label>
              <input
                type="text"
                value={form.employee_name}
                onChange={(e) => setForm({ ...form, employee_name: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                required
                placeholder="John Doe"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                required
                placeholder="john@company.com"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Department *</label>
                <select
                  value={form.department}
                  onChange={(e) => setForm({ ...form, department: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  required
                >
                  <option value="">Select...</option>
                  {departments.map((d) => (
                    <option key={d.id} value={d.id}>{d.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Role *</label>
                <select
                  value={form.role}
                  onChange={(e) => setForm({ ...form, role: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                  required
                >
                  <option value="EMPLOYEE">Employee</option>
                  <option value="MANAGER">Manager</option>
                  <option value="HR_ADMIN">HR Admin</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Manager</label>
                <select
                  value={form.manager}
                  onChange={(e) => setForm({ ...form, manager: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  <option value="">None</option>
                  {managers.map((m) => (
                    <option key={m.id} value={m.id}>{m.employee_name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Default Shift</label>
                <select
                  value={form.default_shift}
                  onChange={(e) => setForm({ ...form, default_shift: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                >
                  <option value="">None</option>
                  {shifts.map((s) => (
                    <option key={s.id} value={s.id}>{s.name} ({s.start_time?.slice(0,5)} - {s.end_time?.slice(0,5)})</option>
                  ))}
                </select>
              </div>
            </div>

            {employee && (
              <>
                <div className="border-t pt-4 mt-4">
                  <p className="text-sm font-medium text-gray-700 mb-2">Reset Credentials (leave blank to keep current)</p>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm text-gray-600 mb-1">New Password</label>
                      <input
                        type="password"
                        value={form.new_password}
                        onChange={(e) => setForm({ ...form, new_password: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                        minLength={6}
                        placeholder="Min 6 chars"
                      />
                    </div>
                    <div>
                      <label className="block text-sm text-gray-600 mb-1">New PIN</label>
                      <input
                        type="password"
                        value={form.new_pin}
                        onChange={(e) => setForm({ ...form, new_pin: e.target.value })}
                        className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
                        minLength={4}
                        maxLength={6}
                        placeholder="4-6 digits"
                      />
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    id="isActive"
                    checked={form.is_active}
                    onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                    className="rounded border-gray-300"
                  />
                  <label htmlFor="isActive" className="text-sm text-gray-700">Active Employee</label>
                </div>
              </>
            )}

            {error && (
              <p className="text-red-600 text-sm">
                {(error as any)?.response?.data?.employee_id?.[0] ||
                 (error as any)?.response?.data?.username?.[0] ||
                 (error as any)?.response?.data?.detail ||
                 'An error occurred. Please try again.'}
              </p>
            )}

            <div className="flex gap-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isLoading}
                className="flex-1 px-4 py-2 rounded-lg text-white font-medium disabled:opacity-50"
                style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}
              >
                {isLoading ? 'Saving...' : (employee ? 'Update' : 'Create')}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

// Department Manager Modal Component
function DepartmentModal({
  department,
  managers,
  onClose,
  onSave,
  isLoading,
}: {
  department: Department;
  managers: Employee[];
  onClose: () => void;
  onSave: (managerId: number | null) => void;
  isLoading: boolean;
}) {
  const [selectedManager, setSelectedManager] = useState(department.manager?.toString() || '');

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-md">
        <div className="p-6">
          <h3 className="text-lg font-bold text-gray-900 mb-2">Assign Manager</h3>
          <p className="text-sm text-gray-600 mb-4">Assign a manager to {department.name}</p>

          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">Department Manager</label>
            <select
              value={selectedManager}
              onChange={(e) => setSelectedManager(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-500"
            >
              <option value="">No Manager</option>
              {managers.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.employee_name} ({m.department_name})
                </option>
              ))}
            </select>
          </div>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={() => onSave(selectedManager ? Number(selectedManager) : null)}
              disabled={isLoading}
              className="flex-1 px-4 py-2 rounded-lg text-white font-medium disabled:opacity-50"
              style={{ background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' }}
            >
              {isLoading ? 'Saving...' : 'Save'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
