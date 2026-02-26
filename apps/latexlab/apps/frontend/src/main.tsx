import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { I18nextProvider } from 'react-i18next';
import App from './app/App';
import './i18n';
import i18n from './i18n';
import './app/App.css';

const routerBase = (import.meta.env.BASE_URL || '/').replace(/\/$/, '');

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <div className="latexlab-theme">
      <I18nextProvider i18n={i18n}>
        <BrowserRouter basename={routerBase || undefined}>
          <App />
        </BrowserRouter>
      </I18nextProvider>
    </div>
  </React.StrictMode>
);
