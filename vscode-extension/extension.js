/**
 * AI Code Reviewer — VS Code Extension
 * Sends code to the local/remote backend API and shows inline diagnostics.
 */

const vscode = require("vscode");
const https = require("https");
const http = require("http");
const { URL } = require("url");

const EXT_NAME = "AI Code Reviewer";
const DIAG_SOURCE = "ai-reviewer";

// ── Severity → VS Code DiagnosticSeverity ────────────────────────────────────
const SEVERITY_MAP = {
  critical: vscode.DiagnosticSeverity.Error,
  high: vscode.DiagnosticSeverity.Error,
  medium: vscode.DiagnosticSeverity.Warning,
  low: vscode.DiagnosticSeverity.Information,
  info: vscode.DiagnosticSeverity.Hint,
};

const SEVERITY_EMOJI = {
  critical: "🔴 CRITICAL",
  high: "🟠 HIGH",
  medium: "🟡 MEDIUM",
  low: "🔵 LOW",
  info: "⚪ INFO",
};

let diagnosticCollection;
let statusBarItem;

/** @param {vscode.ExtensionContext} context */
function activate(context) {
  diagnosticCollection = vscode.languages.createDiagnosticCollection(DIAG_SOURCE);
  context.subscriptions.push(diagnosticCollection);

  // Status bar
  statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  statusBarItem.command = "aiReviewer.reviewFile";
  statusBarItem.text = "$(search) AI Review";
  statusBarItem.tooltip = "Click to review current file";
  statusBarItem.show();
  context.subscriptions.push(statusBarItem);

  // Commands
  context.subscriptions.push(
    vscode.commands.registerCommand("aiReviewer.reviewFile", reviewCurrentFile),
    vscode.commands.registerCommand("aiReviewer.reviewSelection", reviewSelection)
  );

  // Auto-review on save (if enabled)
  context.subscriptions.push(
    vscode.workspace.onDidSaveTextDocument(async (doc) => {
      const cfg = vscode.workspace.getConfiguration("aiReviewer");
      if (cfg.get("autoReviewOnSave")) {
        await reviewDocument(doc);
      }
    })
  );

  console.log(`${EXT_NAME} activated.`);
}

async function reviewCurrentFile() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) {
    vscode.window.showWarningMessage("No active editor.");
    return;
  }
  await reviewDocument(editor.document);
}

async function reviewSelection() {
  const editor = vscode.window.activeTextEditor;
  if (!editor) return;
  const selection = editor.selection;
  const code = editor.document.getText(selection);
  if (!code.trim()) {
    vscode.window.showWarningMessage("No code selected.");
    return;
  }
  const lang = mapLanguage(editor.document.languageId);
  if (!lang) {
    vscode.window.showWarningMessage(`Language '${editor.document.languageId}' not supported.`);
    return;
  }
  await runReview(editor.document, code, lang, selection.start.line);
}

async function reviewDocument(doc) {
  const lang = mapLanguage(doc.languageId);
  if (!lang) return;
  await runReview(doc, doc.getText(), lang, 0);
}

async function runReview(doc, code, language, lineOffset = 0) {
  statusBarItem.text = "$(sync~spin) Reviewing…";

  try {
    const cfg = vscode.workspace.getConfiguration("aiReviewer");
    const apiUrl = cfg.get("apiUrl") || "http://localhost:8000";
    const minSev = cfg.get("minSeverity") || "medium";

    const result = await callApi(apiUrl, {
      code,
      language,
      filename: doc.fileName,
      include_refactor: false,
    });

    const sevOrder = ["info", "low", "medium", "high", "critical"];
    const minIdx = sevOrder.indexOf(minSev);

    const diagnostics = [];
    for (const issue of result.issues || []) {
      if (sevOrder.indexOf(issue.severity) < minIdx) continue;

      const line = Math.max(0, (issue.line || 1) - 1 + lineOffset);
      const lineEnd = issue.line_end ? Math.max(0, issue.line_end - 1 + lineOffset) : line;
      const range = new vscode.Range(
        new vscode.Position(line, issue.column || 0),
        new vscode.Position(lineEnd, 9999)
      );

      const diag = new vscode.Diagnostic(
        range,
        `${SEVERITY_EMOJI[issue.severity] || issue.severity.toUpperCase()} | ${issue.message}\n\nWhy: ${issue.explanation}\n\nFix: ${issue.suggestion}`,
        SEVERITY_MAP[issue.severity] || vscode.DiagnosticSeverity.Warning
      );
      diag.source = DIAG_SOURCE;
      diag.code = issue.rule_id || issue.type;

      // Attach fixed code as a quick fix if available
      if (issue.fixed_code) {
        diag.relatedInformation = [
          new vscode.DiagnosticRelatedInformation(
            new vscode.Location(doc.uri, range),
            `Suggested fix:\n${issue.fixed_code}`
          ),
        ];
      }
      diagnostics.push(diag);
    }

    diagnosticCollection.set(doc.uri, diagnostics);

    const summary = result.summary || {};
    const score = summary.overall_score ?? "?";
    const critical = summary.critical_count || 0;
    const high = summary.high_count || 0;
    const total = summary.total_issues || 0;

    statusBarItem.text = `$(search) AI: ${score}/100 (${total} issues)`;

    if (critical > 0) {
      vscode.window.showErrorMessage(`🔴 AI Review: ${critical} critical issue(s) found. Score: ${score}/100`);
    } else if (high > 0) {
      vscode.window.showWarningMessage(`🟠 AI Review: ${high} high-severity issue(s). Score: ${score}/100`);
    } else if (total > 0) {
      vscode.window.showInformationMessage(`✅ AI Review complete: ${total} suggestion(s). Score: ${score}/100`);
    } else {
      vscode.window.showInformationMessage(`✅ AI Review: Excellent code! Score: ${score}/100`);
    }
  } catch (err) {
    statusBarItem.text = "$(search) AI Review";
    vscode.window.showErrorMessage(`AI Code Reviewer error: ${err.message}`);
  }
}

function mapLanguage(vscodeLangId) {
  const map = {
    python: "python",
    javascript: "javascript",
    typescript: "typescript",
    java: "java",
    go: "go",
    rust: "rust",
    cpp: "cpp",
    c: "c",
  };
  return map[vscodeLangId] || null;
}

function callApi(baseUrl, payload) {
  return new Promise((resolve, reject) => {
    const url = new URL("/api/v1/review", baseUrl);
    const body = JSON.stringify(payload);
    const isHttps = url.protocol === "https:";
    const lib = isHttps ? https : http;

    const options = {
      hostname: url.hostname,
      port: url.port || (isHttps ? 443 : 80),
      path: url.pathname,
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Content-Length": Buffer.byteLength(body),
      },
      timeout: 120000,
    };

    const req = lib.request(options, (res) => {
      let data = "";
      res.on("data", (chunk) => (data += chunk));
      res.on("end", () => {
        try {
          const parsed = JSON.parse(data);
          if (res.statusCode >= 400) {
            reject(new Error(parsed.detail || `HTTP ${res.statusCode}`));
          } else {
            resolve(parsed);
          }
        } catch {
          reject(new Error("Invalid JSON from API"));
        }
      });
    });

    req.on("error", reject);
    req.on("timeout", () => { req.destroy(); reject(new Error("Request timed out")); });
    req.write(body);
    req.end();
  });
}

function deactivate() {
  diagnosticCollection?.clear();
}

module.exports = { activate, deactivate };
