#!/usr/bin/env node
import fs from "node:fs/promises";
import { createRequire } from "node:module";
import path from "node:path";
import process from "node:process";
import { pathToFileURL } from "node:url";

const CHATGPT_HOME = "https://chatgpt.com/";
const BUILDER_URL = "https://chatgpt.com/gpts/editor";
const GPT_URL_PREFIX = "https://chatgpt.com/g/";
const require = createRequire(import.meta.url);

function parseArgs(argv) {
  const result = { command: argv[2], mode: "ui", visibility: "private" };
  for (let i = 3; i < argv.length; i += 1) {
    const arg = argv[i];
    if (!arg.startsWith("--")) continue;
    const key = arg.slice(2).replaceAll("-", "_");
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) {
      result[key] = true;
    } else {
      result[key] = next;
      i += 1;
    }
  }
  return result;
}

async function readJson(file) {
  return JSON.parse(await fs.readFile(file, "utf8"));
}

async function writeJsonPrivate(file, value) {
  await fs.mkdir(path.dirname(file), { recursive: true });
  await fs.writeFile(file, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 });
  if (process.platform !== "win32") {
    await fs.chmod(file, 0o600);
  }
}

function actionBase(config) {
  return String(config.public_base_url || "").replace(/\/+$/, "");
}

function builderPayload(config) {
  const base = actionBase(config);
  return {
    name: "Local Coding Bridge",
    description: "Access and edit one authorized local workspace through a private bearer-protected Action bridge.",
    instructions: [
      "You are my local coding assistant for the workspace exposed through Actions.",
      "Use workspace_status before file, code, or command work so you can show the current local directory.",
      "Use list_workspaces and switch_workspace when I ask to view or switch projects.",
      "Only switch to authorized workspace names returned by list_workspaces.",
      "Use list_files, read_file, search_text, write_file, apply_patch, and exec_command for project work.",
      "Inspect files before editing. Keep changes scoped.",
      "Do not run destructive commands unless I explicitly ask for that exact action in the current chat.",
    ].join(" "),
    schemaUrl: `${base}/openapi.json`,
    privacyUrl: `${base}/privacy`,
  };
}

function redact(value) {
  if (Array.isArray(value)) return value.map(redact);
  if (value && typeof value === "object") {
    const result = {};
    for (const [key, item] of Object.entries(value)) {
      const lowered = key.toLowerCase();
      if (/(authorization|cookie|token|api[_-]?key|password|secret)/.test(lowered)) {
        result[key] = "[REDACTED]";
      } else {
        result[key] = redact(item);
      }
    }
    return result;
  }
  if (typeof value !== "string") return value;
  let redacted = value.replace(/Bearer\s+[A-Za-z0-9._~+/=-]+/gi, "Bearer [REDACTED]");
  redacted = redacted.replace(/(session|token|api[_-]?key|password|secret)=([^;&\s]+)/gi, "$1=[REDACTED]");
  try {
    const parsed = JSON.parse(redacted);
    redacted = JSON.stringify(redact(parsed));
  } catch {
    // Keep non-JSON strings as text.
  }
  return redacted;
}

function shouldCapture(url) {
  return /chatgpt\.com/.test(url) && /(backend|gizmo|gpts|actions|aip|conversation|share)/i.test(url);
}

function replayHeaders(headers) {
  const result = {};
  for (const [key, value] of Object.entries(headers || {})) {
    const lowered = key.toLowerCase();
    if (["authorization", "cookie", "set-cookie", "content-length", "host"].includes(lowered)) continue;
    if (String(value).includes("[REDACTED]")) continue;
    result[key] = value;
  }
  return result;
}

function hydrateSecretPlaceholders(value, config) {
  if (Array.isArray(value)) return value.map(item => hydrateSecretPlaceholders(item, config));
  if (value && typeof value === "object") {
    const result = {};
    for (const [key, item] of Object.entries(value)) {
      const lowered = key.toLowerCase();
      if (typeof item === "string" && item === "[REDACTED]" && /(api[_-]?key|token|secret)/.test(lowered)) {
        result[key] = config.token;
      } else {
        result[key] = hydrateSecretPlaceholders(item, config);
      }
    }
    return result;
  }
  return value;
}

function replayBody(postData, config) {
  if (!postData) return undefined;
  try {
    return hydrateSecretPlaceholders(JSON.parse(postData), config);
  } catch {
    return String(postData).replaceAll("[REDACTED]", "");
  }
}

function replayCandidate(routeMap) {
  const captures = Array.isArray(routeMap.captures) ? routeMap.captures : [];
  const requests = captures.filter(item => item.kind === "request" && /^(POST|PUT|PATCH)$/i.test(item.method || ""));
  const preferred = requests.find(item => /gizmo|gpts|actions/i.test(item.url || "") && /Local Coding Bridge|openapi|schema|privacy|api_key|auth/i.test(String(item.postData || "")));
  return preferred || requests.find(item => /gizmo|gpts|actions/i.test(item.url || "")) || null;
}

function startSniffer(context, captures) {
  context.on("request", request => {
    const url = request.url();
    if (!shouldCapture(url)) return;
    captures.push({
      kind: "request",
      at: new Date().toISOString(),
      method: request.method(),
      url,
      headers: redact(request.headers()),
      postData: redact(request.postData() || ""),
    });
  });
  context.on("response", async response => {
    const url = response.url();
    if (!shouldCapture(url)) return;
    const item = {
      kind: "response",
      at: new Date().toISOString(),
      status: response.status(),
      url,
      headers: redact(response.headers()),
      preview: "",
    };
    try {
      const contentType = response.headers()["content-type"] || "";
      if (/json|text/.test(contentType)) {
        item.preview = redact((await response.text()).slice(0, 4000));
      }
    } catch {
      item.preview = "[unavailable]";
    }
    captures.push(item);
  });
}

async function launch(profile) {
  await fs.mkdir(profile, { recursive: true });
  const { chromium } = await loadPlaywright();
  return chromium.launchPersistentContext(profile, {
    headless: false,
    viewport: { width: 1440, height: 1000 },
  });
}

async function loadPlaywright() {
  try {
    return await import("playwright");
  } catch (firstError) {
    for (const binDir of String(process.env.PATH || "").split(path.delimiter)) {
      if (!binDir.endsWith(path.join("node_modules", ".bin"))) continue;
      const nodeModules = path.dirname(binDir);
      try {
        const resolved = require.resolve("playwright", { paths: [nodeModules] });
        return await import(pathToFileURL(resolved).href);
      } catch {
        // Try the next PATH entry.
      }
    }
    throw firstError;
  }
}

async function detectBuilder(page) {
  await page.goto(BUILDER_URL, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});
  const url = page.url();
  const bodyText = await page.locator("body").innerText({ timeout: 10000 }).catch(() => "");
  const loggedIn = !/login|auth\/login|log in|sign up/i.test(url + "\n" + bodyText);
  const hasEditor = /gpts\/editor|builder|configure|配置|添加操作|actions?/i.test(url + "\n" + bodyText);
  const hasActions = /actions?|操作|schema|openapi|authentication|鉴权|api key/i.test(bodyText);
  return { loggedIn, hasEditor, hasActions, url };
}

async function fillFirst(page, labels, value) {
  for (const label of labels) {
    const locator = page.getByLabel(label).first();
    if (await locator.count().catch(() => 0)) {
      await locator.fill(value).catch(async () => {
        await locator.click();
        await page.keyboard.press(process.platform === "darwin" ? "Meta+A" : "Control+A");
        await page.keyboard.type(value);
      });
      return true;
    }
  }
  return false;
}

async function configureUi(page, config, visibility) {
  const payload = builderPayload(config);
  await page.goto(BUILDER_URL, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});

  await fillFirst(page, ["Name", "名称", "GPT name"], payload.name);
  await fillFirst(page, ["Description", "描述"], payload.description);
  await fillFirst(page, ["Instructions", "指令"], payload.instructions);

  const pageText = await page.locator("body").innerText({ timeout: 10000 }).catch(() => "");
  const result = {
    attempted: true,
    visibility,
    page_url: page.url(),
    found_actions_text: /actions?|操作|schema|openapi|authentication|鉴权|api key/i.test(pageText),
    schema_url: payload.schemaUrl,
    privacy_url: payload.privacyUrl,
    note: "If the UI did not expose stable form controls, rerun sniff mode and use Computer Use fallback.",
  };
  return result;
}

async function runOpenLogin(args) {
  const context = await launch(args.profile);
  const page = await context.newPage();
  await page.goto(CHATGPT_HOME, { waitUntil: "domcontentloaded" });
  console.log(JSON.stringify({ ok: true, opened: CHATGPT_HOME, profile: args.profile, next: "Log in manually, then stop this command with Ctrl-C or run builder doctor in another terminal." }, null, 2));
  await page.waitForTimeout(2147483647);
}

async function runDoctor(args) {
  const context = await launch(args.profile);
  const page = await context.newPage();
  const status = await detectBuilder(page);
  await context.close();
  console.log(JSON.stringify({ ok: status.loggedIn && status.hasEditor, ...status, profile: args.profile }, null, 2));
}

async function runSniff(args) {
  const captures = [];
  const context = await launch(args.profile);
  startSniffer(context, captures);
  const page = await context.newPage();
  await page.goto(BUILDER_URL, { waitUntil: "domcontentloaded" });
  const flush = async () => {
    await writeJsonPrivate(args.routes, {
      schema_version: 1,
      captured_at: new Date().toISOString(),
      source: "playwright-same-session-sniffer",
      warning: "Internal ChatGPT routes are not stable. Replay only in the same Playwright session and verify by refreshing the Builder page.",
      captures: captures.map(redact),
    });
    console.log(JSON.stringify({ ok: true, route_map_path: args.routes, captured: captures.length }, null, 2));
  };
  process.once("SIGINT", async () => {
    await flush();
    await context.close();
    process.exit(0);
  });
  console.log(JSON.stringify({ ok: true, opened: BUILDER_URL, route_map_path: args.routes, next: "Perform one Builder save/configure flow, then press Ctrl-C here to save the redacted route map." }, null, 2));
  await page.waitForTimeout(2147483647);
}

async function runConfigure(args) {
  const config = await readJson(args.config);
  const captures = [];
  const context = await launch(args.profile);
  if (args.mode === "hybrid") startSniffer(context, captures);
  const page = await context.newPage();
  let result;
  if (args.mode === "api") {
    const routeMap = await readJson(args.routes).catch(() => null);
    const candidate = routeMap ? replayCandidate(routeMap) : null;
    if (!candidate) {
      result = {
        ok: false,
        mode: "api",
        error: "API replay requires a validated route map with a replayable Builder POST/PUT/PATCH request. Run builder sniff first; this script will not guess undocumented routes.",
        route_map_path: args.routes,
      };
    } else {
      const response = await context.request.fetch(candidate.url, {
        method: candidate.method,
        headers: replayHeaders(candidate.headers),
        data: replayBody(candidate.postData, config),
        failOnStatusCode: false,
      });
      await page.goto(BUILDER_URL, { waitUntil: "domcontentloaded" });
      await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});
      result = {
        ok: response.status() >= 200 && response.status() < 300,
        mode: "api",
        replayed_url: candidate.url,
        replayed_method: candidate.method,
        status: response.status(),
        route_map_path: args.routes,
        validation_url: page.url(),
        note: "The request was replayed inside the same Playwright browser context and the Builder page was refreshed afterward.",
      };
    }
  } else {
    result = await configureUi(page, config, args.visibility);
    result.ok = true;
    result.mode = args.mode;
    if (captures.length) {
      await writeJsonPrivate(args.routes, {
        schema_version: 1,
        captured_at: new Date().toISOString(),
        source: "playwright-hybrid-configure",
        captures: captures.map(redact),
      });
      result.route_map_path = args.routes;
      result.captured = captures.length;
    }
  }
  await writeJsonPrivate(args.state, {
    schema_version: 1,
    updated_at: new Date().toISOString(),
    last_builder_url: page.url(),
    mode: args.mode,
    visibility: args.visibility,
  });
  await context.close();
  console.log(JSON.stringify(redact(result), null, 2));
}

async function runSmoke(args) {
  const state = await readJson(args.state).catch(() => ({}));
  const targetUrl = state.gpt_url || state.last_gpt_url || (state.last_builder_url && state.last_builder_url.startsWith(GPT_URL_PREFIX) ? state.last_builder_url : "");
  const context = await launch(args.profile);
  const page = await context.newPage();
  await page.goto(targetUrl || CHATGPT_HOME, { waitUntil: "domcontentloaded" });
  const result = {
    ok: Boolean(targetUrl),
    opened: targetUrl || CHATGPT_HOME,
    message: targetUrl
      ? "GPT page opened. Ask it to call getWorkspaceStatus; approve the first Action domain prompt if shown."
      : "No GPT URL saved yet. Finish builder configure/save first.",
  };
  await context.close();
  console.log(JSON.stringify(result, null, 2));
}

async function main() {
  const args = parseArgs(process.argv);
  if (args.command === "self-test") {
    await loadPlaywright();
    console.log(JSON.stringify({ ok: true, playwright_loaded: true }, null, 2));
    return;
  }
  if (!args.command || !args.profile || !args.config || !args.state || !args.routes) {
    throw new Error("usage: chatgpt_builder_playwright.mjs <open-login|doctor|sniff|configure|smoke> --config <path> --profile <path> --state <path> --routes <path>");
  }
  if (args.command === "open-login") return runOpenLogin(args);
  if (args.command === "doctor") return runDoctor(args);
  if (args.command === "sniff") return runSniff(args);
  if (args.command === "configure") return runConfigure(args);
  if (args.command === "smoke") return runSmoke(args);
  throw new Error(`unknown command: ${args.command}`);
}

main().catch(error => {
  console.error(JSON.stringify({ ok: false, error: String(error && error.message ? error.message : error) }, null, 2));
  process.exit(1);
});
