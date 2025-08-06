// @ts-check
import { default as angular, default as pkg } from '@angular-eslint/eslint-plugin';
import angularTemplate from '@angular-eslint/eslint-plugin-template';
import { default as angularTemplateParser } from '@angular-eslint/template-parser';
import markdown from '@eslint/markdown';
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
        project: './tsconfig.json',
      },
    },
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
      'boundaries/element-types': [
        2,
        {
          // disallow importing any element by default
          default: 'disallow',
          // the default error message
          message:
            '${file.context}/${file.type} is not allowed to import from ${dependency.context}/${dependency.type}',
          // all rules will be checked in order and matching rules alter the result
          rules: [
            // generally allow only importing from same context
            {
              from: ['*'],
              allow: [['*', { context: '${from.context}' }]],
            },
            {
              from: ['*'],
              disallow: [['*', { context: '!${from.context}' }]],
              message:
                '${file.context} is not allowed to import from ${dependency.context}',
            },
            {
              from: ['*'],
              allow: [['*', { context: 'shared' }]],
            },
            // overarching portal context may import other feature components
            {
              from: [['features', { context: 'portal' }]],
              allow: [
                [
                  'features',
                  {
                    context: ['metadata', 'verification-addresses', 'access-requests'],
                  },
                ],
              ],
            },
            // access requests context may import from verification addresses context
            {
              from: [['features', { context: 'access-requests' }]],
              allow: [
                ['service', { context: 'verification-addresses' }],
                ['model', { context: 'verification-addresses' }],
                ['pipe', { context: 'verification-addresses' }],
              ],
            },
            // auth context may import from verification addresses context
            {
              from: [['features', { context: 'auth' }]],
              allow: [
                ['service', { context: 'verification-addresses' }],
                ['model', { context: 'verification-addresses' }],
                ['pipe', { context: 'verification-addresses' }],
                ['features', { context: 'verification-addresses' }],
              ],
            },
            // auth context may import from access request context
            {
              from: [['features', { context: 'auth' }]],
              allow: [
                ['service', { context: 'access-requests' }],
                ['model', { context: 'access-requests' }],
                ['pipe', { context: 'access-requests' }],
              ],
            },
            // main may only import config and main app modules
            {
              from: ['main'],
              disallow: ['*'],
              message: 'Main modules may only import config and main app',
            },
            {
              from: ['main'],
              allow: ['config', 'main-app'],
            },
            // main app may only import features and shared modules
            {
              from: ['main-app'],
              disallow: ['*'],
              message:
                'Main app component may only import portal features and shared code',
            },
            {
              from: ['main-app'],
              allow: [
                ['features', { context: 'portal' }],
                ['*', { context: 'shared' }],
              ],
            },
            // config may only import modules for routes
            {
              from: ['config'],
              disallow: ['*'],
              message: 'Config modules can only import routes, utils and auth services',
            },
            {
              from: ['config'],
              allow: [
                'routes',
                ['service', { context: 'auth' }],
                ['util', { context: 'shared' }],
              ],
            },
            // modules for routes may import feature components
            {
              from: ['routes'],
              allow: ['features'],
            },
            // modules for routes may not import ui components
            {
              from: ['routes'],
              disallow: ['ui'],
              message: 'Modules for routes cannot import ui components',
            },
            // tests are currently exempt from all rules
            {
              from: ['spec', 'mock'],
              allow: ['*'],
            },
            // disallow importing from higher levels
            {
              from: ['ui'],
              disallow: ['features'],
              message: 'UI components should not import feature components',
            },
            {
              from: ['ui'],
              disallow: ['service'],
              message: 'UI components should not import services',
            },
            {
              from: ['service', 'pipe', 'model', 'util'],
              disallow: ['features', 'ui'],
              message: 'Components should not be imported from other kinds of modules',
            },
            {
              from: ['pipe'],
              disallow: ['service'],
              message: 'Services should not be imported from pipes',
            },
            {
              from: ['model'],
              disallow: ['service', 'pipe'],
              message: 'Services and pipes should not be imported from models',
            },
            {
              from: ['util'],
              disallow: ['service', 'pipe'],
              message: 'Services and pipes should not be imported from utilities',
            },
            // Auth service may be imported in other contexts
            {
              from: ['features', 'service', 'routes'],
              allow: [['service', { context: 'auth' }]],
            },
            // Auth models may be imported in other contexts
            {
              from: ['features', 'service', 'model', 'mock'],
              allow: [['model', { context: 'auth' }]],
            },
            // Mock module may only import models
            {
              from: ['mock'],
              disallow: ['!model'],
              message: 'Mock modules can only import models  ${dependency.context}',
            },
          ],
        },
      ],
    },
    settings: {
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
          pattern: 'src/app/app.component.ts',
        },
        {
          type: 'routes',
          mode: 'full',
          pattern: 'src/app/**/*.routes.ts',
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
          pattern: [
            'jest.config.ts',
            'setup-jest.ts',
            'playwright.config.ts',
            'playwright.setup.ts',
          ],
        },
      ],
    },
  },
  // Configuration for HTML template files
  {
    files: ['**/*.component.html'],
    languageOptions: {
      parser: angularTemplateParser,
    },
    plugins: {
      '@angular-eslint/template': angularTemplate,
      prettier,
    },
    rules: {
      ...angularTemplate.configs.recommended.rules,
      ...angularTemplate.configs.accessibility.rules,
      'prettier/prettier': 'warn',
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
