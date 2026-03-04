import { useEffect, useMemo, useState } from 'react';
import { Compass, Shuffle, Sparkles } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  GUIDED_PROMPT_SCENARIOS,
  type GuidedPromptScenario,
} from '../../constants/guidedPromptScenarios';
import { api } from '../../../../utils/api';

interface GuidedPromptStarterProps {
  projectName: string;
  setInput: React.Dispatch<React.SetStateAction<string>>;
  textareaRef: React.RefObject<HTMLTextAreaElement>;
}

interface SkillTreeNode {
  name: string;
  type: 'directory' | 'file';
  children?: SkillTreeNode[];
}

function shuffleScenarios() {
  const list = [...GUIDED_PROMPT_SCENARIOS];
  for (let i = list.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [list[i], list[j]] = [list[j], list[i]];
  }
  return list.slice(0, 4);
}

function getStorageKey(projectName: string) {
  return `guided_starter_examples_${projectName}`;
}

function buildTemplate(
  t: (key: string, options?: Record<string, unknown>) => string,
  scenario: GuidedPromptScenario,
  skills: string[],
) {
  return [
    t('guidedStarter.template.intro', {
      scenario: t(scenario.titleKey),
      skills: skills.join(', '),
    }),
    '',
  ].join('\n');
}

function resolveInitialExamples(projectName: string) {
  if (typeof window === 'undefined') {
    return shuffleScenarios();
  }

  try {
    const saved = sessionStorage.getItem(getStorageKey(projectName));
    if (!saved) {
      const next = shuffleScenarios();
      sessionStorage.setItem(getStorageKey(projectName), JSON.stringify(next.map((item) => item.id)));
      return next;
    }
    const ids = JSON.parse(saved) as string[];
    const savedItems = ids
      .map((id) => GUIDED_PROMPT_SCENARIOS.find((item) => item.id === id))
      .filter((item): item is GuidedPromptScenario => Boolean(item))
      .slice(0, 4);
    if (savedItems.length > 0) {
      return savedItems;
    }
  } catch {
    // Fall through to random generation.
  }

  const next = shuffleScenarios();
  if (typeof window !== 'undefined') {
    sessionStorage.setItem(getStorageKey(projectName), JSON.stringify(next.map((item) => item.id)));
  }
  return next;
}

export default function GuidedPromptStarter({
  projectName,
  setInput,
  textareaRef,
}: GuidedPromptStarterProps) {
  const { t } = useTranslation('chat');
  const [examples, setExamples] = useState(() => resolveInitialExamples(projectName));
  const [selectedScenarioId, setSelectedScenarioId] = useState<string | null>(null);
  const [availableSkills, setAvailableSkills] = useState<Set<string> | null>(null);
  const [isLoadingSkills, setIsLoadingSkills] = useState(false);

  useEffect(() => {
    let cancelled = false;

    const normalize = (value: string) => value.trim().toLowerCase();
    const discovered = new Set<string>();

    const collect = (nodes: SkillTreeNode[]) => {
      for (const node of nodes) {
        if (node.type !== 'directory') {
          continue;
        }
        const hasSkillMd = (node.children || []).some(
          (child) => child.type === 'file' && child.name === 'SKILL.md',
        );
        if (hasSkillMd) {
          discovered.add(normalize(node.name));
        }
        if (Array.isArray(node.children) && node.children.length > 0) {
          collect(node.children);
        }
      }
    };

    const fetchSkills = async () => {
      setIsLoadingSkills(true);
      try {
        const response = await api.getGlobalSkills();
        if (!response.ok) {
          return;
        }
        const payload = (await response.json()) as SkillTreeNode[];
        collect(payload);
        if (!cancelled && discovered.size > 0) {
          setAvailableSkills(discovered);
        }
      } catch {
        // Keep static list as fallback.
      } finally {
        if (!cancelled) {
          setIsLoadingSkills(false);
        }
      }
    };

    fetchSkills();
    return () => {
      cancelled = true;
    };
  }, []);

  const selectedScenario = useMemo(
    () => examples.find((item) => item.id === selectedScenarioId) ?? null,
    [examples, selectedScenarioId],
  );

  const availableScenarioSkills = useMemo(() => {
    if (!selectedScenario) {
      return [];
    }
    if (!availableSkills) {
      return selectedScenario.skills;
    }
    const matched = selectedScenario.skills.filter((skill) => availableSkills.has(skill.toLowerCase()));
    return matched.length > 0 ? matched : selectedScenario.skills;
  }, [availableSkills, selectedScenario]);

  const injectTemplate = (scenario: GuidedPromptScenario, skills: string[]) => {
    const nextValue = buildTemplate(t, scenario, skills);
    setInput(nextValue);
    setTimeout(() => {
      const el = textareaRef.current;
      if (!el) return;
      el.focus();
      const cursor = nextValue.length;
      el.setSelectionRange(cursor, cursor);
    }, 100);
  };

  const handleRefreshExamples = () => {
    const next = shuffleScenarios();
    setExamples(next);
    setSelectedScenarioId(null);
    if (typeof window !== 'undefined') {
      sessionStorage.setItem(getStorageKey(projectName), JSON.stringify(next.map((item) => item.id)));
    }
  };

  return (
    <div className="mt-6 rounded-xl border border-cyan-300/50 dark:border-cyan-700/50 bg-gradient-to-br from-cyan-50/80 via-sky-50/60 to-emerald-50/40 dark:from-cyan-950/30 dark:via-sky-950/20 dark:to-emerald-950/10 p-4 sm:p-5 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5 min-w-0">
          <div className="mt-0.5 flex-shrink-0 w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-500 to-emerald-500 flex items-center justify-center">
            <Compass className="w-4 h-4 text-white" />
          </div>
          <div>
            <p className="text-sm font-semibold text-foreground">{t('guidedStarter.title')}</p>
            <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
              {t('guidedStarter.description')}
            </p>
          </div>
        </div>
        <button
          type="button"
          onClick={handleRefreshExamples}
          className="inline-flex items-center gap-1 rounded-md border border-cyan-300/50 dark:border-cyan-700/50 bg-white/70 dark:bg-white/5 px-2.5 py-1 text-[11px] text-muted-foreground hover:text-foreground hover:bg-white/90 dark:hover:bg-white/10 transition-colors"
        >
          <Shuffle className="h-3.5 w-3.5" />
          {t('guidedStarter.refresh')}
        </button>
      </div>

      <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-2.5">
        {examples.map((scenario) => {
          const isActive = selectedScenarioId === scenario.id;
          return (
            <button
              key={scenario.id}
              type="button"
              onClick={() => setSelectedScenarioId(scenario.id)}
              className={`rounded-xl border p-3 text-left transition-colors ${
                isActive
                  ? 'border-cyan-400/60 bg-cyan-500/10 ring-1 ring-cyan-400/20'
                  : 'border-cyan-200/60 dark:border-cyan-900/40 bg-white/70 dark:bg-white/5 hover:bg-white/90 dark:hover:bg-white/10'
              }`}
            >
              <p className="text-sm font-medium text-foreground">
                <span className="mr-1.5">{scenario.icon}</span>
                {t(scenario.titleKey)}
              </p>
              <p className="mt-1 text-xs text-muted-foreground leading-relaxed">
                {t(scenario.descriptionKey)}
              </p>
            </button>
          );
        })}
      </div>

      {selectedScenario && (
        <div className="mt-3 rounded-xl border border-cyan-200/60 dark:border-cyan-900/40 bg-white/75 dark:bg-white/5 p-3">
          <p className="text-xs font-medium text-muted-foreground mb-2">
            {t('guidedStarter.recommendedSkills')}
          </p>
          {isLoadingSkills && (
            <p className="mb-2 text-[11px] text-muted-foreground">
              {t('guidedStarter.loadingSkills')}
            </p>
          )}
          <div className="flex flex-wrap gap-2">
            {availableScenarioSkills.map((skill) => (
              <button
                key={skill}
                type="button"
                onClick={() => injectTemplate(selectedScenario, [skill])}
                className="rounded-full border border-cyan-200/70 dark:border-cyan-800/50 bg-white/90 dark:bg-white/5 px-2.5 py-1 text-xs font-medium text-foreground hover:bg-cyan-50 dark:hover:bg-cyan-900/20 transition-colors"
              >
                {skill}
              </button>
            ))}
            <button
              type="button"
              onClick={() => injectTemplate(selectedScenario, availableScenarioSkills)}
              disabled={availableScenarioSkills.length === 0}
              className="inline-flex items-center gap-1 rounded-full border border-cyan-400/50 px-2.5 py-1 text-xs font-medium text-white bg-gradient-to-r from-cyan-500 via-sky-500 to-emerald-500 hover:from-cyan-400 hover:via-sky-400 hover:to-emerald-400 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Sparkles className="w-3 h-3" />
              {t('guidedStarter.useAllSkills')}
            </button>
          </div>
          {!isLoadingSkills && availableSkills && selectedScenario.skills.length > 0 && selectedScenario.skills.every((skill) => !availableSkills.has(skill.toLowerCase())) && (
            <p className="mt-2 text-[11px] text-muted-foreground">
              {t('guidedStarter.noAvailableSkillsFallback')}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
