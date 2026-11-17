import { useEffect, useState } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { useToast } from '@/hooks/use-toast';
import { api } from '@/lib/api';
import { Loader2, RefreshCcw, Shield, User, LogOut } from 'lucide-react';

export const Profile = () => {
  const { user, refetchProfile, logout } = useAuth();
  const { toast } = useToast();
  const [form, setForm] = useState({ email: '', full_name: '', password: '' });
  const [apiKey, setApiKey] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isLoadingKey, setIsLoadingKey] = useState(false);

  useEffect(() => {
    if (user) {
      setForm({
        email: user.email || '',
        full_name: user.full_name || '',
        password: '',
      });
    }
  }, [user]);

  const fetchApiKey = async () => {
    try {
      setIsLoadingKey(true);
      const res = await api.get<{ api_key: string }>('/auth/me/api-key');
      setApiKey(res.data.api_key);
    } catch (error: any) {
      toast({
        title: 'API key not found',
        description: error?.response?.data?.detail || 'Generate a new key below.',
      });
    } finally {
      setIsLoadingKey(false);
    }
  };

  const regenerateApiKey = async () => {
    try {
      setIsLoadingKey(true);
      const res = await api.post<{ api_key: string }>('/auth/me/api-key');
      setApiKey(res.data.api_key);
      toast({ title: 'API key regenerated' });
    } catch (error: any) {
      toast({
        title: 'Failed to regenerate',
        description: error?.response?.data?.detail || 'Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsLoadingKey(false);
    }
  };

  const handleSave = async () => {
    try {
      setIsSaving(true);
      const payload: Record<string, string> = {};
      if (form.email) payload.email = form.email;
      if (form.full_name) payload.full_name = form.full_name;
      if (form.password) payload.password = form.password;
      await api.put('/auth/me', payload);
      await refetchProfile();
      toast({ title: 'Profile updated' });
      setForm((prev) => ({ ...prev, password: '' }));
    } catch (error: any) {
      toast({
        title: 'Update failed',
        description: error?.response?.data?.detail || 'Please try again.',
        variant: 'destructive',
      });
    } finally {
      setIsSaving(false);
    }
  };

  if (!user) return null;

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 py-10 px-6">
      <div className="max-w-5xl mx-auto space-y-8">
        <div className="flex items-center gap-3">
          <div className="p-3 rounded-xl bg-indigo-500/20 border border-indigo-500/40">
            <User className="w-6 h-6 text-indigo-200" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-white">Profile</h1>
            <p className="text-slate-300">Manage your identity, API key, and preferences.</p>
          </div>
          <div className="ml-auto">
            <Button variant="secondary" className="bg-slate-200 text-slate-900 hover:bg-slate-300 gap-2" onClick={logout}>
              <LogOut className="w-4 h-4" />
              Logout
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card className="bg-slate-900/70 border-slate-800 text-white">
            <CardHeader>
              <CardTitle>Profile details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="username" className="text-slate-300">Username</Label>
                <Input id="username" value={user.username} disabled className="bg-slate-800 border-slate-700 text-white" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="full_name" className="text-slate-300">Full name</Label>
                <Input
                  id="full_name"
                  value={form.full_name}
                  onChange={(e) => setForm((p) => ({ ...p, full_name: e.target.value }))}
                  className="bg-slate-800 border-slate-700 text-white"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="email" className="text-slate-300">Email</Label>
                <Input
                  id="email"
                  type="email"
                  value={form.email}
                  onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))}
                  className="bg-slate-800 border-slate-700 text-white"
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="password" className="text-slate-300">New password</Label>
                <Input
                  id="password"
                  type="password"
                  value={form.password}
                  onChange={(e) => setForm((p) => ({ ...p, password: e.target.value }))}
                  placeholder="Leave blank to keep current"
                  className="bg-slate-800 border-slate-700 text-white"
                />
              </div>
              <Button className="w-full bg-indigo-500 hover:bg-indigo-600" onClick={handleSave} disabled={isSaving}>
                {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Save changes'}
              </Button>
            </CardContent>
          </Card>

          <Card className="bg-slate-900/70 border-slate-800 text-white">
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-emerald-300" />
                API Access
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-slate-300">
                Use your API key to call endpoints programmatically. Keep it secret.
              </p>
              <div className="flex items-center gap-2">
                <Input
                  value={apiKey || '••••••••••••••••'}
                  readOnly
                  className="bg-slate-800 border-slate-700 text-white font-mono"
                />
                <Button
                  variant="outline"
                  onClick={apiKey ? () => navigator.clipboard.writeText(apiKey) : fetchApiKey}
                  disabled={isLoadingKey}
                >
                  {isLoadingKey ? <Loader2 className="w-4 h-4 animate-spin" /> : apiKey ? 'Copy' : 'Fetch'}
                </Button>
              </div>
              <Separator className="bg-slate-800" />
              <Button
                variant="secondary"
                className="gap-2"
                onClick={regenerateApiKey}
                disabled={isLoadingKey}
              >
                <RefreshCcw className="w-4 h-4" />
                Regenerate key
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};
