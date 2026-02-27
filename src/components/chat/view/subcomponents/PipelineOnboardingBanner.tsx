import React, { useEffect, useRef, useState } from 'react';
import { FlaskConical, Sparkles, X, FileText, ListChecks } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useTaskMaster } from '../../../../contexts/TaskMasterContext';
import { api } from '../../../../utils/api';

type PipelineState = 'loading' | 'no-brief' | 'no-tasks' | 'ready';

interface PipelineOnboardingBannerProps {
  setInput: React.Dispatch<React.SetStateAction<string>>;
  textareaRef: React.RefObject<HTMLTextAreaElement>;
}

interface TaskMasterProject {
  name: string;
  [key: string]: unknown;
}

const TEMPLATE_NO_BRIEF = `Please help me set up my research pipeline using the inno-pipeline-planner skill. I have a rough idea for my research — guide me step by step to define it.\n\n`;

const TEMPLATE_NO_TASKS = `I already have a research brief but no tasks yet. Please use the inno-pipeline-planner skill to read my brief and generate tasks.\n\n`;

export default function PipelineOnboardingBanner({
  setInput,
  textareaRef,
}: PipelineOnboardingBannerProps) {
  const { t } = useTranslation('chat');
  const { tasks: rawTasks, currentProject: rawCurrentProject, isLoadingTasks } = useTaskMaster();
  const tasks = rawTasks as unknown[];
  const currentProject = rawCurrentProject as TaskMasterProject | null;
  const [pipelineState, setPipelineState] = useState<PipelineState>('loading');
  const [dismissed, setDismissed] = useState(false);

  // Track whether we've seen isLoadingTasks transition from true -> false
  // at least once for the current project. This avoids a race where
  // setCurrentProject clears tasks to [] before refreshTasks sets
  // isLoadingTasks=true, creating a brief window of (tasks=[], loading=false).
  const hasCompletedLoadRef = useRef(false);
  const trackedProjectRef = useRef<string | null>(null);

  useEffect(() => {
    const projectName = currentProject?.name ?? null;

    // Reset tracking when project changes
    if (projectName !== trackedProjectRef.current) {
      trackedProjectRef.current = projectName;
      hasCompletedLoadRef.current = false;
      setPipelineState('loading');
    }

    if (isLoadingTasks) {
      // Loading started — next time it goes false we know it's a real result
      setPipelineState('loading');
      return;
    }

    // Mark that we've seen at least one completed load cycle
    if (projectName) {
      hasCompletedLoadRef.current = true;
    }

    if (tasks && tasks.length > 0) {
      setPipelineState('ready');
      return;
    }

    // Don't query detect until we've actually completed loading once
    if (!hasCompletedLoadRef.current || !projectName) {
      setPipelineState('loading');
      return;
    }

    let cancelled = false;

    (async () => {
      try {
        const response = await api.taskmaster.detect(projectName);
        if (cancelled) return;

        if (!response.ok) {
          setPipelineState('no-brief');
          return;
        }

        const data = await response.json();
        const taskCount = data?.taskmaster?.metadata?.taskCount ?? 0;
        const hasResearchBrief = data?.taskmaster?.hasResearchBrief === true;

        if (taskCount > 0) {
          setPipelineState('ready');
        } else if (hasResearchBrief) {
          setPipelineState('no-tasks');
        } else {
          setPipelineState('no-brief');
        }
      } catch {
        if (!cancelled) setPipelineState('no-brief');
      }
    })();

    return () => { cancelled = true; };
  }, [tasks, currentProject?.name, isLoadingTasks]);

  if (dismissed || pipelineState === 'loading' || pipelineState === 'ready') {
    return null;
  }

  const handleUseInChat = () => {
    const template = pipelineState === 'no-brief' ? TEMPLATE_NO_BRIEF : TEMPLATE_NO_TASKS;
    setInput(template);
    setTimeout(() => textareaRef.current?.focus(), 100);
  };

  const isNoBrief = pipelineState === 'no-brief';

  return (
    <div className="w-full max-w-2xl mt-4 mb-2">
      <div className="relative rounded-xl border border-cyan-300/50 dark:border-cyan-700/50 bg-gradient-to-br from-cyan-50/80 via-sky-50/60 to-emerald-50/40 dark:from-cyan-950/30 dark:via-sky-950/20 dark:to-emerald-950/10 p-4 shadow-sm">
        <button
          onClick={() => setDismissed(true)}
          className="absolute top-2.5 right-2.5 p-1 rounded-md text-muted-foreground/60 hover:text-muted-foreground hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
          aria-label="Dismiss"
        >
          <X className="w-3.5 h-3.5" />
        </button>

        <div className="flex items-start gap-3">
          <div className="mt-0.5 flex-shrink-0 w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-emerald-500 flex items-center justify-center">
            {isNoBrief ? (
              <FlaskConical className="w-4 h-4 text-white" />
            ) : (
              <ListChecks className="w-4 h-4 text-white" />
            )}
          </div>

          <div className="flex-1 min-w-0 space-y-2.5">
            <div>
              <h3 className="text-sm font-semibold text-foreground leading-tight">
                {t(isNoBrief
                  ? 'pipelineOnboarding.noBrief.title'
                  : 'pipelineOnboarding.noTasks.title')}
              </h3>
              <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                {t(isNoBrief
                  ? 'pipelineOnboarding.noBrief.description'
                  : 'pipelineOnboarding.noTasks.description')}
              </p>
            </div>

            {isNoBrief && (
              <div className="space-y-1.5">
                <p className="text-[11px] font-medium text-muted-foreground/80 uppercase tracking-wide">
                  {t('pipelineOnboarding.noBrief.stepsLabel')}
                </p>
                <ol className="list-decimal pl-4 space-y-0.5 text-xs text-muted-foreground leading-relaxed">
                  <li>{t('pipelineOnboarding.noBrief.step1')}</li>
                  <li>{t('pipelineOnboarding.noBrief.step2')}</li>
                  <li>{t('pipelineOnboarding.noBrief.step3')}</li>
                </ol>
              </div>
            )}

            {!isNoBrief && (
              <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <FileText className="w-3 h-3 flex-shrink-0" />
                <span>{t('pipelineOnboarding.noTasks.briefExists')}</span>
              </div>
            )}

            <button
              onClick={handleUseInChat}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white rounded-lg bg-gradient-to-r from-cyan-500 via-sky-500 to-emerald-500 hover:from-cyan-400 hover:via-sky-400 hover:to-emerald-400 transition-all shadow-sm"
            >
              <Sparkles className="w-3 h-3" />
              {t(isNoBrief
                ? 'pipelineOnboarding.noBrief.buttonLabel'
                : 'pipelineOnboarding.noTasks.buttonLabel')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
