import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';
import { useTranslation } from 'react-i18next';

interface SkillShortcutsPanelProps {
  setInput: React.Dispatch<React.SetStateAction<string>>;
  textareaRef: React.RefObject<HTMLTextAreaElement>;
}

interface SkillCategory {
  key: string;
  icon: string;
  skills: string[];
}

const CATEGORIES: SkillCategory[] = [
  { key: 'deepResearch', icon: '🔍', skills: ['inno-deep-research', 'academic-researcher', 'biorxiv-database', 'dataset-discovery', 'inno-code-survey'] },
  { key: 'ideation', icon: '💡', skills: ['inno-idea-generation', 'inno-idea-eval', 'brainstorming-research-ideas', 'creative-thinking-for-research'] },
  { key: 'experiment', icon: '🧪', skills: ['inno-experiment-dev', 'inno-experiment-analysis', 'bioinformatics-init-analysis', 'inno-prepare-resources'] },
  { key: 'paperWriting', icon: '✏️', skills: ['inno-paper-writing', 'scientific-writing', 'ml-paper-writing', 'inno-figure-gen', 'inno-humanizer'] },
  { key: 'paperReview', icon: '📋', skills: ['inno-paper-reviewer', 'inno-reference-audit', 'inno-rclone-to-overleaf'] },
  { key: 'grantWriting', icon: '📝', skills: ['research-grants'] },
];

export default function SkillShortcutsPanel({
  setInput,
  textareaRef,
}: SkillShortcutsPanelProps) {
  const { t } = useTranslation('chat');
  const [expandedCategory, setExpandedCategory] = useState<string | null>(null);

  const inject = (prompt: string) => {
    setInput(prompt);
    setTimeout(() => textareaRef.current?.focus(), 100);
  };

  const handleSkillClick = (skill: string) => {
    inject(t('skillShortcuts.promptSingle', { skill }));
  };

  const handleUseAll = (category: SkillCategory) => {
    inject(t('skillShortcuts.promptMulti', { skills: category.skills.join(', ') }));
  };

  return (
    <div className="w-full max-w-2xl mx-auto mt-4 mb-2">
      <div className="rounded-xl border border-border/50 bg-card/60 p-4">
        <h3 className="text-base font-semibold text-foreground mb-3">
          {t('skillShortcuts.title')}
        </h3>

        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
          {CATEGORIES.map((cat) => {
            const isExpanded = expandedCategory === cat.key;
            return (
              <button
                key={cat.key}
                onClick={() => setExpandedCategory(isExpanded ? null : cat.key)}
                className={`
                  flex items-center gap-2.5 px-3.5 py-2.5 rounded-xl border text-left transition-all duration-150
                  ${isExpanded
                    ? 'border-primary/50 bg-primary/5 ring-1 ring-primary/10'
                    : 'border-border/50 bg-card/60 hover:bg-card hover:border-border/80'
                  }
                `}
              >
                <span className="text-lg leading-none flex-shrink-0">{cat.icon}</span>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-foreground leading-snug">
                    {t(`skillShortcuts.categories.${cat.key}`)}
                  </p>
                  <p className="text-xs text-muted-foreground leading-snug mt-0.5">
                    {cat.skills.length} skills
                  </p>
                </div>
                <ChevronDown className={`w-3.5 h-3.5 text-muted-foreground flex-shrink-0 transition-transform duration-150 ${isExpanded ? 'rotate-180' : ''}`} />
              </button>
            );
          })}
        </div>

        {expandedCategory && (() => {
          const cat = CATEGORIES.find((c) => c.key === expandedCategory);
          if (!cat) return null;
          return (
            <div className="mt-3 p-3 rounded-xl border border-border/40 bg-muted/30">
              <div className="flex items-center justify-between mb-2.5">
                <span className="text-sm font-medium text-foreground">
                  {cat.icon} {t(`skillShortcuts.categories.${cat.key}`)}
                </span>
                <button
                  onClick={() => handleUseAll(cat)}
                  className="text-xs font-medium text-primary hover:text-primary/80 transition-colors px-2.5 py-1 rounded-lg hover:bg-primary/5"
                >
                  {t('skillShortcuts.useAll')}
                </button>
              </div>
              <div className="flex flex-wrap gap-2">
                {cat.skills.map((skill) => (
                  <button
                    key={skill}
                    onClick={() => handleSkillClick(skill)}
                    className="px-3 py-1.5 text-xs font-medium rounded-full border border-border/50 bg-background hover:bg-muted hover:border-border transition-colors text-foreground"
                  >
                    {skill}
                  </button>
                ))}
              </div>
            </div>
          );
        })()}
      </div>
    </div>
  );
}
