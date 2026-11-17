interface JsonPreviewProps {
  data: any;
  className?: string;
}

export const JsonPreview = ({ data, className = '' }: JsonPreviewProps) => {
  return (
    <pre className={`bg-muted rounded-lg p-4 overflow-auto text-sm ${className}`}>
      <code>{JSON.stringify(data, null, 2)}</code>
    </pre>
  );
};
