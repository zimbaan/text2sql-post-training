import { QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from '@/components/ui/toaster';
import { Toaster as Sonner } from '@/components/ui/sonner';
import { TooltipProvider } from '@/components/ui/tooltip';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { queryClient } from '@/store/queryClient';
import { ConnectionBadge } from '@/features/connection/ConnectionBadge';
import { ModelPicker } from '@/features/models/ModelPicker';
import { Dashboard } from './pages/Dashboard';
import { Playground } from './pages/Playground';
import { History } from './pages/History';
import { Visualization } from './pages/Visualization';
import NotFound from './pages/NotFound';
import { Database } from 'lucide-react';
import { ConnectionProvider } from '@/hooks/useConnection';
import { SelectedModelProvider } from '@/hooks/useSelectedModel';
import { AuthProvider, useAuth } from '@/hooks/useAuth';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { Profile } from './pages/Profile';
import { ProtectedRoute } from './components/common/ProtectedRoute';
import { Button } from './components/ui/button';

const Navbar = () => {
  const { user, logout } = useAuth();
  if (!user) return null;
  return (
    <header className="border-b border-slate-800 bg-slate-950/70 backdrop-blur sticky top-0 z-50">
      <div className="container mx-auto px-6 py-4 text-slate-100">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-8">
            <Link to="/" className="flex items-center gap-2 font-bold text-xl">
              <img src="/logo-2.png" alt="NL-SQL Agent" className="w-10 h-10 rounded-md shadow-md" />
              <span className="text-white">NL-SQL Agent</span>
            </Link>
            <nav className="flex items-center gap-1">
              <Link
                to="/"
                className="px-4 py-2 rounded-lg hover:bg-white/10 transition-colors text-sm font-medium text-slate-100"
              >
                Dashboard
              </Link>
              <Link
                to="/playground"
                className="px-4 py-2 rounded-lg hover:bg-white/10 transition-colors text-sm font-medium text-slate-100"
              >
                Playground
              </Link>
              <Link
                to="/history"
                className="px-4 py-2 rounded-lg hover:bg-white/10 transition-colors text-sm font-medium text-slate-100"
              >
                History
              </Link>
              <Link
                to="/visualization"
                className="px-4 py-2 rounded-lg hover:bg-white/10 transition-colors text-sm font-medium text-slate-100"
              >
                Visualization
              </Link>
            </nav>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 rounded-full bg-white/10 px-3 py-2 border border-white/15 shadow">
              <ModelPicker />
              <ConnectionBadge />
            </div>
            {user ? (
              <Link
                to="/profile"
                className="flex items-center gap-2 text-sm font-medium text-slate-100 hover:text-white"
              >
                <span className="w-9 h-9 rounded-full bg-slate-200 text-slate-900 grid place-items-center font-semibold shadow">
                  {(user.full_name || user.username || '?').trim().charAt(0).toUpperCase()}
                </span>
                <span className="hidden md:inline">{user.full_name || user.username}</span>
              </Link>
            ) : (
              <div className="flex items-center gap-2">
                <Link to="/login" className="text-sm font-medium text-slate-100 hover:text-white">
                  Login
                </Link>
                <Link to="/register" className="text-sm font-medium text-slate-100 hover:text-white">
                  Register
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};

const App = () => (
  <QueryClientProvider client={queryClient}>
    <AuthProvider>
      <ConnectionProvider>
        <SelectedModelProvider>
        <TooltipProvider>
          <Toaster />
          <Sonner />
          <BrowserRouter>
            <div className="min-h-screen text-slate-100">
              <Navbar />
              <Routes>
                <Route
                  path="/"
                  element={
                    <ProtectedRoute>
                      <Dashboard />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/playground"
                  element={
                    <ProtectedRoute>
                      <Playground />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/history"
                  element={
                    <ProtectedRoute>
                      <History />
                    </ProtectedRoute>
                  }
                />
                <Route
                  path="/visualization"
                  element={
                    <ProtectedRoute>
                      <Visualization />
                    </ProtectedRoute>
                  }
                />
                <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </div>
          </BrowserRouter>
        </TooltipProvider>
        </SelectedModelProvider>
      </ConnectionProvider>
    </AuthProvider>
  </QueryClientProvider>
);

export default App;
