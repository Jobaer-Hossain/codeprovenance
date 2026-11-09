/**
 * CodeProvenance Web Dashboard Frontend Logic
 */

let layerChart = null;

document.addEventListener("DOMContentLoaded", () => {
  lucide.createIcons();
  initLayerChart();
  triggerScan();

  document.getElementById("btn-scan").addEventListener("click", () => {
    const customPath = document.getElementById("target-dir-input").value.trim();
    triggerScan(customPath);
  });
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

async function triggerScan(targetPath = "") {
  try {
    const url = targetPath ? `/api/scan?target_path=${encodeURIComponent(targetPath)}` : "/api/scan";
    const res = await fetch(url);
    if (!res.ok) throw new Error("Scan failed");
    const data = await res.json();
    renderReport(data);
  } catch (err) {
    console.error("Scan error:", err);
  }
}

function renderReport(report) {
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
  document.getElementById("kpi-critical").innerText = `${criticalCount} critical breaches`;
  document.getElementById("kpi-refactorings").innerText = report.refactoring_recommendations.length;
  document.getElementById("violations-count-badge").innerText = `${report.violations.length} Issues`;

  // Layer Chart
  if (layerChart && report.layer_distribution) {
    const labels = Object.keys(report.layer_distribution);
    const counts = Object.values(report.layer_distribution);
    layerChart.data.labels = labels.map(l => l.charAt(0).toUpperCase() + l.slice(1));
    layerChart.data.datasets[0].data = counts;
    layerChart.update();
  }

  // Violations List
  const violContainer = document.getElementById("violations-container");
  violContainer.innerHTML = "";
  if (report.violations.length === 0) {
    violContainer.innerHTML = `
      <div class="p-4 rounded-xl bg-gray-900/40 border border-gray-800 text-center text-xs text-emerald-400">
        ✔ Perfect architectural compliance! No layer boundary violations detected.
      </div>
    `;
  } else {
    report.violations.forEach(v => {
      const card = document.createElement("div");
      card.className = "p-3.5 rounded-xl bg-gray-900/70 border border-gray-800 hover:border-gray-700 transition space-y-1.5 text-xs";
      
      let badgeClass = "bg-rose-500/20 text-rose-300 border-rose-500/30";
      if (v.severity === "medium") badgeClass = "bg-amber-500/20 text-amber-300 border-amber-500/30";
      if (v.severity === "low") badgeClass = "bg-blue-500/20 text-blue-300 border-blue-500/30";

      card.innerHTML = `
        <div class="flex items-center justify-between">
          <span class="px-2 py-0.5 rounded text-[10px] font-bold border ${badgeClass}">${v.severity.toUpperCase()}</span>
          <span class="text-gray-400 font-mono text-[11px]">${v.file_path}</span>
        </div>
        <h4 class="font-bold text-white">${v.title}</h4>
        <p class="text-gray-400 leading-relaxed">${v.description}</p>
        <div class="pt-1.5 border-t border-gray-800 text-emerald-400 font-mono text-[11px]">
          ➜ Fix: ${v.suggested_fix}
        </div>
      `;
      violContainer.appendChild(card);
    });
  }

  // Refactoring Recommendations
  const refContainer = document.getElementById("refactor-container");
  refContainer.innerHTML = "";
  report.refactoring_recommendations.forEach(r => {
    const card = document.createElement("div");
    card.className = "p-4 rounded-xl bg-gray-900/80 border border-indigo-500/20 space-y-2 text-xs";
    card.innerHTML = `
      <div class="flex items-center justify-between">
        <span class="font-bold text-white text-xs">${r.title}</span>
        <span class="text-[10px] text-gray-400 font-mono">~${r.estimated_effort_mins} mins</span>
      </div>
      <p class="text-gray-400 text-[11px]">${r.issue} in <span class="font-mono text-gray-300">${r.file_path}</span></p>
      <pre class="p-2.5 rounded-lg bg-black/60 font-mono text-[11px] text-gray-300 overflow-x-auto border border-gray-800">${r.suggested_diff}</pre>
    `;
    refContainer.appendChild(card);
  });

  lucide.createIcons();
}
