import Foundation

enum MatchMode: String, Codable, CaseIterable {
    case standard = "Standard"
    case americano = "Americano"
}

struct Team: Codable, Identifiable, Equatable {
    var id: UUID = UUID()
    var name: String
    var player1: String
    var player2: String
}

struct SetScore: Codable, Equatable {
    var myTeam: Int
    var rivals: Int
}

struct MatchState: Codable, Equatable {
    // Setup
    var myTeam: Team
    var rivals: Team
    var mode: MatchMode
    var goldenPoint: Bool
    var bestOf: Int = 3  // best of 3 sets

    // Set scores
    var completedSets: [SetScore] = []
    var myTeamGames: Int = 0
    var rivalsGames: Int = 0

    // Game points (raw count: 0,1,2,3 = 0,15,30,40)
    var myTeamPoints: Int = 0
    var rivalsPoints: Int = 0

    // Tiebreak
    var inTiebreak: Bool = false

    // Americano
    var americanoMyTeam: Int = 0
    var americanoRivals: Int = 0

    // Serve: 0 = myTeam, 1 = rivals
    var servingTeam: Int = 0
    var servingPlayerIndex: Int = 0  // 0 or 1 within team

    // Tiebreak serve tracking
    var tiebreakPointsPlayed: Int = 0

    // Match result
    var isFinished: Bool = false
    var winnerTeam: Int? = nil  // 0 = myTeam, 1 = rivals
    var startTime: Date = Date()
    var endTime: Date? = nil

    // MARK: - Display

    var myTeamScoreDisplay: String {
        if inTiebreak { return "\(myTeamPoints)" }
        return pointDisplay(myTeamPoints, opponent: rivalsPoints, isMyTeam: true)
    }

    var rivalsScoreDisplay: String {
        if inTiebreak { return "\(rivalsPoints)" }
        return pointDisplay(rivalsPoints, opponent: myTeamPoints, isMyTeam: false)
    }

    var isDeuced: Bool {
        !inTiebreak && myTeamPoints >= 3 && rivalsPoints >= 3 && myTeamPoints == rivalsPoints
    }

    var myTeamHasAdvantage: Bool {
        !inTiebreak && myTeamPoints > 3 && myTeamPoints > rivalsPoints
    }

    var rivalsHaveAdvantage: Bool {
        !inTiebreak && rivalsPoints > 3 && rivalsPoints > myTeamPoints
    }

    var servingPlayerName: String {
        if servingTeam == 0 {
            return servingPlayerIndex == 0 ? myTeam.player1 : myTeam.player2
        } else {
            return servingPlayerIndex == 0 ? rivals.player1 : rivals.player2
        }
    }

    var servingTeamName: String {
        servingTeam == 0 ? myTeam.name : rivals.name
    }

    var myTeamSetsWon: Int {
        completedSets.filter { $0.myTeam > $0.rivals }.count
    }

    var rivalsSetsWon: Int {
        completedSets.filter { $0.rivals > $0.myTeam }.count
    }

    var duration: TimeInterval {
        (endTime ?? Date()).timeIntervalSince(startTime)
    }

    private func pointDisplay(_ pts: Int, opponent: Int, isMyTeam: Bool) -> String {
        // Both at 3+ = deuce territory
        if pts >= 3 && opponent >= 3 {
            if pts == opponent { return "40" }
            if pts > opponent { return "Ad" }
            return "40"
        }
        switch pts {
        case 0: return "0"
        case 1: return "15"
        case 2: return "30"
        default: return "40"
        }
    }
}
