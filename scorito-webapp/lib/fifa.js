'use strict';
const path = require('path');
const fs = require('fs');

// FIFA-ranglijst WK 2026 deelnemers (stand juni 2026)
const DEFAULT_RANKINGS = {
  'Argentina': 1,
  'France': 2,
  'England': 3,
  'Spain': 4,
  'Brazil': 5,
  'Portugal': 6,
  'Netherlands': 7,
  'Belgium': 8,
  'Italy': 9,
  'Uruguay': 10,
  'Germany': 11,
  'Croatia': 12,
  'Switzerland': 13,
  'Colombia': 14,
  'Mexico': 15,
  'United States': 16,
  'USA': 16,
  'Senegal': 17,
  'Denmark': 18,
  'Austria': 19,
  'Morocco': 20,
  'Japan': 21,
  'Serbia': 22,
  'Poland': 23,
  'South Korea': 24,
  'Korea Republic': 24,
  'Hungary': 25,
  'Ukraine': 26,
  'Australia': 27,
  'Canada': 28,
  'Turkey': 29,
  'Türkiye': 29,
  'Iran': 30,
  'Ecuador': 31,
  'Peru': 32,
  'Chile': 33,
  'Paraguay': 34,
  'Saudi Arabia': 35,
  'Egypt': 36,
  'Nigeria': 37,
  'Cameroon': 38,
  'Ghana': 39,
  'Tunisia': 40,
  'Algeria': 41,
  "Côte d'Ivoire": 42,
  'Ivory Coast': 42,
  'Mali': 43,
  'South Africa': 44,
  'New Zealand': 45,
  'Qatar': 46,
  'Jamaica': 47,
  'Honduras': 48,
  'Panama': 49,
  'Costa Rica': 50,
  'El Salvador': 51,
  'Venezuela': 52,
  'Bolivia': 53,
  'Guatemala': 54,
  'Cuba': 55,
  'Trinidad and Tobago': 56,
  'Angola': 57,
  'Tanzania': 58,
  'Zambia': 59,
  'Zimbabwe': 60,
  'Congo DR': 61,
  'Iraq': 62,
  'Uzbekistan': 63,
  'Oman': 64,
  'Palestine': 65,
  'Indonesia': 66,
  'Philippines': 67
};

function normalize(name) {
  return (name || '').toLowerCase().replace(/\s+/g, ' ').trim();
}

function getRank(teamName, rankings) {
  const norm = normalize(teamName);
  for (const [key, rank] of Object.entries(rankings)) {
    if (normalize(key) === norm) return rank;
  }
  for (const [key, rank] of Object.entries(rankings)) {
    const k = normalize(key);
    if (k.includes(norm) || norm.includes(k)) return rank;
  }
  console.warn(`FIFA rang niet gevonden voor: "${teamName}", gebruik 100 als standaard`);
  return 100;
}

function getRankings() {
  const customPath = path.join(__dirname, '../data/fifa-rankings.json');
  try {
    if (fs.existsSync(customPath)) {
      const custom = JSON.parse(fs.readFileSync(customPath, 'utf8'));
      return { ...DEFAULT_RANKINGS, ...custom };
    }
  } catch {
    console.warn('Kon custom FIFA-ranglijst niet laden, gebruik standaard');
  }
  return { ...DEFAULT_RANKINGS };
}

module.exports = { getRankings, getRank };
