// @ts-check
import angular from "@angular-eslint/eslint-plugin";
import angularTemplate from "@angular-eslint/eslint-plugin-template";
import { default as angularTemplateParser } from "@angular-eslint/template-parser";
import typescriptPlugin, {
  configs as tsConfigs,
} from "@typescript-eslint/eslint-plugin";
import * as typescriptParser from "@typescript-eslint/parser";
import jsdoc from "eslint-plugin-jsdoc";
import prettier from "eslint-plugin-prettier";
import boundaries from "eslint-plugin-boundaries";
import markdown from "@eslint/markdown";

import pkg from "@angular-eslint/eslint-plugin";
const { configs: angularConfigs } = pkg;

// Define the configuration
export default [
  // Configuration for TypeScript files
  {
    files: ["**/*.ts"],
    languageOptions: {
      parser: typescriptParser,
      parserOptions: {
        ecmaVersion: 2020,
        sourceType: "module",
        project: "./tsconfig.json",
      },
    },
    plugins: {
      "@angular-eslint": angular,
      "@typescript-eslint": typescriptPlugin,
      jsdoc,
      prettier,
      boundaries,
    },
    rules: {
      ...tsConfigs.recommended.rules,
      ...angularConfigs.recommended.rules,
      ...jsdoc.configs["recommended-typescript"].rules,
      "prettier/prettier": "warn",
      "@angular-eslint/directive-selector": [
        "error",
        { type: "attribute", prefix: "app", style: "camelCase" },
      ],
      "@angular-eslint/component-selector": [
        "error",
        { type: "element", prefix: "app", style: "kebab-case" },
      ],
      "jsdoc/require-jsdoc": [
        "warn",
        {
          require: {
            FunctionDeclaration: true,
            MethodDefinition: true,
            ClassDeclaration: true,
            ArrowFunctionExpression: true,
            FunctionExpression: true,
          },
        },
      ],
      "jsdoc/require-description": [
        "warn",
        {
          contexts: [
            "FunctionDeclaration",
            "MethodDefinition",
            "ClassDeclaration",
          ],
        },
      ],
      ...boundaries.configs.strict.rules,
      "boundaries/element-types": [
        2,
        {
          // disallow importing any element by default
          default: "disallow",
          // the default error message
          message:
            "${file.context}/${file.type} is not allowed to import from ${dependency.context}/${dependency.type}",
          // all rules will be checked in order and matching rules alter the result
          rules: [
            // generally allow only importing from same context
            {
              from: ["*"],
              allow: [["*", { context: "${from.context}" }]],
            },
            {
              from: ["*"],
              disallow: [["*", { context: "!${from.context}" }]],
              message:
                "${file.context} is not allowed to import from ${dependency.context}",
            },
            {
              from: ["*"],
              allow: [["*", { context: "shared" }]],
            },
            // overarching portal context may import other feature components
            {
              from: [["feature", { context: "portal" }]],
              allow: [
                [
                  "feature",
                  {
                    context: [
                      "metadata",
                      "verification-addresses",
                      "access-requests",
                    ],
                  },
                ],
              ],
            },
            // main may only import config and main app modules
            {
              from: ["main"],
              allow: ["config", "main-app"],
              message:
                "The main module should only import config and app component",
            },
            {
              from: ["main"],
              allow: ["config", "main-app"],
            },
            {
              from: ["main-app"],
              disallow: [["*", { context: "!shared" }]],
              message: "The main app component should only import shared code",
            },
            // config may only import modules for routes
            {
              from: ["config"],
              disallow: ["routes"],
              message: "Config modules can only import modules with routes",
            },
            {
              from: ["config"],
              allow: ["routes"],
            },
            // modules for routes may only import feature components
            {
              from: ["routes"],
              disallow: ["*"],
              message: "Modules for routes can only import feature components",
            },
            {
              from: ["routes"],
              allow: ["feature"],
            },
            // unit tests are currently exempt from all rules
            {
              from: ["spec"],
              allow: ["*"],
            },
            // disallow importing from higher levels
            {
              from: ["ui"],
              disallow: ["feature"],
              message: "UI components should not import feature components",
            },
            {
              from: ["ui"],
              disallow: ["service"],
              message: "UI components should not import services",
            },
            {
              from: ["service", "model", "util"],
              disallow: ["feature", "ui"],
              message:
                "Components should not be imported from other kinds of modules",
            },
            {
              from: ["model"],
              disallow: ["service"],
              message: "Services should not be imported from models",
            },
            {
              from: ["util"],
              disallow: ["service", "model"],
              message:
                "Services and models should not be imported from utilities",
            },
            // Auth service may be imported in other contexts
            {
              from: ["feature", "service"],
              allow: [["service", { context: "auth" }]],
            },
            // Auth models may be imported in other contexts
            {
              from: ["feature", "service", "models"],
              allow: [["model", { context: "auth" }]],
            },
          ],
        },
      ],
    },
    settings: {
      "import/resolver": {
        typescript: {
          alwaysTryTypes: true,
        },
      },
      "boundaries/elements": [
        // The first matching pattern will be used as the element type.
        // The element types correspond to the layers of the architecture matrix.
        // The name of the vertical slice is captured as the context value.
        {
          type: "main",
          mode: "full",
          pattern: "src/main.ts",
        },
        {
          type: "config",
          mode: "full",
          pattern: "src/app/**/*.config.ts",
        },
        {
          type: "main-app",
          mode: "full",
          pattern: "src/app/app.component.ts",
        },
        {
          type: "routes",
          mode: "full",
          pattern: "src/app/**/*.routes.ts",
        },
        {
          type: "feature",
          pattern: "src/app/*/features",
          mode: "folder",
          capture: ["context"],
        },
        {
          type: "spec",
          pattern: "src/app/**/*.spec.ts",
          mode: "full",
        },
        {
          type: "ui",
          pattern: "src/app/*/ui",
          mode: "folder",
          capture: ["context"],
        },
        {
          type: "service",
          pattern: "src/app/*/services",
          mode: "folder",
          capture: ["context"],
        },
        {
          type: "model",
          pattern: "src/app/*/models",
          mode: "folder",
          capture: ["context"],
        },
        {
          type: "util",
          pattern: "src/app/*/utils",
          mode: "folder",
          capture: ["context"],
        },
      ],
    },
  },
  // Configuration for HTML template files
  {
    files: ["**/*.component.html"],
    languageOptions: {
      parser: angularTemplateParser,
    },
    plugins: {
      "@angular-eslint/template": angularTemplate,
      prettier,
    },
    rules: {
      ...angularTemplate.configs.recommended.rules,
      ...angularTemplate.configs.accessibility.rules,
      "prettier/prettier": "warn",
    },
  },
  // Configuration for Markdown files
  {
    files: ["**/*.md"],
    plugins: {
      markdown
    },
    language: "markdown/commonmark",
    rules: {
      "markdown/fenced-code-language": "error",
      "markdown/heading-increment": "error",
      "markdown/no-duplicate-headings": "error",
      "markdown/no-empty-links": "error",
      "markdown/no-html": "error",
      "markdown/no-invalid-label-refs": "error",
      "markdown/no-missing-label-refs": "error",
    },
  },
];
