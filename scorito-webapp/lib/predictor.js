'use strict';
const { getRank } = require('./fifa');

// Elo-gebaseerde kansberekening op basis van FIFA-rangverschil
function fifaProbs(homeRank, awayRank) {
  const diff = awayRank - homeRank; // positief = thuisteam beter gerangschikt
  const base = 1 / (1 + Math.pow(10, -diff / 100));
  // Gelijkspelkans ~ 0.25, verdeeld evenredig
  const drawBase = 0.25;
  const homeWin = (base * (1 - drawBase));
  const awayWin = ((1 - base) * (1 - drawBase));
  const draw = drawBase;
  const total = homeWin + draw + awayWin;
  return { homeWin: homeWin / total, draw: draw / total, awayWin: awayWin / total };
}

// Vorm omzetten naar score 0–1 (W=3pt, D=1pt, L=0pt)
function formScore(results) {
  if (!results || results.length === 0) return 0.5;
  const pts = results.reduce((s, r) => s + (r === 'W' ? 3 : r === 'D' ? 1 : 0), 0);
  return pts / (results.length * 3);
}

// Verwachte totale doelpunten uit over/under kans
function expectedTotal(over25Prob) {
  // Als over-2.5 kans 60% is → verwacht ~2.8 goals
  return 2.5 + (over25Prob - 0.5) * 3.0;
}

// Verwachte doelpunten verdelen over thuisteam en uitteam
function expectedGoals(total, homeWinProb, awayWinProb) {
  const homeShare = homeWinProb / (homeWinProb + awayWinProb + 0.001);
  return {
    home: Math.max(0, total * homeShare),
    away: Math.max(0, total * (1 - homeShare))
  };
}

// Verwachte doelpunten afronden naar een realistische uitslag
function toScore(homeExp, awayExp, outcome) {
  let h = Math.round(homeExp);
  let a = Math.round(awayExp);

  if (outcome === 'home' && h <= a) h = a + 1;
  if (outcome === 'away' && a <= h) a = h + 1;
  if (outcome === 'draw') {
    const avg = Math.round((h + a) / 2);
    h = avg;
    a = avg;
  }

  return { homeScore: Math.min(h, 6), awayScore: Math.min(a, 6) };
}

function normalize(name) {
  return (name || '').toLowerCase().replace(/\s+/g, ' ').trim();
}

function findByTeam(teamName, obj) {
  const n = normalize(teamName);
  for (const [key, val] of Object.entries(obj)) {
    const k = normalize(key);
    if (k === n || k.includes(n) || n.includes(k)) return val;
  }
  return null;
}

function teamScorers(teamName, scorers) {
  const n = normalize(teamName);
  return scorers.filter(s => {
    const t = normalize(s.team);
    return t === n || t.includes(n) || n.includes(t);
  });
}

// Defensieve sterkte: hoge waarde = makkelijker te scoren
function defenseRating(teamName, teamStats, rankings) {
  const stats = findByTeam(teamName, teamStats);
  const rank = getRank(teamName, rankings);
  const goalsAgainstPerGame = stats && stats.gamesPlayed > 0
    ? stats.goalsAgainst / stats.gamesPlayed
    : 1.2;
  // Slechter gerangschikte teams zijn ook defensief zwakker
  return goalsAgainstPerGame + (rank / 200);
}

// Scorer-score: goals per wedstrijd × hoe makkelijk het is tegen tegenstander te scoren
function scorerRating(player, opponentDefRating) {
  const gpg = player.gamesPlayed > 0 ? player.goals / player.gamesPlayed : 0;
  return gpg * opponentDefRating;
}

function generatePredictions({ matches, rankings, odds, form, scorers, teamStats }) {
  return matches.map(match => {
    const { homeTeam, awayTeam } = match;

    // — FIFA-rang signaal —
    const homeRank = getRank(homeTeam, rankings);
    const awayRank = getRank(awayTeam, rankings);
    const fifa = fifaProbs(homeRank, awayRank);

    // — Wedkantoor-signaal —
    const matchOdds = odds.find(o => o.matchIndex === match.index);
    const oddsH2h = matchOdds?.h2h || null;
    const oddsTotals = matchOdds?.totals || null;

    // — Toernooivorm signaal —
    const homeFormArr = findByTeam(homeTeam, form) || [];
    const awayFormArr = findByTeam(awayTeam, form) || [];
    const hForm = formScore(homeFormArr);
    const aForm = formScore(awayFormArr);
    const formTotal = hForm + aForm + 0.3;
    const formP = {
      homeWin: hForm / formTotal,
      draw: 0.3 / formTotal,
      awayWin: aForm / formTotal
    };

    // — Gecombineerde kansen (gewogen) —
    let final;
    if (oddsH2h) {
      // Bookmakers 45%, FIFA 25%, vorm 30%
      final = {
        homeWin: 0.45 * oddsH2h.homeWin + 0.25 * fifa.homeWin + 0.30 * formP.homeWin,
        draw:    0.45 * oddsH2h.draw    + 0.25 * fifa.draw    + 0.30 * formP.draw,
        awayWin: 0.45 * oddsH2h.awayWin + 0.25 * fifa.awayWin + 0.30 * formP.awayWin
      };
    } else {
      // Geen odds: FIFA 45%, vorm 55%
      final = {
        homeWin: 0.45 * fifa.homeWin + 0.55 * formP.homeWin,
        draw:    0.45 * fifa.draw    + 0.55 * formP.draw,
        awayWin: 0.45 * fifa.awayWin + 0.55 * formP.awayWin
      };
    }

    // — Uitkomst bepalen —
    const outcome = final.homeWin >= final.draw && final.homeWin >= final.awayWin
      ? 'home'
      : final.awayWin > final.homeWin && final.awayWin >= final.draw
        ? 'away'
        : 'draw';

    // — Uitslag berekenen —
    const over25Prob = oddsTotals?.over25Prob ?? 0.52;
    const expTotal = expectedTotal(over25Prob);
    const expG = expectedGoals(expTotal, final.homeWin, final.awayWin);
    const score = toScore(expG.home, expG.away, outcome);

    // — Topscorers per team aanbevelen —
    // Verdediger van het andere team bepaalt hoe makkelijk scoren is
    const homeDefRating = defenseRating(homeTeam, teamStats, rankings);
    const awayDefRating = defenseRating(awayTeam, teamStats, rankings);

    const homeCandidates = teamScorers(homeTeam, scorers)
      .filter(p => p.goals > 0)
      .map(p => ({ ...p, scorerRating: scorerRating(p, homeDefRating) }))
      .sort((a, b) => b.scorerRating - a.scorerRating)
      .slice(0, 3);

    const awayCandidates = teamScorers(awayTeam, scorers)
      .filter(p => p.goals > 0)
      .map(p => ({ ...p, scorerRating: scorerRating(p, awayDefRating) }))
      .sort((a, b) => b.scorerRating - a.scorerRating)
      .slice(0, 3);

    return {
      ...match,
      prediction: {
        homeScore: score.homeScore,
        awayScore: score.awayScore,
        outcome,
        recommendedScorers: {
          home: homeCandidates,
          away: awayCandidates
        },
        // Standaard ingevuld: top-1 scorer per team (gebruiker kan wijzigen)
        selectedScorers: [
          ...(homeCandidates.slice(0, 1).map(s => s.name)),
          ...(awayCandidates.slice(0, 1).map(s => s.name))
        ]
      },
      reasoning: {
        homeRank,
        awayRank,
        fifaProbs: fifa,
        oddsProbs: oddsH2h,
        formProbs: formP,
        finalProbs: final,
        homeForm: homeFormArr,
        awayForm: awayFormArr,
        expectedGoals: expG,
        over25Prob
      }
    };
  });
}

module.exports = { generatePredictions };
