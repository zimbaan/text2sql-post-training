import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '@/hooks/useAuth';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { useToast } from '@/hooks/use-toast';
import { Loader2, Sparkles } from 'lucide-react';

export const Register = () => {
  const { register, isLoading, user } = useAuth();
  const { toast } = useToast();
  const navigate = useNavigate();

  const [form, setForm] = useState({
    username: '',
    email: '',
    full_name: '',
    password: '',
  });

  useEffect(() => {
    if (user) {
      navigate('/', { replace: true });
    }
  }, [user, navigate]);

  const handleChange = (key: string, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await register({
        username: form.username,
        email: form.email || undefined,
        full_name: form.full_name || undefined,
        password: form.password,
      });
      navigate('/', { replace: true });
    } catch (error: any) {
      const detail = error?.response?.data?.detail;
      const message =
        typeof detail === 'string'
          ? detail
          : Array.isArray(detail)
            ? detail.map((d) => d.msg || JSON.stringify(d)).join('; ')
            : detail?.message || error?.message || 'Please try again';
      toast({
        title: 'Registration failed',
        description: message,
        variant: 'destructive',
      });
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-900 via-slate-900 to-slate-950 flex items-center justify-center px-4 py-10">
      <Card className="w-full max-w-2xl shadow-2xl border-emerald-800/60 bg-gradient-to-br from-slate-900/80 to-emerald-900/60 text-white backdrop-blur">
        <CardHeader className="space-y-4">
          <div className="flex items-center justify-center gap-3">
            <img src="/logo-2.png" alt="NL-SQL Agent" className="w-12 h-12 rounded-lg shadow-md" />
            <div>
              <p className="text-sm text-slate-200">Create your account for</p>
              <CardTitle className="text-2xl">NL-SQL Agent</CardTitle>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-emerald-500/20 border border-emerald-500/40">
              <Sparkles className="w-6 h-6 text-emerald-200" />
            </div>
            <div>
              <CardTitle className="text-2xl">Create your account</CardTitle>
              <CardDescription className="text-slate-200">
                Personalize your workspace and keep your history in sync.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <form className="space-y-5" onSubmit={handleSubmit}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="username" className="text-slate-200">Username</Label>
                <Input
                  id="username"
                  value={form.username}
                  onChange={(e) => handleChange('username', e.target.value)}
                  placeholder="yourname"
                  required
                  className="bg-slate-900/70 border-slate-700 text-white"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="full_name" className="text-slate-200">Full name</Label>
                <Input
                  id="full_name"
                  value={form.full_name}
                  onChange={(e) => handleChange('full_name', e.target.value)}
                  placeholder="Jane Doe"
                  className="bg-slate-900/70 border-slate-700 text-white"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email" className="text-slate-200">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={form.email}
                  onChange={(e) => handleChange('email', e.target.value)}
                  placeholder="you@example.com"
                  className="bg-slate-900/70 border-slate-700 text-white"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password" className="text-slate-200">Password</Label>
                <Input
                  id="password"
                  type="password"
                  value={form.password}
                  onChange={(e) => handleChange('password', e.target.value)}
                  placeholder="••••••••"
                  required
                  className="bg-slate-900/70 border-slate-700 text-white"
                />
              </div>
            </div>
            <Button type="submit" className="w-full bg-emerald-500 hover:bg-emerald-600" disabled={isLoading}>
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Create account'}
            </Button>
          </form>
          <p className="text-sm text-slate-200 mt-4 text-center">
            Already have an account?{' '}
            <Link to="/login" className="text-emerald-200 hover:text-emerald-100">
              Login
            </Link>
          </p>
        </CardContent>
      </Card>
    </div>
  );
};
