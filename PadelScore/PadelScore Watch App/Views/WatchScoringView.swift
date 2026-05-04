import SwiftUI

struct WatchScoringView: View {
    let state: MatchState
    @StateObject private var manager = MatchManager.shared

    var body: some View {
        ScrollView {
            VStack(spacing: 4) {
                // Completed sets mini bar
                if !state.completedSets.isEmpty {
                    setsBar
                }

                // Game score
                HStack(spacing: 8) {
                    gameScoreBox(score: state.myTeamScoreDisplay,
                                 color: scoreColor(hasAdv: state.myTeamHasAdvantage, teamIndex: 0),
                                 isServing: state.servingTeam == 0)
                    gameScoreBox(score: state.rivalsScoreDisplay,
                                 color: scoreColor(hasAdv: state.rivalsHaveAdvantage, teamIndex: 1),
                                 isServing: state.servingTeam == 1)
                }

                if state.isDeuced {
                    Text("DEUCE")
                        .font(.system(size: 11, weight: .bold))
                        .foregroundColor(.orange)
                }

                if state.inTiebreak {
                    Text("TIEBREAK")
                        .font(.system(size: 11, weight: .bold))
                        .foregroundColor(.yellow)
                }

                // Server name
                Text("\(state.servingPlayerName) serveert")
                    .font(.system(size: 11))
                    .foregroundColor(.secondary)

                // Games row
                HStack(spacing: 16) {
                    Text("\(state.myTeamGames)")
                        .font(.system(size: 18, weight: .bold))
                        .foregroundColor(.green)
                    Text("games")
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)
                    Text("\(state.rivalsGames)")
                        .font(.system(size: 18, weight: .bold))
                        .foregroundColor(.red)
                }

                // Score buttons
                HStack(spacing: 8) {
                    watchScoreButton(color: .green, teamIndex: 0)
                    watchScoreButton(color: .red, teamIndex: 1)
                }
                .padding(.top, 4)

                // Undo
                Button(action: { manager.undoLastPoint() }) {
                    Image(systemName: "arrow.uturn.backward")
                        .font(.system(size: 14))
                }
                .buttonStyle(.plain)
                .foregroundColor(.secondary)
                .disabled(manager.history.isEmpty)
            }
            .padding(.horizontal, 4)
        }
        .navigationTitle("Padel")
        .navigationBarTitleDisplayMode(.inline)
    }

    private func scoreColor(hasAdv: Bool, teamIndex: Int) -> Color {
        if hasAdv { return teamIndex == 0 ? .green : .red }
        return .white
    }

    private func gameScoreBox(score: String, color: Color, isServing: Bool) -> some View {
        ZStack(alignment: .bottomTrailing) {
            Text(score)
                .font(.system(size: 32, weight: .black))
                .foregroundColor(color)
                .frame(maxWidth: .infinity)
                .frame(height: 50)
                .background(Color(white: 0.15))
                .clipShape(RoundedRectangle(cornerRadius: 10))

            if isServing {
                Image(systemName: "tennisball.fill")
                    .font(.system(size: 10))
                    .foregroundColor(.yellow)
                    .padding(4)
            }
        }
    }

    private func watchScoreButton(color: Color, teamIndex: Int) -> some View {
        Button(action: { manager.scorePoint(for: teamIndex) }) {
            Text(teamIndex == 0 ? state.myTeam.name : state.rivals.name)
                .font(.system(size: 13, weight: .semibold))
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .frame(height: 44)
                .background(color)
                .clipShape(RoundedRectangle(cornerRadius: 10))
        }
        .buttonStyle(.plain)
    }

    private var setsBar: some View {
        HStack(spacing: 6) {
            ForEach(Array(state.completedSets.enumerated()), id: \.offset) { _, set in
                Text("\(set.myTeam)-\(set.rivals)")
                    .font(.system(size: 10, weight: .medium))
                    .foregroundColor(set.myTeam > set.rivals ? .green : .red)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 3)
                    .background(Color(white: 0.2))
                    .clipShape(RoundedRectangle(cornerRadius: 5))
            }
        }
    }
}
