import { createInstance } from 'i18next';
import { initReactI18next } from 'react-i18next';
import zhCN from '../../../apps/latexlab/apps/frontend/src/i18n/locales/zh-CN.json';
import enUS from '../../../apps/latexlab/apps/frontend/src/i18n/locales/en-US.json';

const STORAGE_KEY = 'latexlab-lang';
const DEFAULT_LANG = 'zh-CN';

function getInitialLang() {
  if (typeof window === 'undefined') return DEFAULT_LANG;
  const stored = window.localStorage.getItem(STORAGE_KEY);
  return stored === 'en-US' ? 'en-US' : DEFAULT_LANG;
}

const latexLabI18n = createInstance();

void latexLabI18n
  .use(initReactI18next)
  .init({
    resources: {
      'zh-CN': { translation: zhCN },
      'en-US': { translation: enUS },
    },
    lng: getInitialLang(),
    fallbackLng: DEFAULT_LANG,
    interpolation: { escapeValue: false },
    keySeparator: false,
  });

latexLabI18n.on('languageChanged', (lng) => {
  if (typeof window === 'undefined') return;
  if (lng === 'zh-CN' || lng === 'en-US') {
    window.localStorage.setItem(STORAGE_KEY, lng);
  }
});

export default latexLabI18n;
