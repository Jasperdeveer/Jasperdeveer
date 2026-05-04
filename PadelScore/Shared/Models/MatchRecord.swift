import Foundation

struct MatchRecord: Codable, Identifiable {
    var id: UUID = UUID()
    var myTeam: Team
    var rivals: Team
    var mode: MatchMode
    var completedSets: [SetScore]
    var myTeamSetsWon: Int
    var rivalsSetsWon: Int
    var winnerTeam: Int  // 0 = myTeam, 1 = rivals
    var startTime: Date
    var endTime: Date
    var americanoMyTeam: Int
    var americanoRivals: Int

    var duration: TimeInterval { endTime.timeIntervalSince(startTime) }

    var durationDisplay: String {
        let mins = Int(duration) / 60
        let secs = Int(duration) % 60
        return String(format: "%d:%02d", mins, secs)
    }

    var dateDisplay: String {
        let f = DateFormatter()
        f.dateStyle = .medium
        f.timeStyle = .short
        return f.string(from: startTime)
    }

    var setScoreDisplay: String {
        completedSets.map { "\($0.myTeam)-\($0.rivals)" }.joined(separator: ", ")
    }

    static func from(state: MatchState) -> MatchRecord {
        MatchRecord(
            myTeam: state.myTeam,
            rivals: state.rivals,
            mode: state.mode,
            completedSets: state.completedSets,
            myTeamSetsWon: state.myTeamSetsWon,
            rivalsSetsWon: state.rivalsSetsWon,
            winnerTeam: state.winnerTeam ?? 0,
            startTime: state.startTime,
            endTime: state.endTime ?? Date(),
            americanoMyTeam: state.americanoMyTeam,
            americanoRivals: state.americanoRivals
        )
    }
}
