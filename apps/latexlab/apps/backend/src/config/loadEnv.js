import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const candidateEnvFiles = [
  path.resolve(__dirname, '../../../../../../.env'),
  path.resolve(__dirname, '../../../../../../.env.local'),
  path.resolve(__dirname, '../../../../.env'),
  path.resolve(__dirname, '../../../../.env.local')
];

function stripWrappingQuotes(value) {
  if ((value.startsWith('"') && value.endsWith('"')) || (value.startsWith("'") && value.endsWith("'"))) {
    return value.slice(1, -1);
  }
  return value;
}

for (const envPath of candidateEnvFiles) {
  if (!fs.existsSync(envPath)) continue;
  const contents = fs.readFileSync(envPath, 'utf8');
  for (const rawLine of contents.split('\n')) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) continue;
    const equalsIndex = line.indexOf('=');
    if (equalsIndex <= 0) continue;
    const key = line.slice(0, equalsIndex).trim();
    if (!key || process.env[key] !== undefined) continue;
    const value = line.slice(equalsIndex + 1).trim();
    process.env[key] = stripWrappingQuotes(value);
  }
}
