/**
 * CodeProvenance Web Dashboard Frontend Logic
 * Multi-Language AST Inspector with Export as Markdown and Copy All.
 */

let layerChart = null;
let currentReport = null;
let activeSeverityFilter = "all";
let searchFilterText = "";

document.addEventListener("DOMContentLoaded", () => {
  lucide.createIcons();
  initLayerChart();
  triggerScan("");

  // Scan Form
  const scanForm = document.getElementById("scan-form");
  if (scanForm) {
    scanForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const customPath = document.getElementById("target-dir-input").value.trim();
      triggerScan(customPath);
    });
  }

  // Quick Preset Buttons
  document.querySelectorAll(".btn-quick-scan").forEach(btn => {
    btn.addEventListener("click", () => {
      const path = btn.getAttribute("data-path");
      document.getElementById("target-dir-input").value = path;
      triggerScan(path);
    });
  });

  // Severity Filter Buttons
  document.querySelectorAll(".filter-sev-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".filter-sev-btn").forEach(b => {
        b.className = "filter-sev-btn px-2.5 py-1 rounded-md text-[11px] font-semibold bg-gray-800 hover:bg-gray-700 text-gray-300";
      });
      btn.className = "filter-sev-btn px-2.5 py-1 rounded-md text-[11px] font-semibold bg-cyan-700 text-white shadow-sm";
      activeSeverityFilter = btn.getAttribute("data-sev");
      renderViolationsList();
    });
  });

  // Search input filter
  const searchInput = document.getElementById("violation-search-input");
  if (searchInput) {
    searchInput.addEventListener("input", (e) => {
      searchFilterText = e.target.value.toLowerCase().trim();
      renderViolationsList();
    });
  }

  // Copy All Button
  const btnCopy = document.getElementById("btn-copy-all");
  if (btnCopy) {
    btnCopy.addEventListener("click", copyAllIssuesMarkdown);
  }

  // Export as .md Button
  const btnExport = document.getElementById("btn-export-md");
  if (btnExport) {
    btnExport.addEventListener("click", exportIssuesAsMarkdown);
  }
});

function initLayerChart() {
  const ctx = document.getElementById("layer-chart").getContext("2d");
  layerChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: ["Presentation", "Services", "Data", "Core"],
      datasets: [{
        data: [0, 0, 0, 0],
        backgroundColor: ["#06b6d4", "#6366f1", "#10b981", "#f59e0b"],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: "right", labels: { color: "#9ca3af", font: { size: 11 } } }
      }
    }
  });
}

function setScanningState(isScanning) {
  const btn = document.getElementById("btn-scan");
  const btnText = document.getElementById("scan-btn-text");
  const icon = document.getElementById("scan-icon");
  const errorAlert = document.getElementById("scan-error-alert");

  if (isScanning) {
    if (btn) btn.disabled = true;
    if (btnText) btnText.innerText = "Scanning...";
    if (icon) icon.classList.add("animate-spin");
    if (errorAlert) errorAlert.classList.add("hidden");
  } else {
    if (btn) btn.disabled = false;
    if (btnText) btnText.innerText = "Scan Codebase";
    if (icon) icon.classList.remove("animate-spin");
  }
}

async function triggerScan(targetPath = "") {
  setScanningState(true);
  try {
    const url = targetPath ? `/api/scan?target_path=${encodeURIComponent(targetPath)}` : "/api/scan";
    const res = await fetch(url);
    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      const detail = errData.detail || `Server error: HTTP ${res.status}`;
      showScanError(detail);
      setScanningState(false);
      return;
    }
    currentReport = await res.json();
    renderReport(currentReport);
  } catch (err) {
    showScanError(`Failed to connect to scanner API: ${err.message}`);
  } finally {
    setScanningState(false);
  }
}

function showScanError(message) {
  const errorAlert = document.getElementById("scan-error-alert");
  const errorMsg = document.getElementById("scan-error-msg");
  if (errorAlert && errorMsg) {
    errorMsg.innerText = message;
    errorAlert.classList.remove("hidden");
  }
}

function renderReport(report) {
  // Update path banner
  const pathEl = document.getElementById("active-scan-path");
  if (pathEl) pathEl.innerText = report.root_path;

  const timeEl = document.getElementById("scan-timestamp");
  if (timeEl) timeEl.innerText = `Scanned at ${new Date(report.scanned_at).toLocaleTimeString()}`;

  // KPIs
  document.getElementById("kpi-score").innerText = report.compliance_score_pct.toFixed(1);
  const statusEl = document.getElementById("kpi-status");
  statusEl.innerText = report.drift_status;
  if (report.compliance_score_pct >= 85) {
    statusEl.className = "mt-2 text-xs text-emerald-400 font-medium";
  } else if (report.compliance_score_pct >= 70) {
    statusEl.className = "mt-2 text-xs text-amber-400 font-medium";
  } else {
    statusEl.className = "mt-2 text-xs text-rose-400 font-medium";
  }

  document.getElementById("kpi-files").innerText = report.total_files;
  document.getElementById("kpi-loc").innerText = `${report.total_loc.toLocaleString()} lines of code`;
  document.getElementById("kpi-violations").innerText = report.violations.length;

  const criticalCount = report.violations.filter(v => v.severity === "critical").length;
  const highCount = report.violations.filter(v => v.severity === "high").length;
  const mediumCount = report.violations.filter(v => v.severity === "medium").length;

  document.getElementById("kpi-critical").innerText = `${criticalCount} critical breaches`;
  document.getElementById("kpi-refactorings").innerText = report.refactoring_recommendations.length;
  document.getElementById("refactor-count-badge").innerText = `${report.refactoring_recommendations.length} prioritized proposals`;

  // Update filter pill counts
  document.getElementById("count-sev-all").innerText = report.violations.length;
  document.getElementById("count-sev-crit").innerText = criticalCount;
  document.getElementById("count-sev-high").innerText = highCount;
  document.getElementById("count-sev-med").innerText = mediumCount;

  // Layer Chart
  if (layerChart && report.layer_distribution) {
    const labels = Object.keys(report.layer_distribution);
    const counts = Object.values(report.layer_distribution);
    layerChart.data.labels = labels.map(l => l.charAt(0).toUpperCase() + l.slice(1));
    layerChart.data.datasets[0].data = counts;
    layerChart.update();
  }

  // Render Violations
  renderViolationsList();

  // Render Refactorings
  renderRefactoringsList();

  lucide.createIcons();
}

function renderViolationsList() {
  if (!currentReport) return;
  const violContainer = document.getElementById("violations-container");
  violContainer.innerHTML = "";

  let list = currentReport.violations;

  // Filter by severity
  if (activeSeverityFilter !== "all") {
    list = list.filter(v => v.severity.toLowerCase() === activeSeverityFilter);
  }

  // Filter by search text
  if (searchFilterText) {
    list = list.filter(v => 
      v.file_path.toLowerCase().includes(searchFilterText) ||
      v.title.toLowerCase().includes(searchFilterText) ||
      v.description.toLowerCase().includes(searchFilterText)
    );
  }

  if (list.length === 0) {
    violContainer.innerHTML = `
      <div class="p-5 rounded-xl bg-gray-900/40 border border-gray-800 text-center text-xs text-emerald-400">
        ✔ No matching architectural violations found for this filter.
      </div>
    `;
    return;
  }

  list.forEach(v => {
    const card = document.createElement("div");
    card.className = "p-3.5 rounded-xl bg-gray-900/80 border border-gray-800 hover:border-gray-700 transition space-y-1.5 text-xs";
    
    let badgeClass = "bg-rose-500/20 text-rose-300 border-rose-500/30";
    if (v.severity === "high") badgeClass = "bg-orange-500/20 text-orange-300 border-orange-500/30";
    if (v.severity === "medium") badgeClass = "bg-amber-500/20 text-amber-300 border-amber-500/30";
    if (v.severity === "low") badgeClass = "bg-blue-500/20 text-blue-300 border-blue-500/30";

    card.innerHTML = `
      <div class="flex items-center justify-between">
        <span class="px-2 py-0.5 rounded text-[10px] font-bold border uppercase ${badgeClass}">${v.severity}</span>
        <span class="text-gray-400 font-mono text-[11px] truncate max-w-sm" title="${v.file_path}">${v.file_path}</span>
      </div>
      <h4 class="font-bold text-white text-xs">${v.title}</h4>
      <p class="text-gray-400 leading-relaxed text-[11px]">${v.description}</p>
      <div class="pt-1.5 border-t border-gray-800/80 text-cyan-400 font-mono text-[11px]">
        ➜ Fix: ${v.suggested_fix}
      </div>
    `;
    violContainer.appendChild(card);
  });
}

function renderRefactoringsList() {
  const refContainer = document.getElementById("refactor-container");
  refContainer.innerHTML = "";

  if (!currentReport || currentReport.refactoring_recommendations.length === 0) {
    refContainer.innerHTML = `
      <div class="col-span-full p-4 rounded-xl bg-gray-900/40 border border-gray-800 text-center text-xs text-gray-400">
        ✔ No refactorings required.
      </div>
    `;
    return;
  }

  // Display top 10 prioritized refactorings
  currentReport.refactoring_recommendations.slice(0, 10).forEach(r => {
    const card = document.createElement("div");
    card.className = "p-4 rounded-xl bg-gray-900/80 border border-indigo-500/20 space-y-2 text-xs flex flex-col justify-between";
    card.innerHTML = `
      <div class="space-y-1">
        <div class="flex items-center justify-between">
          <span class="font-bold text-white text-xs">${r.title}</span>
          <span class="text-[10px] text-gray-400 font-mono">~${r.estimated_effort_mins} mins</span>
        </div>
        <p class="text-gray-400 text-[11px] truncate" title="${r.file_path}">${r.issue} in <span class="font-mono text-gray-300">${r.file_path}</span></p>
      </div>
      <pre class="p-2.5 rounded-lg bg-black/60 font-mono text-[11px] text-gray-300 overflow-x-auto border border-gray-800">${r.suggested_diff}</pre>
    `;
    refContainer.appendChild(card);
  });
}

// Generate formatted Markdown string of all issues
function generateIssuesMarkdown() {
  if (!currentReport) return "# No scan report available";

  const dateStr = new Date(currentReport.scanned_at).toISOString();
  let md = `# CodeProvenance Architecture Audit Report\n\n`;
  md += `- **Project Root:** \`${currentReport.root_path}\`\n`;
  md += `- **Date:** ${dateStr}\n`;
  md += `- **Compliance Score:** **${currentReport.compliance_score_pct}%** (${currentReport.drift_status})\n`;
  md += `- **Files Scanned:** ${currentReport.total_files} files (${currentReport.total_loc.toLocaleString()} LOC)\n`;
  md += `- **Total Violations:** ${currentReport.violations.length}\n\n`;

  md += `## Architectural Boundary Violations\n\n`;
  if (currentReport.violations.length === 0) {
    md += `*✔ No architectural violations detected! Codebase is in full compliance.*\n\n`;
  } else {
    md += `| # | Severity | Rule ID | File Path | Issue | Suggested Fix |\n`;
    md += `|---|---|---|---|---|---|\n`;
    currentReport.violations.forEach((v, idx) => {
      const cleanDesc = v.description.replace(/\|/g, "\\|").replace(/\n/g, " ");
      const cleanFix = v.suggested_fix.replace(/\|/g, "\\|").replace(/\n/g, " ");
      md += `| ${idx + 1} | **${v.severity.toUpperCase()}** | \`${v.rule_id}\` | \`${v.file_path}\` | ${cleanDesc} | ${cleanFix} |\n`;
    });
    md += `\n`;
  }

  md += `## Prioritized Refactoring Proposals\n\n`;
  if (currentReport.refactoring_recommendations.length === 0) {
    md += `*✔ No refactoring actions required.*\n`;
  } else {
    currentReport.refactoring_recommendations.forEach((r, idx) => {
      md += `### ${idx + 1}. ${r.title} (~${r.estimated_effort_mins} mins)\n`;
      md += `- **File:** \`${r.file_path}\`\n`;
      md += `- **Issue:** ${r.issue}\n\n`;
      md += `\`\`\`diff\n${r.suggested_diff}\n\`\`\`\n\n`;
    });
  }

  return md;
}

// Copy all issues to clipboard
async function copyAllIssuesMarkdown() {
  const md = generateIssuesMarkdown();
  const btnText = document.getElementById("copy-btn-text");

  try {
    await navigator.clipboard.writeText(md);
    if (btnText) {
      btnText.innerText = "✔ Copied!";
      setTimeout(() => {
        btnText.innerText = "Copy All";
      }, 2000);
    }
  } catch (err) {
    // Fallback prompt
    const textarea = document.createElement("textarea");
    textarea.value = md;
    document.body.appendChild(textarea);
    textarea.select();
    document.execCommand("copy");
    document.body.removeChild(textarea);
    if (btnText) {
      btnText.innerText = "✔ Copied!";
      setTimeout(() => {
        btnText.innerText = "Copy All";
      }, 2000);
    }
  }
}

// Download markdown file
function exportIssuesAsMarkdown() {
  const md = generateIssuesMarkdown();
  const blob = new Blob([md], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `architecture-audit-${new Date().toISOString().slice(0, 10)}.md`;
  a.click();
  URL.revokeObjectURL(url);
}
