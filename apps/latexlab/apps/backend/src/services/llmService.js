import { CLAUDE_MODELS, CURSOR_MODELS, CODEX_MODELS } from '../../../../../../shared/modelConstants.js';
import { queryClaudeSDK } from '../../../../../../server/claude-sdk.js';
import { spawnCursor } from '../../../../../../server/cursor-cli.js';
import { queryCodex } from '../../../../../../server/openai-codex.js';

const VIBELAB_MODELS = {
  claude: CLAUDE_MODELS.DEFAULT,
  cursor: CURSOR_MODELS.DEFAULT,
  codex: CODEX_MODELS.DEFAULT
};

function resolveModel(model) {
  const raw = typeof model === 'string' ? model.trim() : '';
  if (!raw) return VIBELAB_MODELS.claude;
  const normalized = raw.toLowerCase();
  return VIBELAB_MODELS[normalized] || raw;
}

function resolveProvider({ provider, model }) {
  const normalizedProvider = typeof provider === 'string' ? provider.trim().toLowerCase() : '';
  if (Object.prototype.hasOwnProperty.call(VIBELAB_MODELS, normalizedProvider)) {
    return normalizedProvider;
  }
  const normalizedModel = typeof model === 'string' ? model.trim().toLowerCase() : '';
  if (Object.prototype.hasOwnProperty.call(VIBELAB_MODELS, normalizedModel)) {
    return normalizedModel;
  }
  return '';
}

function toPrompt(messages) {
  if (!Array.isArray(messages)) return '';
  return messages
    .map((message) => {
      if (!message || typeof message !== 'object') return '';
      const role = typeof message.role === 'string' ? message.role.toUpperCase() : 'USER';
      if (typeof message.content === 'string') {
        return `${role}: ${message.content}`;
      }
      if (Array.isArray(message.content)) {
        const merged = message.content
          .map((part) => {
            if (!part || typeof part !== 'object') return '';
            if (part.type === 'text' && typeof part.text === 'string') return part.text;
            return '';
          })
          .filter(Boolean)
          .join('\n');
        return `${role}: ${merged}`;
      }
      return '';
    })
    .filter(Boolean)
    .join('\n\n');
}

class ProviderResponseCollector {
  constructor() {
    this.buffer = '';
    this.cursorFallback = '';
  }

  append(text) {
    if (!text || typeof text !== 'string') return;
    const chunk = text.trim();
    if (!chunk) return;
    this.buffer = this.buffer ? `${this.buffer}\n${chunk}` : chunk;
  }

  send(payload) {
    if (!payload) return;
    if (typeof payload === 'string') {
      try { payload = JSON.parse(payload); } catch { return; }
    }
    if (typeof payload !== 'object') return;
    if (payload.type === 'claude-response') {
      const data = payload.data || {};
      if (data.type === 'content_block_delta' && data.delta?.text) {
        this.append(data.delta.text);
      } else if (data.type === 'assistant' && Array.isArray(data.content)) {
        data.content.forEach((part) => {
          if (part?.type === 'text' && typeof part.text === 'string') {
            this.append(part.text);
          }
        });
      } else if (typeof data.content === 'string') {
        this.append(data.content);
      }
    } else if (payload.type === 'cursor-result') {
      if (typeof payload.data?.result === 'string') {
        this.cursorFallback = payload.data.result.trim();
      }
    } else if (payload.type === 'codex-response') {
      const data = payload.data || {};
      if (data.type === 'item' && data.itemType === 'agent_message') {
        if (typeof data.message?.content === 'string') {
          this.append(data.message.content);
        }
      }
    }
  }

  end() {}

  setSessionId(id) {
    this.sessionId = id;
  }

  getContent() {
    return (this.buffer || this.cursorFallback || '').trim();
  }

  getSessionId() {
    return this.sessionId || null;
  }
}

async function callVibeLabProvider({ messages, provider, model, cwd, sessionId }) {
  const prompt = toPrompt(messages);
  const collector = new ProviderResponseCollector();
  const workingDir = cwd || process.cwd();
  try {
    if (provider === 'cursor') {
      await spawnCursor(prompt, {
        cwd: workingDir,
        projectPath: workingDir,
        sessionId: sessionId || null,
        model: model || CURSOR_MODELS.DEFAULT,
        skipPermissions: true
      }, collector);
    } else if (provider === 'codex') {
      await queryCodex(prompt, {
        cwd: workingDir,
        projectPath: workingDir,
        sessionId: sessionId || null,
        model: model || CODEX_MODELS.DEFAULT,
        permissionMode: 'default'
      }, collector);
    } else {
      await queryClaudeSDK(prompt, {
        cwd: workingDir,
        projectPath: workingDir,
        sessionId: sessionId || null,
        model: model || CLAUDE_MODELS.DEFAULT,
        permissionMode: 'default'
      }, collector);
    }
    return { ok: true, content: collector.getContent(), sessionId: collector.getSessionId() };
  } catch (error) {
    return { ok: false, error: error?.message || String(error) };
  }
}

export function normalizeChatEndpoint(endpoint) {
  if (!endpoint) return 'https://api.openai.com/v1/chat/completions';
  let url = endpoint.trim();
  if (!url) return 'https://api.openai.com/v1/chat/completions';
  url = url.replace(/\/+$/, '');
  if (/\/chat\/completions$/i.test(url)) return url;
  if (/\/v1$/i.test(url)) return `${url}/chat/completions`;
  if (/\/v1\//i.test(url)) return url;
  return `${url}/v1/chat/completions`;
}

export function normalizeBaseURL(endpoint) {
  if (!endpoint) return undefined;
  const trimmed = endpoint.replace(/\/+$/, '');
  return trimmed.replace(/\/chat\/completions$/i, '');
}

export function resolveLLMConfig(llmConfig) {
  const provider = resolveProvider({
    provider: llmConfig?.provider,
    model: llmConfig?.model || process.env.LATEXLAB_LLM_MODEL || ''
  });
  return {
    endpoint: (llmConfig?.endpoint || process.env.LATEXLAB_LLM_ENDPOINT || 'https://api.openai.com/v1/chat/completions').trim(),
    apiKey: (llmConfig?.apiKey || process.env.LATEXLAB_LLM_API_KEY || '').trim(),
    model: resolveModel(llmConfig?.model || process.env.LATEXLAB_LLM_MODEL || 'claude'),
    provider
  };
}

export async function callOpenAICompatible({ messages, model, endpoint, apiKey, provider, cwd, sessionId }) {
  const resolvedProvider = resolveProvider({ provider, model });
  if (resolvedProvider) {
    const resolvedModel = resolveModel(model || resolvedProvider);
    return callVibeLabProvider({
      messages,
      provider: resolvedProvider,
      model: resolvedModel,
      cwd,
      sessionId
    });
  }

  const finalEndpoint = normalizeChatEndpoint(endpoint || process.env.LATEXLAB_LLM_ENDPOINT);
  const finalApiKey = (apiKey || process.env.LATEXLAB_LLM_API_KEY || '').trim();
  const finalModel = resolveModel(model || process.env.LATEXLAB_LLM_MODEL || 'claude');

  if (!finalApiKey) {
    return { ok: false, error: 'LATEXLAB_LLM_API_KEY not set' };
  }

  const res = await fetch(finalEndpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${finalApiKey}`
    },
    body: JSON.stringify({
      model: finalModel,
      messages,
      temperature: 0.2
    })
  });

  const text = await res.text();
  if (!res.ok) {
    return { ok: false, error: text || `Request failed with ${res.status}` };
  }
  const contentType = res.headers.get('content-type') || '';
  if (!contentType.includes('application/json')) {
    return { ok: false, error: text || 'Non-JSON response from provider.' };
  }
  let data = null;
  try {
    data = JSON.parse(text);
  } catch {
    return { ok: false, error: 'Response JSON parse failed.' };
  }
  const content = data?.choices?.[0]?.message?.content || '';
  return { ok: true, content };
}
