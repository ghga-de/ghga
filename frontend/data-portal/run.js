#!/usr/bin/env node

import { spawnSync } from "child_process";
import fs from "fs";
import yaml from "js-yaml";
import path from "path";
import { fileURLToPath } from "url";

const NAME = "data-portal";
const DEV_MODE = process.argv.slice(2).includes("--dev");
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

/**
 * Reads and merges configuration settings from default and specific YAML files.
 * Overrides settings with environment variables prefixed with the application name.
 *
 * @returns {Object} The merged configuration settings.
 * @throws {Error} If there is an error reading the configuration files.
 */
function readSettings() {
  // Read the default configuration file
  const defaultSettingsPath = path.join(__dirname, `${NAME}.default.yaml`);
  const defaultSettings = yaml.load(
    fs.readFileSync(defaultSettingsPath, "utf8"),
  );

  // Read the (optional) development or production specific configuration file
  const specificSettingsPath = DEV_MODE
    ? `.devcontainer/.${NAME}.yaml`
    : `.${NAME}.yaml`;

  let specificSettings = {};
  try {
    specificSettings = yaml.load(fs.readFileSync(specificSettingsPath, "utf8"));
  } catch (e) {
    if (e.code !== "ENOENT") throw e; // ignore non-existing file
  }

  // Merge the default and specific settings
  const settings = { ...defaultSettings, ...specificSettings };

  // Override settings with environment variables
  const prefix = NAME.replace("-", "_");
  for (const key in settings) {
    if (!settings.hasOwnProperty(key)) continue;
    const envVarName = `${prefix}_${key}`;
    const value = settings[key];
    let envVarValue = process.env[envVarName];
    if (envVarValue === undefined) continue;
    const isObject = typeof value === "object" && value !== null;
    if (isObject) {
      envVarValue = JSON.parse(envVarValue);
    } else {
      isBoolean = typeof value === "boolean";
      if (isBoolean) {
        envVarValue = envVarValue.toLowerCase() === "true";
      } else {
        isNumber = typeof value === "number";
        if (isNumber) {
          envVarValue = parseFloat(envVarValue);
        }
      }
    }

    settings[key] = envVarValue;
  }

  return settings;
}

/**
 * Get the subdirectory with the browser files.
 *
 * @param {string} distDir - The distribution directory.
 */
function getBrowserDir(distDir) {
  const browserDir = path.join(distDir, NAME, "browser");
  // Support for flattened distribution directory
  return fs.existsSync(browserDir) ? browserDir : distDir;
}

/**
 * Inject the settings into the index file in the appropriate output directory.
 *
 * @param {Object} settings - The configuration settings to write.
 * @throws {Error} If the output directory or the index file does not exist.
 */
function writeSettings(settings) {
  let outputDir = DEV_MODE ? "src" : getBrowserDir("dist");

  // Ensure the output directory exists
  if (!fs.existsSync(outputDir)) {
    throw new Error(`Output directory not found: ${outputDir}`);
  }

  // Ensure the index file exists
  const indexPath = path.join(outputDir, "index.html");
  if (!fs.existsSync(indexPath)) {
    throw new Error(`Index file not found: ${indexPath}`);
  }

  // Inject the configuration settings into the index file
  const configScript = `window.config = ${JSON.stringify(settings)}`;
  const indexFile = fs
    .readFileSync(indexPath, "utf8")
    .replace(/window\.config = {[^}]*}/, configScript);
  fs.writeFileSync(indexPath, indexFile, "utf8");
}

/**
 * Run the development server on the specified host and port.
 */
function runDevServer(host, port, logLevel) {
  console.log("Running the development server...");

  const params = ["start", "--", "--host", host, "--port", port];
  if (logLevel == "debug") {
    params.push("--verbose");
  }
  const result = spawnSync("npm", params, {
    stdio: "inherit",
  });

  if (result.error) {
    console.error(result.error.message);
    process.exit(1);
  }

  process.exit(result.status);
}

/**
 * Run the production server on the specified host and port.
 *
 * It is assumed that the application has already been built
 * and that the "serve" package is installed globally.
 */
function runProdServer(host, port, logLevel) {
  console.log("Running the production server...");

  const distDir = getBrowserDir(path.join(__dirname, "dist"));
  process.chdir(distDir);

  const params = [
    "-a",
    host,
    "-p",
    port,
    "-g",
    logLevel.toLowerCase(),
    "-d",
    ".",
    "--page-fallback",
    "./index.html",
  ];

  const result = spawnSync("static-web-server", params, {
    stdio: "inherit",
  });

  if (result.error) {
    console.error(result.error.message);
    process.exit(1);
  }

  process.exit(result.status);
}

/**
 * Main entry point.
 */
function main() {
  process.chdir(__dirname);

  const settings = readSettings();
  console.log("Runtime settings =", settings);

  const { host, port, log_level } = settings;
  const logLevel = log_level.toLowerCase();
  delete settings.host;
  delete settings.port;
  delete settings.log_level;

  writeSettings(settings);

  (DEV_MODE ? runDevServer : runProdServer)(host, port, logLevel);
}

main();
