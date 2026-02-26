import { promises as fs } from 'fs';
import path from 'path';
import { DATA_DIR } from '../config/constants.js';

export function getProjectDataRoot(id) {
  return path.join(DATA_DIR, id);
}

export function getProjectMetaPath(id) {
  return path.join(getProjectDataRoot(id), 'project.json');
}

export function isLinkedProject(meta) {
  return typeof meta?.sourceProjectRoot === 'string' && meta.sourceProjectRoot.trim().length > 0;
}

export async function getProjectMeta(id) {
  const metaPath = getProjectMetaPath(id);
  await fs.access(metaPath);
  const content = await fs.readFile(metaPath, 'utf8');
  return JSON.parse(content);
}

export async function getProjectRoot(id) {
  const meta = await getProjectMeta(id);
  if (isLinkedProject(meta)) {
    const resolvedSourceRoot = path.resolve(meta.sourceProjectRoot);
    await fs.access(resolvedSourceRoot);
    return resolvedSourceRoot;
  }
  return getProjectDataRoot(id);
}
