'use strict';
const FOOTBALL_API_BASE = 'https://api.football-data.org/v4';
const COMPETITION_CODE = 'WC';

async function fetchWithAuth(url, apiKey) {
  const res = await fetch(url, {
    headers: apiKey ? { 'X-Auth-Token': apiKey } : {}
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`football-data.org ${res.status}: ${text.substring(0, 200)}`);
  }
  return res.json();
}

// Geeft voor elk team de laatste 5 wedstrijdresultaten in het toernooi terug
async function getTeamForm(apiKey) {
  try {
    const data = await fetchWithAuth(
      `${FOOTBALL_API_BASE}/competitions/${COMPETITION_CODE}/matches?status=FINISHED`,
      apiKey
    );

    const teamMatches = {};

    for (const match of data.matches || []) {
      const home = match.homeTeam.name;
      const away = match.awayTeam.name;
      const homeScore = match.score.fullTime.home ?? 0;
      const awayScore = match.score.fullTime.away ?? 0;

      if (!teamMatches[home]) teamMatches[home] = [];
      if (!teamMatches[away]) teamMatches[away] = [];

      if (homeScore > awayScore) {
        teamMatches[home].push('W');
        teamMatches[away].push('L');
      } else if (homeScore < awayScore) {
        teamMatches[home].push('L');
        teamMatches[away].push('W');
      } else {
        teamMatches[home].push('D');
        teamMatches[away].push('D');
      }
    }

    const form = {};
    for (const [team, results] of Object.entries(teamMatches)) {
      form[team] = results.slice(-5);
    }
    return form;
  } catch (err) {
    console.warn('Kon teamvorm niet ophalen:', err.message);
    return {};
  }
}

// Doelpunten voor/tegen per team in het toernooi
async function getTeamStats(apiKey) {
  try {
    const data = await fetchWithAuth(
      `${FOOTBALL_API_BASE}/competitions/${COMPETITION_CODE}/matches?status=FINISHED`,
      apiKey
    );

    const stats = {};

    for (const match of data.matches || []) {
      const home = match.homeTeam.name;
      const away = match.awayTeam.name;
      const homeScore = match.score.fullTime.home ?? 0;
      const awayScore = match.score.fullTime.away ?? 0;

      if (!stats[home]) stats[home] = { goalsFor: 0, goalsAgainst: 0, gamesPlayed: 0 };
      if (!stats[away]) stats[away] = { goalsFor: 0, goalsAgainst: 0, gamesPlayed: 0 };

      stats[home].goalsFor += homeScore;
      stats[home].goalsAgainst += awayScore;
      stats[home].gamesPlayed++;

      stats[away].goalsFor += awayScore;
      stats[away].goalsAgainst += homeScore;
      stats[away].gamesPlayed++;
    }

    return stats;
  } catch (err) {
    console.warn('Kon teamstatistieken niet ophalen:', err.message);
    return {};
  }
}

// Topscorers van het toernooi met goals en gespeelde wedstrijden
async function getScorers(apiKey) {
  try {
    const data = await fetchWithAuth(
      `${FOOTBALL_API_BASE}/competitions/${COMPETITION_CODE}/scorers?limit=100`,
      apiKey
    );

    return (data.scorers || []).map(s => ({
      name: s.player.name,
      nationality: s.player.nationality,
      team: s.team.name,
      goals: s.goals ?? 0,
      assists: s.assists ?? 0,
      gamesPlayed: s.playedMatches ?? 1
    }));
  } catch (err) {
    console.warn('Kon scorerslijst niet ophalen:', err.message);
    return [];
  }
}

module.exports = { getTeamForm, getTeamStats, getScorers };
