const resultsSchedule = window.MATCH_SCHEDULE || [];
const resultsFlags = window.SCHEDULE_FLAGS || {};
const resultAliases = {
  "Bosnia & Herzegovina": "Bosnia and Herzegovina", "Cape Verde": "Cabo Verde",
  "Czech Republic": "Czechia", "DR Congo": "Congo DR", Iran: "IR Iran",
  "Ivory Coast": "Cote d'Ivoire", "South Korea": "Korea Republic",
  Turkey: "Turkiye", "United States": "USA",
};
const resultTeams = new Map();
window.WORLD_CUP_GROUPS.forEach((group) => group.teams.forEach((team) => resultTeams.set(team.name, team)));
Object.entries(resultAliases).forEach(([alias, canonical]) => resultTeams.set(alias, resultTeams.get(canonical)));

const stageControl = document.querySelector("#results-stage");
const groupControl = document.querySelector("#results-group");
const sourceControl = document.querySelector("#results-source");
const searchControl = document.querySelector("#results-search");
const resultsBody = document.querySelector("#results-body");
const resultsCount = document.querySelector("#results-count");
const refreshButton = document.querySelector("#refresh-results");
const refreshStatus = document.querySelector("#refresh-status");

function resultScore(match) {
  if (match.result_source === "actual") return { text: `${match.actual_team1_goals}-${match.actual_team2_goals}`, source: "actual" };
  const team = resultTeams.get(match.team1);
  const opponent = resultTeams.get(match.team2);
  if (!team || !opponent) return { text: "—", source: "pending" };
  const difference = team.rating - opponent.rating;
  const teamGoals = Math.max(0, Math.round(Math.max(0.15, 1.35 + difference / 520)));
  const opponentGoals = Math.max(0, Math.round(Math.max(0.15, 1.35 - difference / 520)));
  return { text: `${teamGoals}-${opponentGoals}`, source: "model" };
}

function fixtureTeam(name) {
  const flag = resultsFlags[name];
  return `<strong class="fixture-team">${flag ? `<img class="country-flag" src="${flag}" alt="" loading="lazy" />` : ""}<span>${name}</span></strong>`;
}

function localDate(match) {
  const [year, month, day] = match.date.split("-").map(Number);
  return new Intl.DateTimeFormat("en", { month: "short", day: "numeric", year: "numeric" }).format(new Date(year, month - 1, day));
}

function renderResults() {
  const query = searchControl.value.trim().toLowerCase();
  const rows = resultsSchedule.filter((match) => {
    const score = resultScore(match);
    const searchable = `${match.match} ${match.team1} ${match.team2} ${match.stage} ${match.venue}`.toLowerCase();
    return (!stageControl.value || match.stage === stageControl.value) &&
      (!groupControl.value || match.group === groupControl.value) &&
      (!sourceControl.value || score.source === sourceControl.value) && (!query || searchable.includes(query));
  });
  const actualCount = resultsSchedule.filter((match) => resultScore(match).source === "actual").length;
  resultsCount.textContent = `${rows.length} of ${resultsSchedule.length} fixtures · ${actualCount} final`;
  resultsBody.innerHTML = rows.length ? rows.map((match) => {
    const score = resultScore(match);
    const label = score.source === "actual" ? "Final" : score.source === "model" ? "Model" : "Pending";
    return `<tr><td><span class="match-number">${match.match}</span></td><td>${localDate(match)}</td><td><span class="stage-pill">${match.stage}${match.group ? ` · Group ${match.group}` : ""}</span></td><td class="fixture-cell">${fixtureTeam(match.team1)}<span>vs</span>${fixtureTeam(match.team2)}</td><td><strong class="result-score">${score.text}</strong></td><td><span class="result-source result-source--${score.source}">${label}</span></td></tr>`;
  }).join("") : `<tr><td class="empty-schedule" colspan="6">No results found.</td></tr>`;
}

function addResultOptions(control, values, label = (value) => value) {
  [...new Set(values.filter(Boolean))].sort().forEach((value) => {
    const option = document.createElement("option"); option.value = value; option.textContent = label(value); control.appendChild(option);
  });
}
addResultOptions(stageControl, resultsSchedule.map((match) => match.stage));
addResultOptions(groupControl, resultsSchedule.map((match) => match.group), (group) => `Group ${group}`);
[stageControl, groupControl, sourceControl, searchControl].forEach((control) => control.addEventListener("input", renderResults));
document.querySelector("#clear-results-filters").addEventListener("click", () => { stageControl.value = ""; groupControl.value = ""; sourceControl.value = ""; searchControl.value = ""; renderResults(); });
refreshButton.addEventListener("click", async () => {
  refreshButton.disabled = true;
  refreshButton.classList.add("is-refreshing");
  refreshStatus.className = "refresh-status";
  refreshStatus.textContent = "Checking FotMob…";
  try {
    const response = await fetch("/api/results/refresh", { method: "POST", headers: { Accept: "application/json" } });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "Results refresh failed.");
    resultsSchedule.splice(0, resultsSchedule.length, ...payload.schedule);
    renderResults();
    refreshStatus.classList.add("is-success");
    refreshStatus.textContent = payload.message;
  } catch (error) {
    refreshStatus.classList.add("is-error");
    refreshStatus.textContent = error.message;
  } finally {
    refreshButton.disabled = false;
    refreshButton.classList.remove("is-refreshing");
  }
});
renderResults();
