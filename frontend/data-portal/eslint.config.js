// @ts-check
import { default as angular, default as pkg } from '@angular-eslint/eslint-plugin';
import angularTemplate from '@angular-eslint/eslint-plugin-template';
import { default as angularTemplateParser } from '@angular-eslint/template-parser';
import markdown from '@eslint/markdown';
import angularEslint from 'angular-eslint';
import boundaries from 'eslint-plugin-boundaries';
import header from 'eslint-plugin-header';
import jsdoc from 'eslint-plugin-jsdoc';
import prettier from 'eslint-plugin-prettier';
import tseslint from 'typescript-eslint';
const { configs: angularConfigs } = pkg;

header.rules.header.meta.schema = false;

// Define the configuration
export default [
  // Configuration for TypeScript files
  {
    files: ['**/*.ts'],
    languageOptions: {
      parser: tseslint.parser,
      parserOptions: {
        ecmaVersion: 2020,
        sourceType: 'module',
        project: './tsconfig.spec.json',
      },
    },
    processor: angularEslint.processInlineTemplates,
    plugins: {
      '@angular-eslint': angular,
      tseslint,
      jsdoc,
      prettier,
      boundaries,
      header,
    },
    rules: {
      ...tseslint.configs.recommended.rules,
      ...angularConfigs.recommended.rules,
      ...jsdoc.configs['recommended-typescript'].rules,
      'prettier/prettier': 'warn',
      '@angular-eslint/directive-selector': [
        'error',
        { type: 'attribute', prefix: 'app', style: 'camelCase' },
      ],
      '@angular-eslint/component-selector': [
        'error',
        { type: 'element', prefix: 'app', style: 'kebab-case' },
      ],
      'header/header': [
        2,
        'block',
        [
          '*',
          { pattern: ' * .+', template: ' * Short module description' },
          ' * @copyright The GHGA Authors',
          ' * @license Apache-2.0',
          ' ',
        ],
        2,
        { lineEndings: 'linux' },
      ],
      'jsdoc/require-jsdoc': [
        'warn',
        {
          exemptEmptyConstructors: true,
          require: {
            FunctionDeclaration: true,
            MethodDefinition: true,
            ClassDeclaration: true,
            ArrowFunctionExpression: false,
            FunctionExpression: true,
          },
        },
      ],
      'jsdoc/require-description': [
        'warn',
        {
          contexts: ['FunctionDeclaration', 'MethodDefinition', 'ClassDeclaration'],
        },
      ],
      ...boundaries.configs.strict.rules,
      'boundaries/dependencies': [
        2,
        {
          // disallow importing any element by default
          default: 'disallow',
          // the default error message
          message:
            '{{from.captured.context}}/{{from.type}} is not allowed to import from {{to.captured.context}}/{{to.type}}',
          // all rules will be checked in order and matching rules alter the result
          rules: [
            // generally allow only importing from same context
            {
              from: { type: '*' },
              allow: {
                to: { type: '*', captured: { context: '{{from.captured.context}}' } },
              },
            },
            {
              from: { type: '*' },
              disallow: {
                to: { type: '*', captured: { context: '!{{from.captured.context}}' } },
              },
              message:
                '{{from.captured.context}} is not allowed to import from {{to.captured.context}}',
            },
            {
              from: { type: '*' },
              allow: { to: { type: '*', captured: { context: 'shared' } } },
            },
            // overarching portal context may import other feature components
            {
              from: { type: 'features', captured: { context: 'portal' } },
              allow: {
                to: {
                  type: 'features',
                  captured: {
                    context: ['metadata', 'ivas', 'access-requests', 'auth'],
                  },
                },
              },
            },
            // access requests context may import from verification addresses context
            {
              from: { type: 'features', captured: { context: 'access-requests' } },
              allow: {
                to: [
                  { type: 'service', captured: { context: 'ivas' } },
                  { type: 'model', captured: { context: 'ivas' } },
                  { type: 'pipe', captured: { context: 'ivas' } },
                ],
              },
            },
            {
              from: { type: 'model', captured: { context: 'access-requests' } },
              allow: {
                to: [{ type: 'model', captured: { context: 'ivas' } }],
              },
            },
            // upload context may import from verification addresses and metadata context
            {
              from: { type: 'features', captured: { context: 'upload' } },
              allow: {
                to: [
                  { type: 'service', captured: { context: 'ivas' } },
                  { type: 'model', captured: { context: 'ivas' } },
                  { type: 'pipe', captured: { context: 'ivas' } },
                  { type: 'service', captured: { context: 'metadata' } },
                  { type: 'model', captured: { context: 'metadata' } },
                ],
              },
            },
            // work-package context may import from some other contexts
            {
              from: { type: 'features', captured: { context: 'work-packages' } },
              allow: {
                to: [
                  { type: 'service', captured: { context: 'ivas' } },
                  { type: 'model', captured: { context: 'ivas' } },
                  { type: 'pipe', captured: { context: 'ivas' } },
                  { type: 'model', captured: { context: 'access-requests' } },
                  { type: 'model', captured: { context: 'upload' } },
                ],
              },
            },
            // auth context may import from verification addresses and access request context
            {
              from: { type: 'features', captured: { context: 'auth' } },
              allow: {
                to: [
                  { type: 'service', captured: { context: 'ivas' } },
                  { type: 'model', captured: { context: 'ivas' } },
                  { type: 'pipe', captured: { context: 'ivas' } },
                  { type: 'features', captured: { context: 'ivas' } },
                  { type: 'service', captured: { context: 'access-requests' } },
                  { type: 'model', captured: { context: 'access-requests' } },
                  { type: 'pipe', captured: { context: 'access-requests' } },
                  { type: 'features', captured: { context: 'access-requests' } },
                ],
              },
            },
            // main may only import config, main app modules and mock setup (dev mode)
            {
              from: { type: 'main' },
              disallow: { to: { type: '*' } },
              message:
                'Main modules may only import config, main app modules and mock setup',
            },
            {
              from: { type: 'main' },
              allow: { to: { type: ['config', 'main-app', 'mock'] } },
            },
            // main app may only import features and shared modules
            {
              from: { type: 'main-app' },
              disallow: { to: { type: '*' } },
              message:
                'Main app component may only import portal features and shared code',
            },
            {
              from: { type: 'main-app' },
              allow: {
                to: [
                  { type: 'features', captured: { context: 'portal' } },
                  { type: '*', captured: { context: 'shared' } },
                ],
              },
            },
            // config may only import modules for routes
            {
              from: { type: 'config' },
              disallow: { to: { type: '*' } },
              message: 'Config modules can only import routes, utils and auth services',
            },
            {
              from: { type: 'config' },
              allow: {
                to: [
                  { type: 'routes' },
                  { type: 'service', captured: { context: 'auth' } },
                  { type: 'util', captured: { context: 'shared' } },
                ],
              },
            },
            // modules for routes may import feature components
            {
              from: { type: 'routes' },
              allow: { to: { type: 'features' } },
            },
            // modules for routes may not import ui components
            {
              from: { type: 'routes' },
              disallow: { to: { type: 'ui' } },
              message: 'Modules for routes cannot import ui components',
            },
            // tests are currently exempt from all rules
            {
              from: { type: ['spec', 'mock'] },
              allow: { to: { type: '*' } },
            },
            // disallow importing from higher levels
            {
              from: { type: 'ui' },
              disallow: { to: { type: 'features' } },
              message: 'UI components should not import feature components',
            },
            {
              from: { type: 'ui' },
              disallow: { to: { type: 'service' } },
              message: 'UI components should not import services',
            },
            {
              from: { type: ['service', 'pipe', 'model', 'util'] },
              disallow: { to: { type: ['features', 'ui'] } },
              message: 'Components should not be imported from other kinds of modules',
            },
            {
              from: { type: 'pipe' },
              disallow: { to: { type: 'service' } },
              message: 'Services should not be imported from pipes',
            },
            {
              from: { type: 'model' },
              disallow: { to: { type: ['service', 'pipe'] } },
              message: 'Services and pipes should not be imported from models',
            },
            {
              from: { type: 'util' },
              disallow: { to: { type: ['service', 'pipe'] } },
              message: 'Services and pipes should not be imported from utilities',
            },
            // Auth service may be imported in other contexts
            {
              from: { type: ['features', 'service', 'routes'] },
              allow: { to: { type: 'service', captured: { context: 'auth' } } },
            },
            // Auth models may be imported in other contexts
            {
              from: { type: ['features', 'service', 'model', 'mock'] },
              allow: { to: { type: 'model', captured: { context: 'auth' } } },
            },

            // Mock module may only import models
            {
              from: { type: 'mock' },
              disallow: { to: { type: '!model' } },
              message: 'Mock modules can only import models {{to.captured.context}}',
            },
          ],
        },
      ],
    },
    settings: {
      'boundaries/legacy-templates': false,
      'import/resolver': {
        typescript: {
          alwaysTryTypes: true,
        },
      },
      'boundaries/elements': [
        // The first matching pattern will be used as the element type.
        // The element types correspond to the layers of the architecture matrix.
        // The name of the vertical slice is captured as the context value.
        {
          type: 'main',
          mode: 'full',
          pattern: 'src/main.ts',
        },
        {
          type: 'config',
          mode: 'full',
          pattern: 'src/app/**/*.config.ts',
        },
        {
          type: 'main-app',
          mode: 'full',
          pattern: 'src/app/app.ts',
        },
        {
          type: 'routes',
          mode: 'full',
          pattern: 'src/app/**/*-routes.ts',
        },
        {
          type: 'features',
          pattern: 'src/app/*/features',
          mode: 'folder',
          capture: ['context'],
        },
        {
          type: 'spec',
          pattern: 'src/app/**/*.spec.ts|tests/**/*.ts',
          mode: 'full',
        },
        {
          type: 'ui',
          pattern: 'src/app/*/ui',
          mode: 'folder',
          capture: ['context'],
        },
        {
          type: 'service',
          pattern: 'src/app/*/services',
          mode: 'folder',
          capture: ['context'],
        },
        {
          type: 'pipe',
          pattern: 'src/app/*/pipes',
          mode: 'folder',
          capture: ['context'],
        },
        {
          type: 'model',
          pattern: 'src/app/*/models',
          mode: 'folder',
          capture: ['context'],
        },
        {
          type: 'util',
          pattern: 'src/app/*/utils',
          mode: 'folder',
          capture: ['context'],
        },
        {
          type: 'mock',
          mode: 'folder',
          pattern: 'src/mocks',
        },
        {
          type: 'tooling',
          mode: 'file',
          pattern: ['setup-test.ts', 'playwright.config.ts', 'vitest.config.ts'],
        },
      ],
    },
  },
  // Configuration for HTML template files
  {
    files: ['src/app/**/*.html'],
    languageOptions: {
      parser: angularTemplateParser,
    },
    plugins: {
      '@angular-eslint/template': angularTemplate,
    },
    rules: {
      ...angularTemplate.configs.recommended.rules,
      ...angularTemplate.configs.accessibility.rules,
      '@angular-eslint/template/no-positive-tabindex': 'error',
    },
  },
  // Configuration for Markdown files
  {
    files: ['**/*.md'],
    plugins: {
      markdown,
    },
    language: 'markdown/commonmark',
    rules: {
      'markdown/fenced-code-language': 'error',
      'markdown/heading-increment': 'error',
      'markdown/no-duplicate-headings': 'error',
      'markdown/no-empty-links': 'error',
      'markdown/no-html': 'error',
      'markdown/no-invalid-label-refs': 'error',
      'markdown/no-missing-label-refs': 'error',
    },
  },
];
