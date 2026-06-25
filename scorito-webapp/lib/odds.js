'use strict';
const ODDS_API_BASE = 'https://api.the-odds-api.com/v4';

function normalize(name) {
  return (name || '').toLowerCase().replace(/\s+/g, ' ').trim()
    .replace(/^the\s/, '')
    .replace(/^holland$/, 'netherlands');
}

// Verwijder de vig (overround) zodat kansen optellen tot 100%
function removeVig(homeOdds, drawOdds, awayOdds) {
  const h = 1 / homeOdds;
  const d = 1 / drawOdds;
  const a = 1 / awayOdds;
  const total = h + d + a;
  return { homeWin: h / total, draw: d / total, awayWin: a / total };
}

function teamsMatch(eventTeam, matchTeam) {
  const e = normalize(eventTeam);
  const m = normalize(matchTeam);
  return e === m || e.includes(m) || m.includes(e);
}

async function getOdds(matches, apiKey) {
  if (!apiKey) return [];

  try {
    // Zoek de juiste sport-sleutel voor het WK 2026
    const sportsRes = await fetch(`${ODDS_API_BASE}/sports?apiKey=${apiKey}`);
    if (!sportsRes.ok) {
      console.warn('Odds API: kon sportlijst niet ophalen');
      return [];
    }
    const sports = await sportsRes.json();

    const wkSport = sports.find(s =>
      s.key.includes('world_cup') || s.key.includes('fifa')
    );
    const sportKey = wkSport?.key || 'soccer_fifa_world_cup';
    console.log(`Odds API gebruikt sport: ${sportKey}`);

    const url = `${ODDS_API_BASE}/sports/${sportKey}/odds?apiKey=${apiKey}&regions=eu&markets=h2h,totals&oddsFormat=decimal`;
    const res = await fetch(url);

    if (!res.ok) {
      const text = await res.text();
      console.warn(`Odds API fout (${res.status}):`, text.substring(0, 200));
      return [];
    }

    const events = await res.json();
    const remaining = res.headers.get('x-requests-remaining');
    console.log(`Odds API: ${remaining} verzoeken resterend deze maand`);

    return matches.map(match => {
      const event = events.find(e =>
        teamsMatch(e.home_team, match.homeTeam) &&
        teamsMatch(e.away_team, match.awayTeam)
      );

      if (!event) {
        console.warn(`Geen odds gevonden voor: ${match.homeTeam} vs ${match.awayTeam}`);
        return { matchIndex: match.index, found: false };
      }

      // Gebruik de meest recente bookmaker
      const h2hMarket = event.bookmakers
        .flatMap(b => b.markets.filter(m => m.key === 'h2h').map(m => ({ ...m, bookmaker: b.key })))
        .sort((a, b) => new Date(b.last_update) - new Date(a.last_update))[0];

      const totalsMarket = event.bookmakers
        .flatMap(b => b.markets.filter(m => m.key === 'totals').map(m => ({ ...m, bookmaker: b.key })))
        .sort((a, b) => new Date(b.last_update) - new Date(a.last_update))[0];

      let h2h = null;
      if (h2hMarket) {
        const homeOdds = h2hMarket.outcomes.find(o => teamsMatch(o.name, match.homeTeam))?.price;
        const awayOdds = h2hMarket.outcomes.find(o => teamsMatch(o.name, match.awayTeam))?.price;
        const drawOdds = h2hMarket.outcomes.find(o => o.name === 'Draw')?.price;
        if (homeOdds && awayOdds && drawOdds) {
          h2h = {
            ...removeVig(homeOdds, drawOdds, awayOdds),
            homeOdds,
            drawOdds,
            awayOdds
          };
        }
      }

      let totals = null;
      if (totalsMarket) {
        // Gebruik over/under 2.5 als meest gangbare lijn
        const over = totalsMarket.outcomes.find(o => o.name === 'Over' && Number(o.point) === 2.5);
        const under = totalsMarket.outcomes.find(o => o.name === 'Under' && Number(o.point) === 2.5);
        if (over) {
          const overProb = 1 / over.price;
          totals = {
            line: 2.5,
            over25Prob: overProb,
            under25Prob: under ? 1 / under.price : 1 - overProb
          };
        }
      }

      return { matchIndex: match.index, found: true, h2h, totals };
    });

  } catch (err) {
    console.warn('Kon odds niet ophalen:', err.message);
    return [];
  }
}

module.exports = { getOdds };
