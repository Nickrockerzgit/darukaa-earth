#!/usr/bin/env node
/**
 * Strictly parse every tracked JSON file.
 *
 * Prettier is not a substitute for this: its JSON parser is lenient and
 * happily accepts things `JSON.parse` rejects. An invalid escape sequence in
 * vercel.json once passed `prettier --check` and only surfaced as "Invalid
 * vercel.json file provided" in the Vercel dashboard, which is a slow and
 * confusing place to learn about a typo.
 */

import { execFileSync } from 'node:child_process';
import { existsSync, readFileSync } from 'node:fs';

const IGNORED = /(^|\/)(node_modules|dist|coverage|htmlcov)\//;

/**
 * Files that are JSON with Comments by convention, not strict JSON.
 * TypeScript and VS Code both document comments as supported in these.
 */
const JSONC = /(^|\/)(tsconfig[^/]*\.json|jsconfig\.json|\.vscode\/[^/]+\.json)$/;

function trackedJsonFiles() {
  const output = execFileSync('git', ['ls-files', '*.json'], { encoding: 'utf8' });
  return (
    output
      .split('\n')
      .map((line) => line.trim())
      .filter((line) => line && !IGNORED.test(line) && !JSONC.test(line))
      // A file can be tracked but already deleted in the working tree.
      .filter((file) => existsSync(file))
  );
}

const failures = [];
const files = trackedJsonFiles();

for (const file of files) {
  try {
    JSON.parse(readFileSync(file, 'utf8'));
  } catch (error) {
    failures.push({ file, message: error instanceof Error ? error.message : String(error) });
  }
}

if (failures.length > 0) {
  console.error(`\n${failures.length} JSON file(s) failed to parse:\n`);
  for (const { file, message } of failures) {
    console.error(`  ${file}`);
    console.error(`    ${message}\n`);
  }
  process.exit(1);
}

console.log(`All ${files.length} tracked JSON files parse cleanly.`);
