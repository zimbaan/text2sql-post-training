import { Database, Shield } from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { useConnection } from '@/hooks/useConnection';
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip';
import { useSafeMode } from '@/hooks/useSafeMode';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';

export const ConnectionBadge = () => {
  const { connection, isConnected } = useConnection();
  const { safeModeEnabled, setSafeMode, isLoading } = useSafeMode();

  if (!isConnected || !connection) {
    return (
      <Badge variant="secondary" className="gap-1">
        <Database className="w-3 h-3" />
        Not Connected
      </Badge>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <Badge variant="secondary" className="gap-1">
        <Database className="w-3 h-3" />
        {connection.default_database || 'Connected'}
      </Badge>
      <Tooltip>
        <TooltipTrigger>
          <Badge variant={safeModeEnabled ? 'secondary' : 'outline'} className="gap-1">
            <Shield className="w-3 h-3" />
            {safeModeEnabled ? 'Read-Only' : 'Writes Allowed'}
          </Badge>
        </TooltipTrigger>
        <TooltipContent className="space-y-2">
          <p className="text-sm">
            Safe mode {safeModeEnabled ? 'is enabled. Only SELECT queries are executed.' : 'is disabled. DML/DDL allowed with confirmation.'}
          </p>
          <div className="flex items-center justify-between">
            <Label htmlFor="safe-mode-toggle" className="text-xs">Safe Mode</Label>
            <Switch
              id="safe-mode-toggle"
              checked={safeModeEnabled}
              onCheckedChange={(value) => setSafeMode(value)}
              disabled={isLoading}
            />
          </div>
        </TooltipContent>
      </Tooltip>
    </div>
  );
};
