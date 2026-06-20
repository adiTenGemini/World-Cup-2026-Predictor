const schedule = window.MATCH_SCHEDULE;
const scheduleFlags = window.SCHEDULE_FLAGS || {};

const stageFilter = document.querySelector("#stage-filter");
const groupFilter = document.querySelector("#group-filter");
const venueFilter = document.querySelector("#venue-filter");
const searchInput = document.querySelector("#schedule-search");
const clearButton = document.querySelector("#clear-schedule-filters");
const scheduleBody = document.querySelector("#schedule-body");
const scheduleCount = document.querySelector("#schedule-count");
const userTimeZone = Intl.DateTimeFormat().resolvedOptions().timeZone || "Local time";

function uniqueValues(key) {
  return [...new Set(schedule.map((match) => match[key]).filter(Boolean))];
}

function addOptions(select, values, labeler = (value) => value) {
  values.forEach((value) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = labeler(value);
    select.appendChild(option);
  });
}

function easternKickoffToDate(match) {
  const [year, month, day] = match.date.split("-").map(Number);
  const [hour, minute] = match.time.replace(" ET", "").split(":").map(Number);
  return new Date(Date.UTC(year, month - 1, day, hour + 4, minute));
}

function formatLocalDate(match) {
  return new Intl.DateTimeFormat("en", {
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  }).format(easternKickoffToDate(match));
}

function formatLocalTime(match) {
  return new Intl.DateTimeFormat("en", {
    hour: "numeric",
    minute: "2-digit",
    timeZoneName: "short",
  }).format(easternKickoffToDate(match));
}

function filteredSchedule() {
  const stage = stageFilter.value;
  const group = groupFilter.value;
  const venue = venueFilter.value;
  const query = searchInput.value.trim().toLowerCase();

  return schedule.filter((match) => {
    const matchesStage = !stage || match.stage === stage;
    const matchesGroup = !group || match.group === group;
    const matchesVenue = !venue || match.venue === venue;
    const haystack = [
      match.match,
      match.stage,
      match.group,
      match.date,
      match.time,
      match.team1,
      match.team2,
      match.venue,
    ]
      .join(" ")
      .toLowerCase();
    return matchesStage && matchesGroup && matchesVenue && (!query || haystack.includes(query));
  });
}

function renderSchedule() {
  const matches = filteredSchedule();
  scheduleCount.textContent = `${matches.length} of ${schedule.length} matches - ${userTimeZone}`;

  if (!matches.length) {
    scheduleBody.innerHTML = `
      <tr>
        <td class="empty-schedule" colspan="7">No matches found.</td>
      </tr>
    `;
    return;
  }

  scheduleBody.innerHTML = matches
    .map(
      (match) => `
        <tr>
          <td><span class="match-number">${match.match}</span></td>
          <td>${formatLocalDate(match)}</td>
          <td>${formatLocalTime(match)}</td>
          <td>
            <span class="stage-pill">${match.stage}${match.group ? ` &middot; Group ${match.group}` : ""}</span>
          </td>
          <td class="fixture-cell">
            ${renderFixtureTeam(match.team1)}
            <span>vs</span>
            ${renderFixtureTeam(match.team2)}
          </td>
          <td>${renderMatchResult(match)}</td>
          <td>${match.venue}</td>
        </tr>
      `,
    )
    .join("");
}

function renderMatchResult(match) {
  if (match.result_source !== "actual") {
    return `<span class="result-source result-source--pending">Scheduled</span>`;
  }
  return `
    <span class="schedule-result">
      <strong>${match.actual_team1_goals}-${match.actual_team2_goals}</strong>
      <span class="result-source result-source--actual">Final</span>
    </span>
  `;
}

function renderFixtureTeam(name) {
  const flagUrl = scheduleFlags[name];
  if (!flagUrl) {
    return `<strong>${name}</strong>`;
  }
  return `
    <strong class="fixture-team">
      <img class="country-flag" src="${flagUrl}" alt="" loading="lazy" />
      <span>${name}</span>
    </strong>
  `;
}

function clearFilters() {
  stageFilter.value = "";
  groupFilter.value = "";
  venueFilter.value = "";
  searchInput.value = "";
  renderSchedule();
}

addOptions(stageFilter, uniqueValues("stage"));
addOptions(groupFilter, uniqueValues("group").sort(), (group) => `Group ${group}`);
addOptions(venueFilter, uniqueValues("venue").sort());

[stageFilter, groupFilter, venueFilter, searchInput].forEach((control) => {
  control.addEventListener("input", renderSchedule);
});
clearButton.addEventListener("click", clearFilters);

renderSchedule();
