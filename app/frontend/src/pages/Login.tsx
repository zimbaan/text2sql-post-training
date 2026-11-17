import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { Loader2, LockKeyhole } from 'lucide-react';
import { useEffect } from 'react';

export const Login = () => {
  const { login, isLoading, user } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');

  useEffect(() => {
    if (user) {
      navigate('/', { replace: true });
    }
  }, [user, navigate]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await login(username, password);
      navigate('/', { replace: true });
    } catch (error: any) {
      const detail = error?.response?.data?.detail;
      const message =
        typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
            ? detail.map((d) => d.msg || JSON.stringify(d)).join('; ')
            : detail?.message || error?.message || 'Invalid credentials';
      toast({
        title: 'Login failed',
        description: message,
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 flex items-center justify-center px-4 py-10">
      <Card className="w-full max-w-xl shadow-2xl border-slate-800 bg-gradient-to-br from-slate-900/80 to-slate-800/80 text-white backdrop-blur">
        <CardHeader className="space-y-4">
          <div className="flex items-center justify-center gap-3">
            <img src="/logo-2.png" alt="NL-SQL Agent" className="w-12 h-12 rounded-lg shadow-md" />
            <div>
              <p className="text-sm text-slate-300">Welcome to</p>
              <CardTitle className="text-2xl">NL-SQL Agent</CardTitle>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-indigo-500/20 border border-indigo-500/40">
              <LockKeyhole className="w-6 h-6 text-indigo-300" />
            </div>
            <div>
              <CardTitle className="text-2xl">Welcome back</CardTitle>
              <CardDescription className="text-slate-300">
                Sign in to continue querying your databases securely.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="space-y-2">
              <Label htmlFor="username" className="text-slate-200">Username</Label>
              <Input
                id="username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="yourname"
                required
                className="bg-slate-900/70 border-slate-700 text-white"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password" className="text-slate-200">Password</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                className="bg-slate-900/70 border-slate-700 text-white"
              />
            </div>
            <Button type="submit" className="w-full bg-indigo-500 hover:bg-indigo-600" disabled={isLoading}>
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Login'}
            </Button>
          </form>
          <p className="text-sm text-slate-300 mt-4 text-center">
            Don&apos;t have an account?{' '}
            <Link to="/register" className="text-indigo-300 hover:text-indigo-200">
              Register
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
};
