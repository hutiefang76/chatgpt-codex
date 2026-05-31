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
const SMOKE_PROMPT = [
  "Call the workspace_status Action now.",
  "Reply with the current workspace name and absolute local directory.",
  "Do not modify files or run shell commands.",
].join(" ");

// A saved GPT exposes a chat URL like https://chatgpt.com/g/g-XXXX-name.
// This is the single source of truth for "the GPT was saved", used by both the
// configure capture loop and the smoke target resolver.
function isSavedGptUrl(url) {
  return typeof url === "string" && url.startsWith(GPT_URL_PREFIX);
}

function isSmokeSuccessful(text, previousText = "") {
  const fullText = String(text || "");
  const newText = previousText && fullText.includes(previousText)
    ? fullText.slice(fullText.indexOf(previousText) + previousText.length)
    : fullText;
  const hasWorkspaceSignal = /active[_\s-]?workspace|current workspace|当前工作区|workspace["'\s:]/i.test(newText);
  const hasLocalPath = /\/(?:Users|home|tmp|var|Volumes|[A-Za-z0-9._ -]+\/)|[A-Za-z]:\\/i.test(newText);
  return hasWorkspaceSignal && hasLocalPath;
}

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
  if (!chromium || typeof chromium.launchPersistentContext !== "function") {
    throw new Error("Playwright chromium launcher was not found");
  }
  const baseOptions = {
    headless: false,
    viewport: { width: 1440, height: 1000 },
  };
  const requestedChannel = String(process.env.CHATGPT_CODEX_PLAYWRIGHT_CHANNEL || "").trim();
  const channelOptions = [];
  if (requestedChannel) {
    channelOptions.push({ ...baseOptions, channel: requestedChannel });
  } else {
    channelOptions.push({ ...baseOptions, channel: "chrome" });
    channelOptions.push(baseOptions);
  }
  let lastError;
  for (const options of channelOptions) {
    try {
      return await chromium.launchPersistentContext(profile, options);
    } catch (error) {
      lastError = error;
      if (requestedChannel) break;
      if (!/chrome|executable|browser/i.test(String(error && error.message ? error.message : error))) break;
    }
  }
  throw lastError;
}

function normalizePlaywright(module) {
  if (module && module.chromium) return module;
  if (module && module.default && module.default.chromium) return module.default;
  return module;
}

async function loadPlaywright() {
  try {
    return normalizePlaywright(await import("playwright"));
  } catch (firstError) {
    for (const binDir of String(process.env.PATH || "").split(path.delimiter)) {
      if (!binDir.endsWith(path.join("node_modules", ".bin"))) continue;
      const nodeModules = path.dirname(binDir);
      try {
        const resolved = require.resolve("playwright", { paths: [nodeModules] });
        return normalizePlaywright(await import(pathToFileURL(resolved).href));
      } catch {
        // Try the next PATH entry.
      }
    }
    throw firstError;
  }
}

function classifyBuilderState(url, title, bodyText, hasTurnstile) {
  const haystack = `${url || ""}\n${title || ""}\n${bodyText || ""}`;
  const blockedByChallenge = Boolean(hasTurnstile) || /just a moment|请稍候|checking your browser|cloudflare|turnstile/i.test(haystack);
  const loggedIn = !blockedByChallenge && !/login|auth\/login|log in|sign up/i.test(haystack);
  const hasEditor = !blockedByChallenge && /gpts\/editor|builder|configure|配置|添加操作|actions?/i.test(haystack);
  const hasActions = !blockedByChallenge && /actions?|操作|schema|openapi|authentication|鉴权|api key/i.test(bodyText || "");
  return { loggedIn, hasEditor, hasActions, blockedByChallenge };
}

function numericArg(value, fallback) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
}

function shouldUseBuilderFallback(status, challengeStartedAt, now, args = {}) {
  if (String(args.fallback || "auto").toLowerCase() === "none") return false;
  if (!status || !status.blockedByChallenge || challengeStartedAt == null) return false;
  const graceSeconds = Math.max(0, numericArg(args.challenge_grace_seconds, 45));
  return Number(now) - Number(challengeStartedAt) >= graceSeconds * 1000;
}

function builderFallbackHandoff(status = {}, args = {}, trigger = "playwright_challenge") {
  return {
    stage: "builder_fallback_required",
    fallback_required: true,
    blocked_by_challenge: Boolean(status.blockedByChallenge),
    fallback: {
      kind: "chrome_or_computer_use",
      trigger,
      can_continue_with_ai_agent: true,
      local_cli_can_finish_without_browser_control: false,
      human_required: [
        "Only complete ChatGPT login or challenge if the browser is not already signed in.",
      ],
      open_url: BUILDER_URL,
      profile_path: args.profile || "",
      read_fields_command: "chatgpt-codex builder payload --json",
      credential_command: "chatgpt-codex token",
      commands_after_save: [
        "chatgpt-codex builder smoke",
        "chatgpt-codex verify",
      ],
      agent_steps: [
        "Use Chrome/Computer Use browser control to open ChatGPT Builder in the user's normal browser session.",
        "Read Builder fields from `chatgpt-codex builder payload --json` and the credential value from `chatgpt-codex token`.",
        "Create or update the private GPT, import the OpenAPI schema URL, set API key authentication to bearer-auth, paste the credential value, save, and open the saved /g/ URL.",
        "Run the smoke and verify commands after the saved GPT URL is available.",
      ],
      note: "Playwright is blocked by a ChatGPT/Cloudflare challenge. The CLI returns this handoff so an AI agent with browser control can continue instead of waiting.",
      cn_note: "Playwright 被 ChatGPT/Cloudflare 验证页阻塞。CLI 返回此交接信息，具备浏览器控制能力的 AI agent 可直接接管，而不是继续等待。",
    },
    url: status.url || BUILDER_URL,
    title: status.title || "",
  };
}

async function detectBuilder(page) {
  await page.goto(BUILDER_URL, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});
  const url = page.url();
  const title = await page.title().catch(() => "");
  const bodyText = await page.locator("body").innerText({ timeout: 10000 }).catch(() => "");
  const hasTurnstile = Boolean(await page.locator('input[name="cf-turnstile-response"]').count().catch(() => 0));
  return { ...classifyBuilderState(url, title, bodyText, hasTurnstile), url, title };
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

function labelPattern(label) {
  return new RegExp(String(label).replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "i");
}

async function clickFirst(page, labels) {
  for (const label of labels) {
    const pattern = labelPattern(label);
    const candidates = [
      page.getByRole("button", { name: pattern }).first(),
      page.getByRole("tab", { name: pattern }).first(),
      page.getByText(pattern).first(),
    ];
    for (const locator of candidates) {
      if (!(await locator.count().catch(() => 0))) continue;
      try {
        await locator.click({ timeout: 3000 });
        await page.waitForTimeout(500);
        return true;
      } catch {
        // Try the next locator shape.
      }
    }
  }
  return false;
}

async function fillFirstLoose(page, labels, value) {
  for (const label of labels) {
    const pattern = labelPattern(label);
    const candidates = [
      page.getByLabel(pattern).first(),
      page.getByPlaceholder(pattern).first(),
      page.getByRole("textbox", { name: pattern }).first(),
    ];
    for (const locator of candidates) {
      if (!(await locator.count().catch(() => 0))) continue;
      try {
        await locator.fill(value, { timeout: 3000 });
        return true;
      } catch {
        try {
          await locator.click({ timeout: 3000 });
          await page.keyboard.press(process.platform === "darwin" ? "Meta+A" : "Control+A");
          await page.keyboard.insertText(value);
          return true;
        } catch {
          // Try the next locator shape.
        }
      }
    }
  }
  return false;
}

async function fillLastTextarea(page, value) {
  const locator = page.locator("textarea").last();
  if (!(await locator.count().catch(() => 0))) return false;
  try {
    await locator.fill(value, { timeout: 3000 });
    return true;
  } catch {
    return false;
  }
}

async function loadSchemaText(context, schemaUrl) {
  try {
    const response = await context.request.get(schemaUrl, { failOnStatusCode: false });
    if (response.status() >= 200 && response.status() < 300) {
      return await response.text();
    }
  } catch {
    // Keep UI automation best-effort.
  }
  return "";
}

async function attemptActionSetup(page, context, config, ui, visibility) {
  const payload = builderPayload(config);
  const actionAttempt = {
    configure_tab: false,
    actions_panel: Boolean(ui.found_actions_text),
    create_action: false,
    schema_url: false,
    schema_textarea: false,
    privacy_url: false,
    auth_api_key: false,
    auth_bearer: false,
    auth_token: false,
    save_clicked: false,
  };

  actionAttempt.configure_tab = await clickFirst(page, ["Configure", "配置"]) || actionAttempt.configure_tab;
  actionAttempt.actions_panel = await clickFirst(page, ["Actions", "操作"]) || actionAttempt.actions_panel;
  actionAttempt.create_action = await clickFirst(page, ["Create new action", "Add action", "Create action", "添加操作", "创建新操作"]);

  actionAttempt.schema_url = await fillFirstLoose(page, ["Import from URL", "Schema URL", "OpenAPI URL", "URL"], payload.schemaUrl);
  if (!actionAttempt.schema_url) {
    const schemaText = await loadSchemaText(context, payload.schemaUrl);
    if (schemaText) {
      actionAttempt.schema_textarea = await fillFirstLoose(page, ["Schema", "OpenAPI schema", "OpenAPI"], schemaText)
        || await fillLastTextarea(page, schemaText);
    }
  }
  actionAttempt.privacy_url = await fillFirstLoose(page, ["Privacy policy", "Privacy URL", "Privacy policy URL", "隐私政策"], payload.privacyUrl);

  await clickFirst(page, ["Authentication", "鉴权", "Auth"]);
  actionAttempt.auth_api_key = await clickFirst(page, ["API Key", "API key", "API 密钥"]);
  actionAttempt.auth_bearer = await clickFirst(page, ["Bearer"]);
  actionAttempt.auth_token = await fillFirstLoose(page, ["API Key", "API key", "Bearer token", "Token", "密钥", "令牌"], config.token);

  if (visibility === "private") {
    await clickFirst(page, ["Only me", "私密", "仅自己"]);
  }
  actionAttempt.save_clicked = await clickFirst(page, ["Save", "Create", "Update", "保存", "创建", "更新"]);
  return actionAttempt;
}

async function configureUi(page, config) {
  const payload = builderPayload(config);
  await page.goto(BUILDER_URL, { waitUntil: "domcontentloaded" });
  await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});
  const status = {
    ...classifyBuilderState(
      page.url(),
      await page.title().catch(() => ""),
      await page.locator("body").innerText({ timeout: 10000 }).catch(() => ""),
      Boolean(await page.locator('input[name="cf-turnstile-response"]').count().catch(() => 0)),
    ),
  };
  if (status.blockedByChallenge) {
    return {
      prefilled: { name: false, description: false, instructions: false },
      found_actions_text: false,
      blocked_by_challenge: true,
      schema_url: payload.schemaUrl,
      privacy_url: payload.privacyUrl,
      page_url: page.url(),
    };
  }

  // These labels are the most stable part of the Builder page. The top-level
  // setup command adds a best-effort Action/auth/save pass after this.
  const prefilled = {
    name: await fillFirst(page, ["Name", "名称", "GPT name"], payload.name),
    description: await fillFirst(page, ["Description", "描述"], payload.description),
    instructions: await fillFirst(page, ["Instructions", "指令"], payload.instructions),
  };

  const pageText = await page.locator("body").innerText({ timeout: 10000 }).catch(() => "");
  return {
    prefilled,
    found_actions_text: /actions?|操作|schema|openapi|authentication|鉴权|api key/i.test(pageText),
    schema_url: payload.schemaUrl,
    privacy_url: payload.privacyUrl,
    page_url: page.url(),
  };
}

// Wait until the editor navigates to a saved GPT URL (https://chatgpt.com/g/...),
// which appears after the human saves the GPT and opens it. Resolves with the URL
// on capture, or null on timeout / Ctrl-C / browser close.
function waitForSavedGptUrl(page, context, maxSeconds) {
  return new Promise(resolve => {
    let settled = false;
    const finish = value => {
      if (settled) return;
      settled = true;
      clearInterval(poll);
      clearTimeout(cap);
      resolve(value);
    };
    const poll = setInterval(() => {
      let url = "";
      try {
        url = page.url();
      } catch {
        finish(null);
        return;
      }
      if (isSavedGptUrl(url)) finish(url);
    }, 1500);
    const cap = setTimeout(() => finish(null), Math.max(5, maxSeconds) * 1000);
    process.once("SIGINT", () => finish(null));
    context.on("close", () => finish(null));
  });
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
  console.log(JSON.stringify({
    ok: status.loggedIn && status.hasEditor,
    ...status,
    detection: "heuristic-text-scan",
    note: status.blockedByChallenge
      ? "A Cloudflare/ChatGPT challenge page is blocking the Playwright profile. Run `builder open-login`, complete the browser challenge/login manually, then rerun `builder doctor`; if it persists, use the Computer Use or Chrome fallback."
      : "Login/editor/Actions detection is a heuristic page-text scan and can be wrong (the Actions panel may be hidden behind a Configure tab). The reliable confirmation is a successful `builder smoke`.",
    profile: args.profile,
  }, null, 2));
  return status.loggedIn && status.hasEditor;
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
    await writeJsonPrivate(args.state, {
      schema_version: 1,
      updated_at: new Date().toISOString(),
      last_builder_url: page.url(),
      mode: args.mode,
      visibility: args.visibility,
    });
  } else {
    const ui = await configureUi(page, config);
    if (ui.blocked_by_challenge) {
      await writeJsonPrivate(args.state, {
        schema_version: 1,
        updated_at: new Date().toISOString(),
        last_builder_url: page.url(),
        mode: args.mode,
        visibility: args.visibility,
        blocked_by_challenge: true,
      });
      result = {
        ok: false,
        mode: args.mode,
        saved: false,
        gpt_url: "",
        prefilled: ui.prefilled,
        found_actions_text: false,
        blocked_by_challenge: true,
        schema_url: ui.schema_url,
        privacy_url: ui.privacy_url,
        manual_steps_required: [
          "Run `chatgpt-codex builder open-login`.",
          "Complete the Cloudflare/ChatGPT challenge and login in that Playwright browser.",
          "Rerun `chatgpt-codex builder doctor`, then rerun `chatgpt-codex builder configure --mode ui`.",
          "If the challenge persists, switch to the Computer Use or Chrome fallback for the Builder UI.",
        ],
        state_path: args.state,
        note: "Blocked by a Cloudflare/ChatGPT challenge page before Builder fields were available.",
      };
      await context.close();
      console.log(JSON.stringify(redact(result), null, 2));
      return false;
    }
    const manualSteps = [
      `Add an Action and import the schema URL: ${ui.schema_url}`,
      "Authentication: API key. Auth type: Bearer. Paste the token from `chatgpt-codex token` (not printed here).",
      `Privacy policy URL: ${ui.privacy_url}`,
      `Visibility: save as ${args.visibility === "private" ? "Only me" : args.visibility}.`,
      "Save the GPT, then open it (View GPT) so its /g/ chat URL loads.",
    ];
    const waitSeconds = Number(args.wait_seconds) > 0 ? Number(args.wait_seconds) : 600;

    // Live guidance on stderr so stdout stays a single JSON result for callers.
    process.stderr.write(`${JSON.stringify({
      stage: "prefilled",
      prefilled: ui.prefilled,
      manual_steps_required: manualSteps,
      waiting_seconds: waitSeconds,
      note: "Prefilled text fields. Finish Add Action + token + Save, then open the GPT; this command auto-captures the /g/ URL. Press Ctrl-C to stop without capturing.",
      cn_note: "已预填文本字段。请完成 添加 Action + 填 token + 保存，并打开该 GPT；本命令会自动捕获 /g/ 地址写入 state。Ctrl-C 可随时中止。",
    }, null, 2)}\n`);

    const capturedUrl = await waitForSavedGptUrl(page, context, waitSeconds);

    if (args.mode === "hybrid" && captures.length) {
      await writeJsonPrivate(args.routes, {
        schema_version: 1,
        captured_at: new Date().toISOString(),
        source: "playwright-hybrid-configure",
        captures: captures.map(redact),
      });
    }
    await writeJsonPrivate(args.state, {
      schema_version: 1,
      updated_at: new Date().toISOString(),
      last_builder_url: page.url(),
      ...(capturedUrl ? { gpt_url: capturedUrl } : {}),
      mode: args.mode,
      visibility: args.visibility,
    });
    result = {
      ok: Boolean(capturedUrl),
      mode: args.mode,
      saved: Boolean(capturedUrl),
      gpt_url: capturedUrl || "",
      prefilled: ui.prefilled,
      found_actions_text: ui.found_actions_text,
      blocked_by_challenge: Boolean(ui.blocked_by_challenge),
      schema_url: ui.schema_url,
      privacy_url: ui.privacy_url,
      manual_steps_required: capturedUrl ? [] : manualSteps,
      state_path: args.state,
      note: capturedUrl
        ? "Saved GPT URL captured. `builder smoke` can now open the GPT end to end."
        : "Stopped before a saved GPT URL appeared. Finish Save + open the GPT, then rerun `builder configure` to capture it.",
    };
    if (args.mode === "hybrid" && captures.length) {
      result.route_map_path = args.routes;
      result.captured = captures.length;
    }
  }
  await context.close();
  console.log(JSON.stringify(redact(result), null, 2));
  return Boolean(result && result.ok);
}

async function waitForBuilderReady(page, maxSeconds, args = {}) {
  const waitSeconds = Number(maxSeconds) > 0 ? Number(maxSeconds) : 600;
  const deadline = Date.now() + Math.max(10, waitSeconds) * 1000;
  let lastStatus = null;
  let challengeStartedAt = null;
  while (Date.now() < deadline) {
    lastStatus = await detectBuilder(page);
    if (lastStatus.loggedIn && lastStatus.hasEditor && !lastStatus.blockedByChallenge) {
      return { ok: true, ...lastStatus };
    }
    if (lastStatus.blockedByChallenge) {
      challengeStartedAt = challengeStartedAt == null ? Date.now() : challengeStartedAt;
      if (shouldUseBuilderFallback(lastStatus, challengeStartedAt, Date.now(), args)) {
        return { ok: false, ...lastStatus, ...builderFallbackHandoff(lastStatus, args) };
      }
    } else {
      challengeStartedAt = null;
    }
    process.stderr.write(`${JSON.stringify({
      stage: "waiting_for_chatgpt_login_or_builder",
      logged_in: Boolean(lastStatus.loggedIn),
      has_editor: Boolean(lastStatus.hasEditor),
      blocked_by_challenge: Boolean(lastStatus.blockedByChallenge),
      url: lastStatus.url,
      title: lastStatus.title,
      note: "Complete ChatGPT login/challenge in the opened browser; setup will continue automatically.",
      cn_note: "请在已打开的浏览器完成 ChatGPT 登录/验证；setup 会自动继续。",
    }, null, 2)}\n`);
    await page.waitForTimeout(3000);
  }
  if (lastStatus && lastStatus.blockedByChallenge && String(args.fallback || "auto").toLowerCase() !== "none") {
    return { ok: false, ...lastStatus, ...builderFallbackHandoff(lastStatus, args, "playwright_challenge_timeout") };
  }
  return { ok: false, ...(lastStatus || {}) };
}

async function runSetup(args) {
  const config = await readJson(args.config);
  const waitSeconds = Number(args.wait_seconds) > 0 ? Number(args.wait_seconds) : 600;
  const captures = [];
  const context = await launch(args.profile);
  if (args.mode === "hybrid") startSniffer(context, captures);
  const page = await context.newPage();
  let result;
  try {
    const ready = await waitForBuilderReady(page, waitSeconds, args);
    if (!ready.ok) {
      result = ready.fallback_required
        ? {
            ok: false,
            mode: args.mode,
            stage: "builder_fallback_required",
            fallback_required: true,
            logged_in: Boolean(ready.loggedIn),
            has_editor: Boolean(ready.hasEditor),
            blocked_by_challenge: Boolean(ready.blockedByChallenge),
            url: ready.url || page.url(),
            title: ready.title || "",
            profile: args.profile,
            fallback: ready.fallback,
            manual_steps_required: ready.fallback.human_required,
            note: "Playwright remained blocked long enough to trigger automatic agent fallback.",
            cn_note: "Playwright 持续被阻塞，已自动触发 agent 兜底交接。",
          }
        : {
            ok: false,
            mode: args.mode,
            stage: "waiting_for_login_or_builder",
            logged_in: Boolean(ready.loggedIn),
            has_editor: Boolean(ready.hasEditor),
            blocked_by_challenge: Boolean(ready.blockedByChallenge),
            url: ready.url || page.url(),
            title: ready.title || "",
            profile: args.profile,
            manual_steps_required: [
              "Complete ChatGPT login/challenge in the opened Playwright browser.",
              "Rerun `chatgpt-codex setup --workspace <path>` or `chatgpt-codex builder setup`.",
              "If the challenge persists in the Playwright profile, use the Computer Use or existing-Chrome fallback.",
            ],
            note: "Timed out before ChatGPT Builder became usable.",
          };
      await writeJsonPrivate(args.state, {
        schema_version: 1,
        updated_at: new Date().toISOString(),
        mode: args.mode,
        visibility: args.visibility,
        setup_stage: result.stage,
        fallback_required: Boolean(result.fallback_required),
        blocked_by_challenge: result.blocked_by_challenge,
        last_builder_url: page.url(),
      });
    } else if (args.mode === "api") {
      await context.close();
      return runConfigure(args);
    } else {
      const ui = await configureUi(page, config);
      if (ui.blocked_by_challenge) {
        result = {
          ok: false,
          mode: args.mode,
          stage: "configure_fields",
          saved: false,
          gpt_url: "",
          blocked_by_challenge: true,
          schema_url: ui.schema_url,
          privacy_url: ui.privacy_url,
          profile: args.profile,
          manual_steps_required: [
            "Complete the Cloudflare/ChatGPT challenge in the opened browser.",
            "Rerun `chatgpt-codex builder setup`.",
          ],
          note: "Builder became blocked by a challenge while configuring fields.",
        };
        await writeJsonPrivate(args.state, {
          schema_version: 1,
          updated_at: new Date().toISOString(),
          mode: args.mode,
          visibility: args.visibility,
          setup_stage: result.stage,
          blocked_by_challenge: true,
          last_builder_url: page.url(),
        });
      } else {
        const actionAttempt = await attemptActionSetup(page, context, config, ui, args.visibility);
        const manualSteps = [
          `If not already filled, add an Action and import: ${ui.schema_url}`,
          "Authentication: API key. Auth type: Bearer. Paste the token from `chatgpt-codex token`.",
          `Privacy policy URL: ${ui.privacy_url}`,
          `Visibility: save as ${args.visibility === "private" ? "Only me" : args.visibility}.`,
          "Save the GPT, then open it so its /g/ chat URL loads.",
        ];
        process.stderr.write(`${JSON.stringify({
          stage: "builder_prefilled",
          prefilled: ui.prefilled,
          action_attempt: actionAttempt,
          found_actions_text: ui.found_actions_text,
          waiting_seconds: waitSeconds,
          manual_steps_required_if_ui_blocks_automation: manualSteps,
          note: "Stable text fields are filled and setup attempted Action/auth/save automation. It now waits for a saved /g/ URL.",
          cn_note: "稳定文本字段已填写，setup 已尝试自动配置 Action/鉴权/保存。现在等待保存后的 /g/ 地址。",
        }, null, 2)}\n`);

        const capturedUrl = await waitForSavedGptUrl(page, context, waitSeconds);
        if (args.mode === "hybrid" && captures.length) {
          await writeJsonPrivate(args.routes, {
            schema_version: 1,
            captured_at: new Date().toISOString(),
            source: "playwright-hybrid-setup",
            captures: captures.map(redact),
          });
        }
        await writeJsonPrivate(args.state, {
          schema_version: 1,
          updated_at: new Date().toISOString(),
          last_builder_url: page.url(),
          ...(capturedUrl ? { gpt_url: capturedUrl } : {}),
          mode: args.mode,
          visibility: args.visibility,
          setup_stage: "capture_saved_gpt_url",
        });
        result = {
          ok: Boolean(capturedUrl),
          mode: args.mode,
          stage: "capture_saved_gpt_url",
          saved: Boolean(capturedUrl),
          gpt_url: capturedUrl || "",
          prefilled: ui.prefilled,
          action_attempt: actionAttempt,
          found_actions_text: ui.found_actions_text,
          blocked_by_challenge: false,
          schema_url: ui.schema_url,
          privacy_url: ui.privacy_url,
          manual_steps_required: capturedUrl ? [] : manualSteps,
          state_path: args.state,
          note: capturedUrl
            ? "Saved GPT URL captured. The top-level setup command can now run builder smoke."
            : "No saved GPT URL appeared before timeout.",
        };
        if (args.mode === "hybrid" && captures.length) {
          result.route_map_path = args.routes;
          result.captured = captures.length;
        }
      }
    }
  } finally {
    await context.close().catch(() => {});
  }
  console.log(JSON.stringify(redact(result), null, 2));
  return Boolean(result && result.ok);
}

async function bodyText(page) {
  return page.locator("body").innerText({ timeout: 10000 }).catch(() => "");
}

async function submitSmokePrompt(page, prompt) {
  const candidates = [
    page.getByRole("textbox").last(),
    page.locator("textarea").last(),
    page.locator('[contenteditable="true"]').last(),
  ];
  for (const locator of candidates) {
    if (!(await locator.count().catch(() => 0))) continue;
    try {
      await locator.click({ timeout: 5000 });
      await page.keyboard.type(prompt);
      await page.keyboard.press("Enter");
      return true;
    } catch {
      // Try the next composer shape.
    }
  }
  return false;
}

async function waitForSmokeResult(page, previousText, maxSeconds) {
  const deadline = Date.now() + Math.max(10, maxSeconds) * 1000;
  while (Date.now() < deadline) {
    await page.waitForTimeout(2000);
    const text = await bodyText(page);
    if (isSmokeSuccessful(text, previousText)) {
      return { ok: true, body_text_preview: text.slice(-1200) };
    }
  }
  const text = await bodyText(page);
  return { ok: false, body_text_preview: text.slice(-1200) };
}

async function runSmoke(args) {
  const state = await readJson(args.state).catch(() => ({}));
  const targetUrl = state.gpt_url || state.last_gpt_url || (isSavedGptUrl(state.last_builder_url) ? state.last_builder_url : "");
  const context = await launch(args.profile);
  const page = await context.newPage();
  let result;
  try {
    await page.goto(targetUrl || CHATGPT_HOME, { waitUntil: "domcontentloaded" });
    await page.waitForLoadState("networkidle", { timeout: 15000 }).catch(() => {});
    if (!targetUrl) {
      result = {
        ok: false,
        opened: CHATGPT_HOME,
        message: "No GPT URL saved yet. Finish builder configure/save first.",
      };
    } else {
      const waitSeconds = Number(args.wait_seconds) > 0 ? Number(args.wait_seconds) : 90;
      const beforeText = await bodyText(page);
      const submitted = await submitSmokePrompt(page, SMOKE_PROMPT);
      const smoke = submitted ? await waitForSmokeResult(page, beforeText, waitSeconds) : { ok: false, body_text_preview: beforeText.slice(-1200) };
      result = {
        ok: Boolean(submitted && smoke.ok),
        opened: targetUrl,
        submitted,
        prompt: SMOKE_PROMPT,
        wait_seconds: waitSeconds,
        body_text_preview: smoke.body_text_preview,
        message: submitted
          ? "Smoke prompt submitted. The run passes only if a workspace_status Action result appears in the page."
          : "Could not find a ChatGPT composer to submit the smoke prompt.",
      };
    }
  } finally {
    await context.close();
  }
  console.log(JSON.stringify(redact(result), null, 2));
  return Boolean(result && result.ok);
}

// Pure-function self-test. Requires no browser/login so it can run in CI; the
// playwright probe is best-effort and does not fail the run when absent.
async function runSelfTest() {
  const checks = [];
  const expect = (name, cond) => checks.push({ name, ok: Boolean(cond) });

  // Saved-GPT-URL detection — the regression that made `builder smoke` dead code.
  expect("saved_gpt_url_detected", isSavedGptUrl("https://chatgpt.com/g/g-abc123-demo"));
  expect("editor_url_not_saved", !isSavedGptUrl("https://chatgpt.com/gpts/editor"));
  expect("empty_url_not_saved", !isSavedGptUrl(""));

  const payload = builderPayload({ public_base_url: "https://actions.example.com/" });
  expect("schema_url", payload.schemaUrl === "https://actions.example.com/openapi.json");
  expect("privacy_url", payload.privacyUrl === "https://actions.example.com/privacy");

  const redacted = JSON.stringify(redact({ headers: { authorization: "Bearer secret-xyz" }, api_key: "secret-xyz" }));
  expect("redacts_secrets", !redacted.includes("secret-xyz"));

  const parsed = parseArgs(["node", "script", "configure", "--mode", "hybrid", "--wait-seconds", "5"]);
  expect("parses_mode", parsed.mode === "hybrid");
  expect("parses_wait_seconds", parsed.wait_seconds === "5");
  const setupParsed = parseArgs(["node", "script", "setup", "--wait-seconds", "9"]);
  expect("parses_setup_wait_seconds", setupParsed.command === "setup" && setupParsed.wait_seconds === "9");
  const fallbackParsed = parseArgs(["node", "script", "setup", "--fallback", "auto", "--challenge-grace-seconds", "4"]);
  expect("parses_setup_fallback", fallbackParsed.fallback === "auto" && fallbackParsed.challenge_grace_seconds === "4");
  expect("smoke_prompt_mentions_action", SMOKE_PROMPT.includes("workspace_status"));
  expect("smoke_success_detects_workspace_path", isSmokeSuccessful("assistant: active_workspace demo workspace /Users/me/project/demo"));
  expect("smoke_success_rejects_prompt_only", !isSmokeSuccessful(SMOKE_PROMPT));
  const challenge = classifyBuilderState("https://chatgpt.com/gpts/editor", "请稍候…", "", true);
  expect("builder_challenge_detected", challenge.blockedByChallenge && !challenge.hasEditor);
  expect("setup_timeout_step_detects_challenge", challenge.blockedByChallenge && !challenge.loggedIn);
  const challengeStatus = { ...challenge, url: BUILDER_URL, title: "请稍候…" };
  const now = Date.now();
  expect("builder_challenge_fallback_after_grace", shouldUseBuilderFallback(challengeStatus, now - 5000, now, fallbackParsed));
  expect("builder_challenge_no_fallback_when_disabled", !shouldUseBuilderFallback(challengeStatus, now - 5000, now, { fallback: "none", challenge_grace_seconds: "0" }));
  const handoff = builderFallbackHandoff(challengeStatus, { profile: "/tmp/chatgpt-codex-profile" });
  expect(
    "builder_fallback_handoff_is_machine_readable",
    handoff.stage === "builder_fallback_required"
      && handoff.fallback_required
      && handoff.fallback.kind === "chrome_or_computer_use"
      && handoff.fallback.read_fields_command.includes("builder payload")
      && handoff.fallback.commands_after_save.includes("chatgpt-codex verify"),
  );

  let playwrightLoaded = false;
  let playwrightHasChromium = false;
  try {
    const playwright = await loadPlaywright();
    playwrightLoaded = true;
    playwrightHasChromium = Boolean(playwright.chromium && typeof playwright.chromium.launchPersistentContext === "function");
  } catch {
    playwrightLoaded = false;
  }
  expect("playwright_has_chromium", !playwrightLoaded || playwrightHasChromium);

  const ok = checks.every(check => check.ok);
  console.log(JSON.stringify({ ok, playwright_loaded: playwrightLoaded, checks }, null, 2));
  if (!ok) process.exit(1);
}

async function main() {
  const args = parseArgs(process.argv);
  if (args.command === "self-test") return runSelfTest();
  if (!args.command || !args.profile || !args.config || !args.state || !args.routes) {
    throw new Error("usage: chatgpt_builder_playwright.mjs <open-login|doctor|sniff|configure|setup|smoke> --config <path> --profile <path> --state <path> --routes <path>");
  }
  let ok;
  if (args.command === "open-login") ok = await runOpenLogin(args);
  else if (args.command === "doctor") ok = await runDoctor(args);
  else if (args.command === "sniff") ok = await runSniff(args);
  else if (args.command === "configure") ok = await runConfigure(args);
  else if (args.command === "setup") ok = await runSetup(args);
  else if (args.command === "smoke") ok = await runSmoke(args);
  else throw new Error(`unknown command: ${args.command}`);
  if (ok === false) process.exitCode = 1;
}

main().catch(error => {
  console.error(JSON.stringify({ ok: false, error: String(error && error.message ? error.message : error) }, null, 2));
  process.exit(1);
});
