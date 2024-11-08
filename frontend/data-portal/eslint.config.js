// @ts-check
import angular from '@angular-eslint/eslint-plugin';
import angularTemplate from '@angular-eslint/eslint-plugin-template';
import { default as angularTemplateParser } from "@angular-eslint/template-parser";
import typescriptPlugin, { configs as tsConfigs } from "@typescript-eslint/eslint-plugin";
import * as typescriptParser from "@typescript-eslint/parser";
import jsdoc from "eslint-plugin-jsdoc";
import prettier from "eslint-plugin-prettier";

import pkg from '@angular-eslint/eslint-plugin';
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
        { contexts: ["FunctionDeclaration", "MethodDefinition", "ClassDeclaration"] },
      ],
    },
  },
  {
    files: ["**/*.html"],
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
    }
  },
];
