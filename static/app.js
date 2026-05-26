const groups = window.WORLD_CUP_GROUPS;
const groupState = new Map(groups.map((group) => [group.id, [...group.teams]]));
const winners = {
  round32: Array(16).fill(null),
  round16: Array(8).fill(null),
  quarterfinal: Array(4).fill(null),
  semifinal: Array(2).fill(null),
  final: Array(1).fill(null),
};

const groupsGrid = document.querySelector("#groups-grid");
const bracketView = document.querySelector("#bracket-view");
const resetButton = document.querySelector("#reset-button");

function teamId(team) {
  return team.code;
}

function getQualifiers() {
  return groups.map((group) => {
    const standings = groupState.get(group.id);
    return {
      group: group.id,
      winner: { ...standings[0], seed: `${group.id}1` },
      runnerUp: { ...standings[1], seed: `${group.id}2` },
      third: { ...standings[2], seed: `${group.id}3` },
    };
  });
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

function renderProbability(team, opponent) {
  const probability = winProbability(team, opponent);
  if (probability === null) return "";
  return `<span class="probability">${Math.round(probability * 100)}%</span>`;
}

function renderGroups() {
  groupsGrid.innerHTML = groups
    .map((group) => {
      const standings = groupState.get(group.id);
      return `
        <article class="group-card">
          <div class="group-card__head">
            <h3>Group ${group.id}</h3>
            <span class="status-pill">${standings[0].code} &middot; ${standings[1].code}</span>
          </div>
          <div class="team-list" data-group="${group.id}" aria-label="Group ${group.id} standings">
            ${standings
              .map(
                (team, index) => `
                  <div class="team-row" draggable="true" data-team="${teamId(team)}" data-group="${group.id}">
                    <span class="rank">${index + 1}</span>
                    ${renderTeam(team)}
                  </div>
                `,
              )
              .join("")}
          </div>
        </article>
      `;
    })
    .join("");

  bindDragAndDrop();
}

function bindDragAndDrop() {
  document.querySelectorAll(".team-row").forEach((row) => {
    row.addEventListener("dragstart", (event) => {
      row.classList.add("is-dragging");
      event.dataTransfer.setData(
        "application/json",
        JSON.stringify({
          group: row.dataset.group,
          team: row.dataset.team,
        }),
      );
    });

    row.addEventListener("dragend", () => row.classList.remove("is-dragging"));
  });

  document.querySelectorAll(".team-list").forEach((list) => {
    list.addEventListener("dragover", (event) => {
      event.preventDefault();
      const dragged = document.querySelector(".is-dragging");
      const afterElement = getDragAfterElement(list, event.clientY);
      if (!dragged || dragged.dataset.group !== list.dataset.group) return;
      if (afterElement == null) {
        list.appendChild(dragged);
      } else {
        list.insertBefore(dragged, afterElement);
      }
    });

    list.addEventListener("drop", () => {
      const order = [...list.querySelectorAll(".team-row")].map((row) => row.dataset.team);
      const group = groups.find((item) => item.id === list.dataset.group);
      groupState.set(
        group.id,
        order.map((code) => group.teams.find((team) => team.code === code)),
      );
      resetWinners();
      renderGroups();
      renderBracket();
    });
  });
}

function getDragAfterElement(container, y) {
  const draggableElements = [...container.querySelectorAll(".team-row:not(.is-dragging)")];

  return draggableElements.reduce(
    (closest, child) => {
      const box = child.getBoundingClientRect();
      const offset = y - box.top - box.height / 2;
      if (offset < 0 && offset > closest.offset) {
        return { offset, element: child };
      }
      return closest;
    },
    { offset: Number.NEGATIVE_INFINITY, element: null },
  ).element;
}

function resetWinners() {
  Object.keys(winners).forEach((round) => {
    winners[round] = winners[round].map(() => null);
  });
}

function getBracketRounds() {
  const qualifiers = getQualifiers();
  const groupWinners = qualifiers.map((item) => item.winner);
  const runnersUp = qualifiers.map((item) => item.runnerUp);
  const thirdPlaceAssignments = getThirdPlaceAssignments(qualifiers.slice(0, 8).map((item) => item.third));

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

  const semifinalMatches = [
    [winners.quarterfinal[0], winners.quarterfinal[1]],
    [winners.quarterfinal[2], winners.quarterfinal[3]],
  ];

  const finalMatches = [[winners.semifinal[0], winners.semifinal[1]]];

  return [
    { key: "round32", title: "Round of 32", matchStart: 73, matches: round32Matches },
    { key: "round16", title: "Round of 16", matchStart: 89, matches: round16Matches },
    { key: "quarterfinal", title: "Quarter-finals", matchStart: 97, matches: quarterfinalMatches },
    { key: "semifinal", title: "Semi-finals", matchStart: 101, matches: semifinalMatches },
    { key: "final", title: "Final", matchStart: 104, matches: finalMatches },
  ];
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

function renderBracket() {
  const rounds = getBracketRounds();
  bracketView.innerHTML = `
    <div class="bracket-board">
      ${rounds.map(renderRound).join("")}
      <div class="bracket-column champion-column">
        <h3>Champion</h3>
        <div class="champion-card">
          <div class="champion-name">${renderTeam(winners.final[0])}</div>
        </div>
      </div>
    </div>
  `;

  document.querySelectorAll(".slot").forEach((slot) => {
    slot.addEventListener("click", () => {
      const round = slot.dataset.round;
      const matchIndex = Number(slot.dataset.match);
      const slotIndex = Number(slot.dataset.slot);
      const team = getBracketRounds().find((item) => item.key === round).matches[matchIndex][slotIndex];
      winners[round][matchIndex] = team;
      clearDependentWinners(round);
      renderBracket();
    });
  });
}

function renderRound(round) {
  return `
    <div class="bracket-column">
      <h3>${round.title}</h3>
      ${round.matches
        .map(
          (match, matchIndex) => `
            <article class="match">
              <div class="match__title">${round.title} &middot; Match ${
                round.matchStart + matchIndex
              }</div>
              ${match
                .map((team, slotIndex) => {
                  const opponent = match[slotIndex === 0 ? 1 : 0];
                  const selected = winners[round.key][matchIndex]?.code === team?.code;
                  return `
                    <button
                      class="slot ${selected ? "is-winner" : ""}"
                      type="button"
                      data-round="${round.key}"
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
          `,
        )
        .join("")}
    </div>
  `;
}

function clearDependentWinners(round) {
  const order = ["round32", "round16", "quarterfinal", "semifinal", "final"];
  const start = order.indexOf(round) + 1;
  order.slice(start).forEach((key) => {
    winners[key] = winners[key].map(() => null);
  });
}

resetButton.addEventListener("click", () => {
  groups.forEach((group) => groupState.set(group.id, [...group.teams]));
  resetWinners();
  renderGroups();
  renderBracket();
});

renderGroups();
renderBracket();
