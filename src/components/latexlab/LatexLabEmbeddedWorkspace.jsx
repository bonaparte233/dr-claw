import React, { Suspense, lazy, useMemo } from 'react';
import { I18nextProvider } from 'react-i18next';
import latexLabI18n from './latexLabI18n';
import '../../../apps/latexlab/apps/frontend/src/app/App.css';
import LatexLoadingFallback from '../main-content/view/subcomponents/LatexLoadingFallback';

if (typeof window !== 'undefined') {
  window.__LATEXLAB_API_PREFIX__ = '/latexlab-api';
}

const LazyEditorPage = lazy(() => import('@latexlab/editor-page'));

export default function LatexLabEmbeddedWorkspace({ projectId, openFile }) {
  const normalizedProjectId = useMemo(() => String(projectId || '').trim(), [projectId]);
  const normalizedOpenFile = useMemo(() => String(openFile || '').trim(), [openFile]);

  return (
    <div className="latexlab-theme latexlab-embedded h-full">
      <I18nextProvider i18n={latexLabI18n}>
        <Suspense fallback={<LatexLoadingFallback message="Loading LatexLab workspace..." />}>
          <LazyEditorPage
            embeddedProjectId={normalizedProjectId}
            embeddedOpenFile={normalizedOpenFile}
            embeddedSourceTag="vibelab"
            embeddedMode
          />
        </Suspense>
      </I18nextProvider>
    </div>
  );
}
