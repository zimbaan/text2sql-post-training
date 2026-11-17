import { AlertCircle } from 'lucide-react';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Button } from '@/components/ui/button';

interface ErrorBannerProps {
  title?: string;
  message: string;
  retry?: () => void;
}

export const ErrorBanner = ({ title = 'Error', message, retry }: ErrorBannerProps) => {
  return (
    <Alert variant="destructive" className="mb-4">
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription className="flex items-center justify-between">
        <span>{message}</span>
        {retry && (
          <Button variant="outline" size="sm" onClick={retry} className="ml-4">
            Retry
          </Button>
        )}
      </AlertDescription>
    </Alert>
  );
};
