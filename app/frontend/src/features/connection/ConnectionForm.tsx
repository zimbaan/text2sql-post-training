import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useConnection } from '@/hooks/useConnection';
import { ConnectPayload } from '@/lib/types';
import { Database, Loader2 } from 'lucide-react';
import { useToast } from '@/hooks/use-toast';

const formatErrorMessage = (error: any) => {
  const detail = error?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail[0]?.msg) return detail[0].msg;
  if (detail?.error?.message) return detail.error.message;
  if (detail?.message) return detail.message;
  return error?.message || 'Connection failed';
};

export const ConnectionForm = () => {
  const { connect, disconnect, isConnected, isConnecting, connectionId, clearStaleConnection } = useConnection();
  const { toast } = useToast();
  const [formData, setFormData] = useState<ConnectPayload>({
    dialect: 'postgresql',
    host: 'localhost',
    port: 5432,
    username: '',
    password: '',
    database: '',
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Normalize payload for backend expectations
    const payload: ConnectPayload = { ...formData };
    if (payload.dialect === 'sqlite') {
      // Backend expects "database" to carry the sqlite file path
      payload.database = payload.file_path || '';
      // SQLite does not use these fields
      delete payload.host;
      delete payload.port;
      delete payload.username;
      delete payload.password;
    }

    connect(payload, {
      onSuccess: () => {
        toast({
          title: 'Connected',
          description: 'Successfully connected to the database',
        });
      },
      onError: (error: any) => {
        toast({
          title: 'Connection failed',
          description: formatErrorMessage(error),
          variant: 'destructive',
        });
      },
    });
  };

  if (isConnected && connectionId) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="w-5 h-5" />
            Connected
          </CardTitle>
          <CardDescription>Database connection is active</CardDescription>
        </CardHeader>
        <CardContent>
          <Button 
            onClick={() => {
              if (connectionId) {
                disconnect();
              } else {
                // If no connectionId but still showing as connected, clear state
                clearStaleConnection();
              }
            }} 
            variant="destructive" 
            className="w-full"
            disabled={isConnecting}
          >
            Disconnect
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Database className="w-5 h-5" />
          Database Connection
        </CardTitle>
        <CardDescription>Connect to your database</CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
              <Label htmlFor="dialect">Database Type</Label>
              <Select
                value={formData.dialect}
                onValueChange={(value: any) => setFormData({ ...formData, dialect: value })}
              >
                <SelectTrigger id="dialect">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="postgresql">PostgreSQL</SelectItem>
                  <SelectItem value="mysql">MySQL</SelectItem>
                  <SelectItem value="sqlite">SQLite</SelectItem>
                </SelectContent>
              </Select>
            </div>

          {formData.dialect !== 'sqlite' && (
            <>
              <div>
                <Label htmlFor="host">Host</Label>
                <Input
                  id="host"
                  value={formData.host ?? ''}
                  onChange={(e) => setFormData({ ...formData, host: e.target.value })}
                  placeholder="localhost"
                />
              </div>

              <div>
                <Label htmlFor="port">Port</Label>
                <Input
                  id="port"
                  type="number"
                  value={formData.port ?? ''}
                  onChange={(e) => {
                    const value = e.target.value;
                    setFormData({ ...formData, port: value ? parseInt(value, 10) : undefined });
                  }}
                  placeholder="5432"
                />
              </div>

              <div>
                <Label htmlFor="username">Username</Label>
                <Input
                  id="username"
                  value={formData.username ?? ''}
                  onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                  placeholder="postgres"
                />
              </div>

              <div>
                <Label htmlFor="password">Password</Label>
                <Input
                  id="password"
                  type="password"
                  value={formData.password ?? ''}
                  onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                />
              </div>

              <div>
                <Label htmlFor="database">Database</Label>
                <Input
                  id="database"
                  value={formData.database ?? ''}
                  onChange={(e) => setFormData({ ...formData, database: e.target.value })}
                  placeholder="mydb"
                />
              </div>
            </>
          )}

          {formData.dialect === 'sqlite' && (
            <div>
              <Label htmlFor="file_path">Database File</Label>
              <Input
                id="file_path"
                value={formData.file_path ?? ''}
                onChange={(e) => setFormData({ ...formData, file_path: e.target.value })}
                placeholder="/path/to/database.db"
              />
            </div>
          )}

          <Button type="submit" className="w-full" disabled={isConnecting}>
            {isConnecting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            Connect
          </Button>
        </form>
      </CardContent>
    </Card>
  );
};
