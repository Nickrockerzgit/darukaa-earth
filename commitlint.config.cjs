/**
 * Conventional Commits enforcement.
 * Keeps the commit history readable and machine-parseable, which the
 * hackathon brief calls out explicitly ("logical commit history").
 */
module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
      [
        'feat',
        'fix',
        'docs',
        'style',
        'refactor',
        'perf',
        'test',
        'build',
        'ci',
        'chore',
        'revert',
      ],
    ],
    'scope-enum': [
      2,
      'always',
      [
        'auth',
        'projects',
        'sites',
        'analytics',
        'map',
        'charts',
        'ui',
        'api',
        'db',
        'ci',
        'deps',
        'docs',
        'config',
        'tests',
        'release',
      ],
    ],
    'scope-empty': [1, 'never'],
    // Forbid Title Case and SHOUTING, but allow proper nouns mid-subject:
    // "add PostGIS migrations" and "fix ORM drift" are correct English, and a
    // blanket lower-case rule would force them to be wrong.
    'subject-case': [2, 'never', ['start-case', 'pascal-case', 'upper-case']],
    'header-max-length': [2, 'always', 100],
  },
};
