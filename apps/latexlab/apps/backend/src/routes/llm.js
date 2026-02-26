import { callOpenAICompatible } from '../services/llmService.js';
import { getProjectRoot } from '../services/projectService.js';

export function registerLLMRoutes(fastify) {
  fastify.post('/api/llm', async (req) => {
    const { messages, model, llmConfig, projectId } = req.body || {};
    let cwd = '';
    if (projectId) {
      try {
        cwd = await getProjectRoot(projectId);
      } catch {
        cwd = '';
      }
    }
    const result = await callOpenAICompatible({
      messages,
      model: llmConfig?.model || model,
      provider: llmConfig?.provider,
      endpoint: llmConfig?.endpoint,
      apiKey: llmConfig?.apiKey,
      cwd
    });
    return result;
  });
}
