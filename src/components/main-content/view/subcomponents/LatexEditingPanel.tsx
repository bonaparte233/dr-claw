import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from 'react';
import type { Project } from '../../../../types/app';
import { api } from '../../../../utils/api';
import { Button } from '../../../ui/button';
import LatexLoadingFallback from './LatexLoadingFallback';

const LazyLatexLabEmbeddedWorkspace = lazy(
  () => import('../../../latexlab/LatexLabEmbeddedWorkspace'),
);

type LatexEditingPanelProps = {
  selectedProject: Project;
  preferredTexPath?: string;
};

type OpenFromVibeLabResponse = {
  ok?: boolean;
  projectId?: string;
  openFile?: string;
  needsTemplateBootstrap?: boolean;
  error?: string;
};

type LatexLabTemplate = {
  id: string;
  label?: string;
  description?: string;
  descriptionEn?: string;
};

type TemplateListResponse = {
  templates?: LatexLabTemplate[];
};

type ApplyTemplateResponse = {
  ok?: boolean;
  mainFile?: string;
  error?: string;
};

function normalizeString(value: unknown): string {
  return typeof value === 'string' ? value.trim() : '';
}

export default function LatexEditingPanel({
  selectedProject,
  preferredTexPath = '',
}: LatexEditingPanelProps) {
  const sourceProjectRoot = useMemo(
    () => normalizeString(selectedProject.path || selectedProject.fullPath),
    [selectedProject.path, selectedProject.fullPath],
  );
  const normalizedPreferredTexPath = useMemo(
    () => normalizeString(preferredTexPath),
    [preferredTexPath],
  );

  const [isPreparing, setIsPreparing] = useState(true);
  const [error, setError] = useState('');
  const [projectId, setProjectId] = useState('');
  const [openFile, setOpenFile] = useState('');
  const [needsTemplateBootstrap, setNeedsTemplateBootstrap] = useState(false);
  const [templates, setTemplates] = useState<LatexLabTemplate[]>([]);
  const [selectedTemplateId, setSelectedTemplateId] = useState('');
  const [isApplyingTemplate, setIsApplyingTemplate] = useState(false);

  const loadTemplates = useCallback(async () => {
    const response = await api.latexLab.listTemplates();
    if (!response.ok) {
      throw new Error(await response.text());
    }
    const data = (await response.json()) as TemplateListResponse;
    const nextTemplates = Array.isArray(data.templates) ? data.templates : [];
    setTemplates(nextTemplates);
    setSelectedTemplateId((prev) => prev || nextTemplates[0]?.id || '');
    return nextTemplates;
  }, []);

  const initializeWorkspace = useCallback(async () => {
    if (!sourceProjectRoot) {
      setIsPreparing(false);
      setNeedsTemplateBootstrap(false);
      setProjectId('');
      setOpenFile('');
      setError('This project does not have a valid filesystem path.');
      return;
    }

    setIsPreparing(true);
    setError('');
    setNeedsTemplateBootstrap(false);
    setTemplates([]);
    setSelectedTemplateId('');

    try {
      const response = await api.latexLab.openFromVibeLab({
        sourceProjectRoot,
        sourceTexPath: normalizedPreferredTexPath || undefined,
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }

      const data = (await response.json()) as OpenFromVibeLabResponse;
      if (!data?.projectId) {
        throw new Error(data?.error || 'Unable to initialize LatexLab workspace.');
      }

      setProjectId(data.projectId);
      setOpenFile(normalizeString(data.openFile));

      const shouldBootstrap = Boolean(data.needsTemplateBootstrap);
      setNeedsTemplateBootstrap(shouldBootstrap);
      if (shouldBootstrap) {
        await loadTemplates();
      }
    } catch (err) {
      setProjectId('');
      setOpenFile('');
      setNeedsTemplateBootstrap(false);
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsPreparing(false);
    }
  }, [sourceProjectRoot, normalizedPreferredTexPath, loadTemplates]);

  useEffect(() => {
    void initializeWorkspace();
  }, [initializeWorkspace]);

  const handleApplyTemplate = useCallback(async () => {
    if (!projectId || !selectedTemplateId || isApplyingTemplate) {
      return;
    }

    setIsApplyingTemplate(true);
    setError('');

    try {
      const response = await api.latexLab.applyTemplate({
        projectId,
        template: selectedTemplateId,
      });
      if (!response.ok) {
        throw new Error(await response.text());
      }

      const data = (await response.json()) as ApplyTemplateResponse;
      if (!data?.ok) {
        throw new Error(data?.error || 'Unable to apply template.');
      }

      setOpenFile(normalizeString(data.mainFile) || 'main.tex');
      setNeedsTemplateBootstrap(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setIsApplyingTemplate(false);
    }
  }, [projectId, selectedTemplateId, isApplyingTemplate]);

  if (isPreparing) {
    return <LatexLoadingFallback message="Preparing LaTeX workspace..." />;
  }

  if (needsTemplateBootstrap) {
    return (
      <div className="h-full overflow-auto p-4 sm:p-6">
        <div className="mx-auto max-w-2xl space-y-4">
          <div>
            <h3 className="text-lg font-semibold text-foreground">Create a LaTeX workspace</h3>
            <p className="text-sm text-muted-foreground mt-1">
              No `.tex` file was detected in this project. Select a template to initialize the editor.
            </p>
          </div>

          {error && (
            <div className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-600">
              {error}
            </div>
          )}

          <div className="rounded-lg border border-border bg-card p-4 space-y-3">
            <label className="block text-sm font-medium text-foreground" htmlFor="latex-template-select">
              Template
            </label>
            <select
              id="latex-template-select"
              className="w-full rounded-md border border-border bg-background px-3 py-2 text-sm"
              value={selectedTemplateId}
              onChange={(event) => setSelectedTemplateId(event.target.value)}
            >
              {templates.map((template) => (
                <option key={template.id} value={template.id}>
                  {template.label || template.id}
                </option>
              ))}
            </select>
            {templates.length === 0 && (
              <p className="text-sm text-muted-foreground">
                No templates are currently available from LatexLab.
              </p>
            )}
            <div className="flex items-center gap-2 pt-1">
              <Button
                onClick={handleApplyTemplate}
                disabled={isApplyingTemplate || !selectedTemplateId}
              >
                {isApplyingTemplate ? 'Creating workspace...' : 'Create workspace'}
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  void initializeWorkspace();
                }}
                disabled={isApplyingTemplate}
              >
                Retry detection
              </Button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (!projectId) {
    return (
      <div className="h-full w-full flex items-center justify-center p-6">
        <div className="max-w-lg rounded-md border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-600 space-y-3">
          <p>{error || 'Unable to load LaTeX workspace.'}</p>
          <Button
            variant="outline"
            onClick={() => {
              void initializeWorkspace();
            }}
          >
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full w-full overflow-hidden">
      <Suspense fallback={<LatexLoadingFallback message="Downloading LatexLab editor..." />}>
        <LazyLatexLabEmbeddedWorkspace projectId={projectId} openFile={openFile} />
      </Suspense>
    </div>
  );
}
