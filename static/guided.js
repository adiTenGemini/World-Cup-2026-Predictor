const groups = window.WORLD_CUP_GROUPS;
const matchSchedule = window.MATCH_SCHEDULE || [];
const scheduleByMatch = new Map(matchSchedule.map((match) => [match.match, match]));
const groupState = new Map(groups.map((group) => [group.id, [...group.teams]]));
let thirdPlaceOrder = [];
const winners = {
  round32: Array(16).fill(null),
  round16: Array(8).fill(null),
  quarterfinal: Array(4).fill(null),
  semifinal: Array(2).fill(null),
  final: Array(1).fill(null),
};

const steps = [
  { key: "groups", label: "Group Stage", title: "Rank all 12 groups", kicker: "48 teams" },
  { key: "thirds", label: "Best Thirds", title: "Choose the eight best third-place teams", kicker: "12 into 8" },
  { key: "round32", label: "Round of 32", title: "Pick every Round of 32 winner", kicker: "32 teams" },
  { key: "round16", label: "Round of 16", title: "Pick every Round of 16 winner", kicker: "16 teams" },
  { key: "quarterfinal", label: "Quarter-finals", title: "Pick the semi-finalists", kicker: "8 teams" },
  { key: "semifinal", label: "Semi-finals", title: "Pick the finalists", kicker: "4 teams" },
  { key: "final", label: "Final", title: "Crown your champion", kicker: "2 teams" },
  { key: "champion", label: "Champion", title: "Your 2026 winner", kicker: "Prediction complete" },
];

let currentStep = 0;

const stepperList = document.querySelector("#stepper-list");
const guidedKicker = document.querySelector("#guided-kicker");
const guidedHeading = document.querySelector("#guided-heading");
const guidedContent = document.querySelector("#guided-content");
const stepMessage = document.querySelector("#step-message");
const backStep = document.querySelector("#back-step");
const nextStep = document.querySelector("#next-step");
const guidedReset = document.querySelector("#guided-reset");
const guidedSimulate = document.querySelector("#guided-simulate");
const guidedExportCsv = document.querySelector("#guided-export-csv");
const teamAliases = {
  "Bosnia & Herzegovina": "Bosnia and Herzegovina",
  "Cape Verde": "Cabo Verde",
  "Czech Republic": "Czechia",
  "DR Congo": "Congo DR",
  Iran: "IR Iran",
  "Ivory Coast": "Cote d'Ivoire",
  "South Korea": "Korea Republic",
  Turkey: "Turkiye",
  "United States": "USA",
};
const teamsByName = new Map();

groups.forEach((group) => {
  group.teams.forEach((team) => {
    teamsByName.set(team.name, team);
  });
});

Object.entries(teamAliases).forEach(([alias, canonical]) => {
  if (teamsByName.has(canonical)) {
    teamsByName.set(alias, teamsByName.get(canonical));
  }
});

function teamId(team) {
  return team.code;
}

function renderTeam(team) {
  if (!team) return `<span class="team"><span>-</span><span>Awaiting winner</span></span>`;
  return `
    <span class="team">
      <img class="country-flag" src="${team.flag_url}" alt="" loading="lazy" />
      <span>${team.name}</span>
    </span>
    <span class="seed-tag">${team.seed || team.code}</span>
  `;
}

function winProbability(team, opponent) {
  if (!team || !opponent) return null;
  return 1 / (1 + Math.pow(10, (opponent.rating - team.rating) / 400));
}

function predictedWinner(team, opponent) {
  if (!team) return opponent;
  if (!opponent) return team;
  return winProbability(team, opponent) >= 0.5 ? team : opponent;
}

function simulateGroup(group) {
  const standings = [...group.teams]
    .map((team) => ({
      team,
      score: group.teams.reduce((total, opponent) => {
        if (opponent.code === team.code) return total;
        return total + winProbability(team, opponent);
      }, 0),
    }))
    .sort((a, b) => b.score - a.score)
    .map((item) => item.team);
  groupState.set(group.id, standings);
}

function simulateThirdPlaceOrder() {
  thirdPlaceOrder = getQualifiers()
    .map((item) => item.third)
    .map((team) => ({
      team,
      score: team.rating,
    }))
    .sort((a, b) => b.score - a.score)
    .map((item) => item.team);
}

function simulateAll() {
  groups.forEach(simulateGroup);
  thirdPlaceOrder = [];
  simulateThirdPlaceOrder();
  simulateKnockout();
  currentStep = steps.length - 1;
  render();
}

function simulateKnockout() {
  getThirdPlaceTeams();
  resetWinners();

  ["round32", "round16", "quarterfinal", "semifinal", "final"].forEach((roundKey) => {
    const round = getBracketRounds()[roundKey];
    round.matches.forEach((match, index) => {
      winners[roundKey][index] = predictedWinner(match[0], match[1]);
    });
  });
}

function renderProbability(team, opponent) {
  const probability = winProbability(team, opponent);
  if (probability === null) return "";
  return `<span class="probability">${Math.round(probability * 100)}%</span>`;
}

function predictedScore(team, opponent, winner = null) {
  if (!team || !opponent) {
    return { teamGoals: "", opponentGoals: "", result: "" };
  }

  const teamExpectedGoals = Math.max(0.15, 1.35 + (team.rating - opponent.rating) / 520);
  const opponentExpectedGoals = Math.max(0.15, 1.35 - (team.rating - opponent.rating) / 520);
  let teamGoals = Math.max(0, Math.round(teamExpectedGoals));
  let opponentGoals = Math.max(0, Math.round(opponentExpectedGoals));

  if (!winner) {
    return {
      teamGoals,
      opponentGoals,
      result: `${teamGoals}-${opponentGoals}`,
    };
  }

  if (teamGoals === opponentGoals) {
    if (winner.code === team.code) teamGoals += 1;
    if (winner.code === opponent.code) opponentGoals += 1;
  } else if (winner.code === team.code && teamGoals < opponentGoals) {
    teamGoals = opponentGoals + 1;
  } else if (winner.code === opponent.code && opponentGoals < teamGoals) {
    opponentGoals = teamGoals + 1;
  }

  return {
    teamGoals,
    opponentGoals,
    result: `${teamGoals}-${opponentGoals}`,
  };
}

function csvEscape(value) {
  const text = value === null || value === undefined ? "" : String(value);
  if (/[",\r\n]/.test(text)) return `"${text.replaceAll('"', '""')}"`;
  return text;
}

function matchOutcome(team, opponent, score, selectedWinner = null) {
  if (selectedWinner) return selectedWinner.name;
  if (score.teamGoals === "" || score.opponentGoals === "") return "";
  if (score.teamGoals > score.opponentGoals) return team.name;
  if (score.teamGoals < score.opponentGoals) return opponent.name;
  return "Draw";
}

function buildMatchRow({ matchNumber, stage, team, opponent, selectedWinner = null }) {
  const schedule = scheduleByMatch.get(matchNumber) || {};
  const probability = winProbability(team, opponent);
  const score = predictedScore(team, opponent, selectedWinner);
  const outcome = matchOutcome(team, opponent, score, selectedWinner);
  const winnerProbability =
    probability === null || !selectedWinner
      ? ""
      : selectedWinner.code === team.code
        ? probability
        : 1 - probability;

  return {
    match_number: matchNumber,
    stage: stage || schedule.stage || "",
    match_date: schedule.date || "",
    match_time: schedule.time || "",
    venue: schedule.venue || "",
    team_1: team?.name || schedule.team1 || "",
    team_2: opponent?.name || schedule.team2 || "",
    team_1_win_probability: probability === null ? "" : `${(probability * 100).toFixed(1)}%`,
    team_2_win_probability: probability === null ? "" : `${((1 - probability) * 100).toFixed(1)}%`,
    predicted_winner: outcome,
    winner_probability: winnerProbability === "" ? "" : `${(winnerProbability * 100).toFixed(1)}%`,
    result: score.result,
    team_1_goals: score.teamGoals,
    team_2_goals: score.opponentGoals,
  };
}

function buildGroupStageExportRows() {
  return matchSchedule
    .filter((match) => match.match <= 72)
    .map((match) =>
      buildMatchRow({
        matchNumber: match.match,
        stage: match.stage,
        team: teamsByName.get(match.team1),
        opponent: teamsByName.get(match.team2),
      }),
    );
}

function buildKnockoutExportRows() {
  const rounds = getBracketRounds();
  const rows = ["round32", "round16", "quarterfinal", "semifinal", "final"].flatMap((roundKey) =>
    rounds[roundKey].matches.map((match, matchIndex) =>
      buildMatchRow({
        matchNumber: rounds[roundKey].matchStart + matchIndex,
        stage: rounds[roundKey].title,
        team: match[0],
        opponent: match[1],
        selectedWinner: winners[roundKey][matchIndex] || null,
      }),
    ),
  );
  const thirdPlaceTeams = rounds.semifinal.matches.map((match, index) => {
    const winner = winners.semifinal[index];
    return match.find((team) => team && team.code !== winner?.code) || null;
  });
  rows.push(
    buildMatchRow({
      matchNumber: 103,
      stage: "Third Place",
      team: thirdPlaceTeams[0],
      opponent: thirdPlaceTeams[1],
      selectedWinner:
        thirdPlaceTeams[0] && thirdPlaceTeams[1]
          ? predictedWinner(thirdPlaceTeams[0], thirdPlaceTeams[1])
          : null,
    }),
  );
  return rows.sort((a, b) => a.match_number - b.match_number);
}

function buildExportRows() {
  return [...buildGroupStageExportRows(), ...buildKnockoutExportRows()];
}

function downloadCsv(rows) {
  const columns = [
    "match_number",
    "stage",
    "match_date",
    "match_time",
    "venue",
    "team_1",
    "team_2",
    "team_1_win_probability",
    "team_2_win_probability",
    "predicted_winner",
    "winner_probability",
    "result",
    "team_1_goals",
    "team_2_goals",
  ];
  const csv = [
    columns.join(","),
    ...rows.map((row) => columns.map((column) => csvEscape(row[column])).join(",")),
  ].join("\r\n");
  const blob = new Blob([csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `world-cup-2026-simulation-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function exportCurrentSimulation() {
  downloadCsv(buildExportRows());
}

function getQualifiers() {
  return groups.map((group) => {
    const standings = groupState.get(group.id);
    return {
      group: group.id,
      winner: { ...standings[0], seed: `${group.id}1` },
      runnerUp: { ...standings[1], seed: `${group.id}2` },
      third: { ...standings[2], seed: `${group.id}3` },
      fourth: { ...standings[3], seed: `${group.id}4` },
    };
  });
}

function getThirdPlaceTeams() {
  const currentThirds = getQualifiers().map((item) => item.third);
  const currentCodes = new Set(currentThirds.map((team) => team.code));
  const keptOrder = thirdPlaceOrder.filter((team) => currentCodes.has(team.code));
  const missing = currentThirds.filter((team) => !keptOrder.some((item) => item.code === team.code));
  thirdPlaceOrder = [...keptOrder, ...missing];
  return thirdPlaceOrder;
}

function getBestThirds() {
  return getThirdPlaceTeams().slice(0, 8);
}

function getBracketRounds() {
  const qualifiers = getQualifiers();
  const groupWinners = qualifiers.map((item) => item.winner);
  const runnersUp = qualifiers.map((item) => item.runnerUp);
  const thirdPlaceAssignments = getThirdPlaceAssignments(getBestThirds());

  const round32Matches = [
    [runnersUp[0], runnersUp[1]],
    [groupWinners[4], thirdPlaceAssignments.m74],
    [groupWinners[5], runnersUp[2]],
    [groupWinners[2], runnersUp[5]],
    [groupWinners[8], thirdPlaceAssignments.m77],
    [runnersUp[4], runnersUp[8]],
    [groupWinners[0], thirdPlaceAssignments.m79],
    [groupWinners[11], thirdPlaceAssignments.m80],
    [groupWinners[3], thirdPlaceAssignments.m81],
    [groupWinners[6], thirdPlaceAssignments.m82],
    [runnersUp[10], runnersUp[11]],
    [groupWinners[7], runnersUp[9]],
    [groupWinners[1], thirdPlaceAssignments.m85],
    [groupWinners[9], runnersUp[7]],
    [groupWinners[10], thirdPlaceAssignments.m87],
    [runnersUp[3], runnersUp[6]],
  ];

  const round16Matches = [
    [winners.round32[1], winners.round32[4]],
    [winners.round32[0], winners.round32[2]],
    [winners.round32[3], winners.round32[5]],
    [winners.round32[6], winners.round32[7]],
    [winners.round32[10], winners.round32[11]],
    [winners.round32[8], winners.round32[9]],
    [winners.round32[13], winners.round32[15]],
    [winners.round32[12], winners.round32[14]],
  ];
  const quarterfinalMatches = [
    [winners.round16[0], winners.round16[1]],
    [winners.round16[4], winners.round16[5]],
    [winners.round16[2], winners.round16[3]],
    [winners.round16[6], winners.round16[7]],
  ];
  const semifinalMatches = pairWinners("quarterfinal", 2);
  const finalMatches = pairWinners("semifinal", 1);

  return {
    round32: { title: "Round of 32", matchStart: 73, matches: round32Matches },
    round16: { title: "Round of 16", matchStart: 89, matches: round16Matches },
    quarterfinal: { title: "Quarter-finals", matchStart: 97, matches: quarterfinalMatches },
    semifinal: { title: "Semi-finals", matchStart: 101, matches: semifinalMatches },
    final: { title: "Final", matchStart: 104, matches: finalMatches },
  };
}

function getThirdPlaceAssignments(bestThirds) {
  const slots = [
    { key: "m74", allowed: ["A", "B", "C", "D", "F"] },
    { key: "m77", allowed: ["C", "D", "F", "G", "H"] },
    { key: "m79", allowed: ["C", "E", "F", "H", "I"] },
    { key: "m80", allowed: ["E", "H", "I", "J", "K"] },
    { key: "m81", allowed: ["B", "E", "F", "I", "J"] },
    { key: "m82", allowed: ["A", "E", "H", "I", "J"] },
    { key: "m85", allowed: ["E", "F", "G", "I", "J"] },
    { key: "m87", allowed: ["D", "E", "I", "J", "L"] },
  ];
  const ranked = bestThirds.map((team, index) => ({ ...team, thirdRank: index }));

  function search(index, used, result) {
    if (index === slots.length) return result;
    const slot = slots[index];
    const candidates = ranked.filter((team) => slot.allowed.includes(team.seed[0]) && !used.has(team.code));
    for (const candidate of candidates) {
      const nextUsed = new Set(used);
      nextUsed.add(candidate.code);
      const solved = search(index + 1, nextUsed, { ...result, [slot.key]: candidate });
      if (solved) return solved;
    }
    return null;
  }

  return search(0, new Set(), {}) || {};
}

function pairWinners(roundKey, count) {
  return Array.from({ length: count }, (_, index) => [
    winners[roundKey][index * 2],
    winners[roundKey][index * 2 + 1],
  ]);
}

function renderStepper() {
  stepperList.innerHTML = steps
    .map(
      (step, index) => `
        <li class="${index === currentStep ? "is-current" : ""} ${index < currentStep ? "is-done" : ""}">
          <span>${index + 1}</span>
          <button type="button" data-step="${index}" ${index > maxReachableStep() ? "disabled" : ""}>
            ${step.label}
          </button>
        </li>
      `,
    )
    .join("");

  stepperList.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      currentStep = Number(button.dataset.step);
      render();
    });
  });
}

function maxReachableStep() {
  let max = 0;
  for (let index = 0; index < steps.length - 1; index += 1) {
    if (!isStepComplete(index)) return max;
    max = index + 1;
  }
  return steps.length - 1;
}

function render() {
  const step = steps[currentStep];
  guidedKicker.textContent = step.kicker;
  guidedHeading.textContent = step.title;
  guidedContent.innerHTML = "";

  if (step.key === "groups") renderGroupsStep();
  if (step.key === "thirds") renderThirdsStep();
  if (["round32", "round16", "quarterfinal", "semifinal", "final"].includes(step.key)) {
    renderRoundStep(step.key);
  }
  if (step.key === "champion") renderChampionStep();

  renderStepper();
  updateActions();
}

function renderGroupsStep() {
  guidedContent.innerHTML = `<div class="groups-grid">${groups.map(renderGroupCard).join("")}</div>`;
  bindSortableLists(".team-list", handleGroupDrop);
}

function renderGroupCard(group) {
  const standings = groupState.get(group.id);
  return `
    <article class="group-card">
      <div class="group-card__head">
        <h3>Group ${group.id}</h3>
        <span class="status-pill">${standings[0].code} &middot; ${standings[1].code}</span>
      </div>
      <div class="team-list" data-group="${group.id}" aria-label="Group ${group.id} standings">
        ${standings.map((team, index) => renderDraggableTeam(team, index + 1, group.id)).join("")}
      </div>
    </article>
  `;
}

function renderDraggableTeam(team, rank, groupId = "") {
  return `
    <div class="team-row" draggable="true" data-team="${teamId(team)}" data-group="${groupId}">
      <span class="rank">${rank}</span>
      ${renderTeam(team)}
    </div>
  `;
}

function renderThirdsStep() {
  const thirdPlaceTeams = getThirdPlaceTeams();
  guidedContent.innerHTML = `
    <div class="thirds-layout">
      <div>
        <h3>Third-place ranking</h3>
        <div class="team-list thirds-list" data-list="thirds">
          ${thirdPlaceTeams.map((team, index) => renderDraggableTeam(team, index + 1)).join("")}
        </div>
      </div>
      <div class="elimination-summary">
        <h3>Advancing</h3>
        ${thirdPlaceTeams.slice(0, 8).map((team) => `<div class="summary-row">${renderTeam(team)}</div>`).join("")}
        <h3>Eliminated</h3>
        ${thirdPlaceTeams.slice(8).map((team) => `<div class="summary-row is-out">${renderTeam(team)}</div>`).join("")}
      </div>
    </div>
  `;
  bindSortableLists(".thirds-list", handleThirdsDrop);
}

function renderRoundStep(roundKey) {
  const round = getBracketRounds()[roundKey];
  guidedContent.innerHTML = `
    <div class="round guided-round">
      ${round.matches
        .map((match, index) => renderMatch(roundKey, round.title, round.matchStart, match, index))
        .join("")}
    </div>
  `;
  bindWinnerButtons();
}

function renderMatch(roundKey, title, matchStart, match, matchIndex) {
  return `
    <article class="match">
      <div class="match__title">${title} &middot; Match ${matchStart + matchIndex}</div>
      ${match
        .map((team, slotIndex) => {
          const opponent = match[slotIndex === 0 ? 1 : 0];
          const selected = winners[roundKey][matchIndex]?.code === team?.code;
          return `
            <button
              class="slot ${selected ? "is-winner" : ""}"
              type="button"
              data-round="${roundKey}"
              data-match="${matchIndex}"
              data-slot="${slotIndex}"
              ${team ? "" : "disabled"}
            >
              ${renderTeam(team)}
              ${renderProbability(team, opponent)}
            </button>
          `;
        })
        .join("")}
    </article>
  `;
}

function renderChampionStep() {
  guidedContent.innerHTML = `
    <div class="champion-card guided-champion">
      <h3>Champion</h3>
      <div class="champion-name">${renderTeam(winners.final[0])}</div>
    </div>
  `;
}

function bindSortableLists(selector, onDrop) {
  document.querySelectorAll(`${selector} .team-row`).forEach((row) => {
    row.addEventListener("dragstart", (event) => {
      row.classList.add("is-dragging");
      event.dataTransfer.setData("text/plain", row.dataset.team);
    });
    row.addEventListener("dragend", () => row.classList.remove("is-dragging"));
  });

  document.querySelectorAll(selector).forEach((list) => {
    list.addEventListener("dragover", (event) => {
      event.preventDefault();
      const dragged = document.querySelector(".is-dragging");
      if (!dragged) return;
      if (list.dataset.group && dragged.dataset.group !== list.dataset.group) return;
      const afterElement = getDragAfterElement(list, event.clientY);
      if (afterElement == null) {
        list.appendChild(dragged);
      } else {
        list.insertBefore(dragged, afterElement);
      }
    });
    list.addEventListener("drop", () => onDrop(list));
  });
}

function handleGroupDrop(list) {
  const group = groups.find((item) => item.id === list.dataset.group);
  const order = [...list.querySelectorAll(".team-row")].map((row) => row.dataset.team);
  groupState.set(
    group.id,
    order.map((code) => group.teams.find((team) => team.code === code)),
  );
  resetWinners();
  render();
}

function handleThirdsDrop(list) {
  const currentThirds = getThirdPlaceTeams();
  const order = [...list.querySelectorAll(".team-row")].map((row) => row.dataset.team);
  thirdPlaceOrder = order.map((code) => currentThirds.find((team) => team.code === code));
  resetWinners();
  render();
}

function getDragAfterElement(container, y) {
  const draggableElements = [...container.querySelectorAll(".team-row:not(.is-dragging)")];
  return draggableElements.reduce(
    (closest, child) => {
      const box = child.getBoundingClientRect();
      const offset = y - box.top - box.height / 2;
      if (offset < 0 && offset > closest.offset) return { offset, element: child };
      return closest;
    },
    { offset: Number.NEGATIVE_INFINITY, element: null },
  ).element;
}

function bindWinnerButtons() {
  document.querySelectorAll(".slot").forEach((slot) => {
    slot.addEventListener("click", () => {
      const round = slot.dataset.round;
      const matchIndex = Number(slot.dataset.match);
      const slotIndex = Number(slot.dataset.slot);
      const team = getBracketRounds()[round].matches[matchIndex][slotIndex];
      winners[round][matchIndex] = team;
      clearDependentWinners(round);
      render();
    });
  });
}

function isStepComplete(index) {
  const key = steps[index].key;
  if (key === "groups" || key === "thirds") return true;
  if (key === "champion") return true;
  return winners[key].every(Boolean);
}

function updateActions() {
  backStep.disabled = currentStep === 0;
  const complete = isStepComplete(currentStep);
  nextStep.disabled = currentStep === steps.length - 1 || !complete;
  stepMessage.textContent = complete ? "" : "Select a winner for every match to continue.";
  nextStep.textContent = currentStep === steps.length - 2 ? "Finish" : "Next";
}

function clearDependentWinners(round) {
  const order = ["round32", "round16", "quarterfinal", "semifinal", "final"];
  const start = order.indexOf(round) + 1;
  order.slice(start).forEach((key) => {
    winners[key] = winners[key].map(() => null);
  });
}

function resetWinners() {
  Object.keys(winners).forEach((round) => {
    winners[round] = winners[round].map(() => null);
  });
}

backStep.addEventListener("click", () => {
  currentStep = Math.max(0, currentStep - 1);
  render();
});

nextStep.addEventListener("click", () => {
  if (!isStepComplete(currentStep)) return;
  currentStep = Math.min(steps.length - 1, currentStep + 1);
  render();
});

guidedReset.addEventListener("click", () => {
  groups.forEach((group) => groupState.set(group.id, [...group.teams]));
  thirdPlaceOrder = [];
  resetWinners();
  currentStep = 0;
  render();
});

guidedSimulate.addEventListener("click", simulateAll);
guidedExportCsv.addEventListener("click", exportCurrentSimulation);
render();
