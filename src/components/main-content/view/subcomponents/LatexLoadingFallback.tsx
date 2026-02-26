type LatexLoadingFallbackProps = {
  message?: string;
};

export default function LatexLoadingFallback({
  message = 'Loading LaTeX editing workspace...',
}: LatexLoadingFallbackProps) {
  return (
    <div className="h-full w-full flex items-center justify-center bg-background">
      <div className="flex items-center gap-3 text-sm text-muted-foreground">
        <span className="inline-block h-5 w-5 rounded-full border-2 border-primary/25 border-t-primary animate-spin" />
        <span>{message}</span>
      </div>
    </div>
  );
}
