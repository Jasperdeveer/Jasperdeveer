import ActivityKit
import Foundation

struct PadelScoreAttributes: ActivityAttributes {
    // Static — set at match start, never changes
    var myTeamName: String
    var rivalsName: String

    // Dynamic — updated on every point
    struct ContentState: Codable, Hashable {
        var myTeamScore: String      // "0", "15", "30", "40", "Ad"
        var rivalsScore: String
        var myTeamGames: Int
        var rivalsGames: Int
        var myTeamSetsWon: Int
        var rivalsSetsWon: Int
        var setScores: [String]      // ["6-4", "3-1"]
        var servingPlayerName: String
        var servingTeam: Int         // 0 = myTeam, 1 = rivals
        var isDeuced: Bool
        var myTeamHasAdvantage: Bool
        var rivalsHaveAdvantage: Bool
        var inTiebreak: Bool
        var isFinished: Bool
        var themeId: String
    }
}
