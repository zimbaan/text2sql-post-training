import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Copy, Check } from 'lucide-react';
import { useState } from 'react';
import { NLQExplainResult } from '@/lib/types';

interface SQLPreviewProps {
  sql: string;
  explainResult?: NLQExplainResult | null;
}

export const SQLPreview = ({ sql, explainResult }: SQLPreviewProps) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">Generated SQL</CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopy}
            className="gap-2"
          >
            {copied ? (
              <>
                <Check className="w-4 h-4" />
                Copied
              </>
            ) : (
              <>
                <Copy className="w-4 h-4" />
                Copy
              </>
            )}
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm">
          <code>{sql}</code>
        </pre>

        {explainResult && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Badge variant={explainResult.is_read_only ? 'default' : 'destructive'}>
                {explainResult.is_read_only ? 'Read-Only' : 'Write Operation'}
              </Badge>
              {explainResult.limit_applied && (
                <Badge variant="secondary">Limit Applied</Badge>
              )}
              {explainResult.generated_by && (
                <Badge variant="outline" title="Model that generated this SQL">
                  {explainResult.generated_by}
                </Badge>
              )}
              <div className="ml-auto">
                <span className="text-sm text-muted-foreground">Confidence: </span>
                <span
                  className={`font-semibold ${
                    explainResult.confidence >= 0.8
                      ? 'text-success'
                      : explainResult.confidence >= 0.5
                      ? 'text-warning'
                      : 'text-destructive'
                  }`}
                >
                  {Math.round(explainResult.confidence * 100)}%
                </span>
              </div>
            </div>

            <div>
              <h4 className="text-sm font-semibold mb-2">Reasoning</h4>
              <p className="text-sm text-muted-foreground">{explainResult.reasoning}</p>
            </div>

            {explainResult.parameters && Object.keys(explainResult.parameters).length > 0 && (
              <div>
                <h4 className="text-sm font-semibold mb-2">Parameters</h4>
                <pre className="bg-muted p-3 rounded text-xs overflow-x-auto">
                  <code>{JSON.stringify(explainResult.parameters, null, 2)}</code>
                </pre>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
};
