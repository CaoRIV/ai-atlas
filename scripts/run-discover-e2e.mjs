import { spawn, spawnSync } from "node:child_process";
import { randomBytes } from "node:crypto";
import { once } from "node:events";
import { existsSync, mkdirSync, openSync, closeSync, readFileSync, rmSync } from "node:fs";
import { createServer } from "node:net";
import { dirname, join, resolve } from "node:path";
import process from "node:process";
import { fileURLToPath } from "node:url";
import { setTimeout as delay } from "node:timers/promises";

const repositoryRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const runId = randomBytes(8).toString("hex");
const databaseName = `ai_atlas_e2e_${runId}`;
const artifactRoot = resolve(repositoryRoot, process.env.E2E_ARTIFACT_ROOT || ".cache/discover-e2e");
const runDirectory = join(artifactRoot, runId);
const playwrightOutput = join(runDirectory, "test-results");
const nextDistDirectory = ".next-e2e";
const apiLog = join(runDirectory, "api.log");
const webLog = join(runDirectory, "web.log");
const managedProcesses = new Set();
let databaseCreated = false;
let cleanupPromise;
let runSucceeded = false;

function requiredInteger(name, fallback, minimum, maximum) {
  const raw = process.env[name];
  if (raw === undefined || raw === "") return fallback;
  if (!/^\d+$/.test(raw)) throw new Error(`${name} must be an integer.`);
  const value = Number(raw);
  if (value < minimum || value > maximum) {
    throw new Error(`${name} must be between ${minimum} and ${maximum}.`);
  }
  return value;
}

function localDatabaseAdminUrl() {
  const fallbackPort = requiredInteger("POSTGRES_PORT", 5432, 1, 65535);
  const value =
    process.env.E2E_DATABASE_ADMIN_URL ||
    `postgresql://ai_atlas:ai_atlas_dev@127.0.0.1:${fallbackPort}/ai_atlas`;
  const parsed = new URL(value);
  if (!["postgres:", "postgresql:"].includes(parsed.protocol)) {
    throw new Error("E2E_DATABASE_ADMIN_URL must be a PostgreSQL URL.");
  }
  if (!["127.0.0.1", "localhost", "[::1]"].includes(parsed.hostname)) {
    throw new Error("E2E_DATABASE_ADMIN_URL must target a local PostgreSQL server.");
  }
  return parsed;
}

function configuredWebOrigin() {
  const value = process.env.E2E_BASE_URL;
  if (!value) return null;
  const parsed = new URL(value);
  if (
    parsed.protocol !== "http:" ||
    parsed.hostname !== "127.0.0.1" ||
    parsed.pathname !== "/" ||
    parsed.search ||
    parsed.hash ||
    parsed.username ||
    parsed.password
  ) {
    throw new Error("E2E_BASE_URL must be an HTTP 127.0.0.1 origin without credentials.");
  }
  const port = Number(parsed.port);
  if (!Number.isInteger(port) || port < 1024 || port > 65535) {
    throw new Error("E2E_BASE_URL must include a port between 1024 and 65535.");
  }
  const configuredPort = requiredInteger("E2E_WEB_PORT", port, 1024, 65535);
  if (configuredPort !== port) {
    throw new Error("E2E_BASE_URL and E2E_WEB_PORT must use the same port.");
  }
  return { origin: parsed.origin, port };
}

function temporaryDatabaseUrl(adminUrl) {
  const value = new URL(adminUrl);
  value.pathname = `/${databaseName}`;
  return value.toString();
}

function pythonExecutable() {
  if (process.env.E2E_PYTHON) return process.env.E2E_PYTHON;
  const candidate =
    process.platform === "win32"
      ? join(repositoryRoot, ".venv", "Scripts", "python.exe")
      : join(repositoryRoot, ".venv", "bin", "python");
  if (!existsSync(candidate)) {
    throw new Error("Python environment missing. Run the repository setup script first.");
  }
  return candidate;
}

function pnpmInvocation(argumentsList) {
  const entrypoint = process.env.npm_execpath;
  if (!entrypoint) {
    throw new Error("Run this harness through `pnpm test:e2e:discover`.");
  }
  if (/\.(?:c?js|mjs)$/i.test(entrypoint)) {
    return { command: process.execPath, arguments: [entrypoint, ...argumentsList] };
  }
  return { command: entrypoint, arguments: argumentsList };
}

function environment(overrides = {}) {
  return {
    ...process.env,
    PYTHONPATH: join(repositoryRoot, "apps", "api", "src"),
    PYTHONUTF8: "1",
    RUN_LIVE_AI_TESTS: "0",
    GEMINI_API_KEY: "",
    NEXT_TELEMETRY_DISABLED: "1",
    ...overrides,
  };
}

function spawnOptions(env, stdio = "inherit") {
  return {
    cwd: repositoryRoot,
    env,
    stdio,
    detached: process.platform !== "win32",
    windowsHide: true,
  };
}

function startCommand(command, argumentsList, options) {
  const child = spawn(command, argumentsList, options);
  managedProcesses.add(child);
  child.once("exit", () => managedProcesses.delete(child));
  return child;
}

async function runCommand(command, argumentsList, env, { capture = false } = {}) {
  const child = startCommand(
    command,
    argumentsList,
    spawnOptions(env, capture ? ["ignore", "pipe", "pipe"] : "inherit"),
  );
  let stdout = "";
  let stderr = "";
  if (capture) {
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk) => {
      stdout += chunk;
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk;
    });
  }
  const [code, signal] = await once(child, "exit");
  if (code !== 0) {
    const detail = capture ? `\n${stdout}${stderr}`.trimEnd() : "";
    throw new Error(`Command failed (${code ?? signal}): ${command}${detail ? `\n${detail}` : ""}`);
  }
  return { stdout, stderr };
}

function startLoggedCommand(command, argumentsList, env, logPath) {
  const descriptor = openSync(logPath, "a");
  try {
    return startCommand(command, argumentsList, spawnOptions(env, ["ignore", descriptor, descriptor]));
  } finally {
    closeSync(descriptor);
  }
}

function logTail(path) {
  if (!existsSync(path)) return "";
  const content = readFileSync(path, "utf8");
  return content.slice(-4000);
}

async function unusedPort(configuredName) {
  const configured = requiredInteger(configuredName, 0, 1024, 65535);
  if (configured) return configured;
  const server = createServer();
  server.unref();
  await new Promise((resolveListen, rejectListen) => {
    server.once("error", rejectListen);
    server.listen(0, "127.0.0.1", resolveListen);
  });
  const address = server.address();
  const port = typeof address === "object" && address ? address.port : 0;
  await new Promise((resolveClose, rejectClose) =>
    server.close((error) => (error ? rejectClose(error) : resolveClose())),
  );
  if (!port) throw new Error(`Could not allocate ${configuredName}.`);
  return port;
}

async function waitForHttp(url, child, logPath, validate) {
  const timeout = requiredInteger("E2E_STARTUP_TIMEOUT_MS", 60_000, 5_000, 180_000);
  const deadline = Date.now() + timeout;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) {
      throw new Error(`Service exited before readiness.\n${logTail(logPath)}`);
    }
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(2_000) });
      if (response.ok && (await validate(response))) return;
    } catch (error) {
      if (error?.name !== "TimeoutError" && error?.name !== "AbortError") {
        // Connection failures are expected until the bounded readiness deadline.
      }
    }
    await delay(200);
  }
  throw new Error(`Service readiness timed out for ${url}.\n${logTail(logPath)}`);
}

async function stopProcess(child) {
  if (!child || child.exitCode !== null || !child.pid) return;
  if (process.platform === "win32") {
    spawnSync("taskkill", ["/pid", String(child.pid), "/T", "/F"], {
      stdio: "ignore",
      windowsHide: true,
    });
  } else {
    try {
      process.kill(-child.pid, "SIGTERM");
    } catch (error) {
      if (error?.code !== "ESRCH") throw error;
    }
  }
  await Promise.race([once(child, "exit"), delay(5_000)]);
  if (child.exitCode === null && process.platform !== "win32") {
    try {
      process.kill(-child.pid, "SIGKILL");
    } catch (error) {
      if (error?.code !== "ESRCH") throw error;
    }
  }
}

async function cleanup(python, databaseEnvironment) {
  if (cleanupPromise) return cleanupPromise;
  cleanupPromise = (async () => {
    const errors = [];
    for (const child of [...managedProcesses].reverse()) {
      try {
        await stopProcess(child);
      } catch {
        errors.push("E2E_PROCESS_CLEANUP_FAILED");
      }
    }
    if (databaseCreated) {
      try {
        await runCommand(python, ["scripts/e2e_database.py", "drop"], databaseEnvironment, {
          capture: true,
        });
        databaseCreated = false;
      } catch {
        errors.push("E2E_DATABASE_CLEANUP_FAILED");
      }
    }
    rmSync(join(repositoryRoot, "apps", "web", nextDistDirectory), {
      force: true,
      recursive: true,
    });
    if (runSucceeded && errors.length === 0) {
      rmSync(runDirectory, { force: true, recursive: true });
    }
    if (errors.length) throw new Error(errors.join(","));
  })();
  return cleanupPromise;
}

async function main() {
  mkdirSync(runDirectory, { recursive: true });
  const python = pythonExecutable();
  const adminUrl = localDatabaseAdminUrl();
  const databaseUrl = temporaryDatabaseUrl(adminUrl);
  const databaseEnvironment = environment({
    E2E_DATABASE_ADMIN_URL: adminUrl.toString(),
    E2E_DATABASE_NAME: databaseName,
  });
  const applicationEnvironment = environment({ DATABASE_URL: databaseUrl });
  const webEnvironment = environment({ NEXT_DIST_DIR: nextDistDirectory });
  delete webEnvironment.DATABASE_URL;
  const apiPort = await unusedPort("E2E_API_PORT");
  const configuredWeb = configuredWebOrigin();
  const webPort = configuredWeb?.port ?? (await unusedPort("E2E_WEB_PORT"));
  if (webPort === apiPort) throw new Error("E2E_API_PORT and E2E_WEB_PORT must differ.");
  const apiOrigin = `http://127.0.0.1:${apiPort}`;
  const webOrigin = configuredWeb?.origin ?? `http://127.0.0.1:${webPort}`;
  webEnvironment.API_BASE_URL = apiOrigin;

  const playwrightInstall = pnpmInvocation(["exec", "playwright", "install", "chromium"]);
  await runCommand(
    playwrightInstall.command,
    playwrightInstall.arguments,
    environment({ PLAYWRIGHT_SKIP_BROWSER_GC: "1" }),
  );

  await runCommand(python, ["scripts/e2e_database.py", "create"], databaseEnvironment, {
    capture: true,
  });
  databaseCreated = true;
  await runCommand(
    python,
    ["apps/api/src/ai_atlas_api/migrations.py", "up"],
    applicationEnvironment,
    { capture: true },
  );
  const imported = await runCommand(
    python,
    [
      "-m",
      "ai_atlas_api.curated_cli",
      "import",
      "--format",
      "json",
      "data/curated/taxonomy.json",
      "data/curated/tools.json",
    ],
    applicationEnvironment,
    { capture: true },
  );
  const importReport = JSON.parse(imported.stdout);
  const expectedSummary = { added: 202, updated: 0, unchanged: 0 };
  if (
    importReport.status !== "valid" ||
    JSON.stringify(importReport.summary) !== JSON.stringify(expectedSummary)
  ) {
    throw new Error("Curated E2E seed did not import the expected 202 records.");
  }

  await runCommand(python, ["scripts/e2e_database.py", "seed-fixtures"], databaseEnvironment, {
    capture: true,
  });

  const build = pnpmInvocation(["--filter", "@ai-atlas/web", "build"]);
  await runCommand(build.command, build.arguments, webEnvironment);

  const api = startLoggedCommand(
    python,
    [
      "-m",
      "uvicorn",
      "ai_atlas_api.main:app",
      "--host",
      "127.0.0.1",
      "--port",
      String(apiPort),
      "--no-access-log",
    ],
    applicationEnvironment,
    apiLog,
  );
  await waitForHttp(`${apiOrigin}/health/ready`, api, apiLog, async () => true);

  const start = pnpmInvocation([
    "--filter",
    "@ai-atlas/web",
    "exec",
    "next",
    "start",
    "--hostname",
    "127.0.0.1",
    "--port",
    String(webPort),
  ]);
  const web = startLoggedCommand(start.command, start.arguments, webEnvironment, webLog);
  await waitForHttp(`${webOrigin}/api/catalog/categories`, web, webLog, async (response) => {
    const body = await response.json();
    return Array.isArray(body.data) && body.data.length === 8;
  });

  console.log(`Discover E2E stack ready at ${webOrigin}`);
  const test = pnpmInvocation(["exec", "playwright", "test", "--config", "playwright.config.ts"]);
  await runCommand(
    test.command,
    test.arguments,
    environment({
      DISCOVER_BASE_URL: webOrigin,
      E2E_PLAYWRIGHT_OUTPUT_DIR: playwrightOutput,
    }),
  );
  runSucceeded = true;
  console.log("Discover E2E passed; temporary services and database will be removed.");
}

const signalExitCode = { SIGINT: 130, SIGTERM: 143 };
for (const signal of Object.keys(signalExitCode)) {
  process.once(signal, () => {
    const python = pythonExecutable();
    const adminUrl = localDatabaseAdminUrl();
    void cleanup(
      python,
      environment({
        E2E_DATABASE_ADMIN_URL: adminUrl.toString(),
        E2E_DATABASE_NAME: databaseName,
      }),
    ).finally(() => process.exit(signalExitCode[signal]));
  });
}

try {
  await main();
} catch (error) {
  console.error(error instanceof Error ? error.message : "Discover E2E harness failed.");
  process.exitCode = 1;
} finally {
  try {
    await cleanup(
      pythonExecutable(),
      environment({
        E2E_DATABASE_ADMIN_URL: localDatabaseAdminUrl().toString(),
        E2E_DATABASE_NAME: databaseName,
      }),
    );
  } catch (error) {
    console.error(error instanceof Error ? error.message : "E2E cleanup failed.");
    process.exitCode = 1;
  }
  if (process.exitCode) {
    console.error(`Failure artifacts: ${runDirectory}`);
  }
}
