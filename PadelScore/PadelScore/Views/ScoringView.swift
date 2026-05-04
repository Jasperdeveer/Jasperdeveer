import SwiftUI

struct ScoringView: View {
    let state: MatchState
    @StateObject private var manager = MatchManager.shared
    @State private var showSetup = false
    @State private var showEndAlert = false

    var body: some View {
        NavigationStack {
            ZStack {
                Color.black.ignoresSafeArea()

                VStack(spacing: 0) {
                    // Previous sets
                    if !state.completedSets.isEmpty {
                        completedSetsBar
                    }

                    // Current set header
                    Text("SET \(state.currentSetIndex + 1)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .padding(.top, 12)

                    // Games row
                    HStack {
                        VStack {
                            Text(state.myTeam.name)
                                .font(.caption)
                                .foregroundColor(.secondary)
                            Text("\(state.myTeamGames)")
                                .font(.system(size: 48, weight: .bold))
                                .foregroundColor(.green)
                        }
                        Text("GAMES")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                            .padding(.horizontal, 8)
                        VStack {
                            Text(state.rivals.name)
                                .font(.caption)
                                .foregroundColor(.secondary)
                            Text("\(state.rivalsGames)")
                                .font(.system(size: 48, weight: .bold))
                                .foregroundColor(.red)
                        }
                    }
                    .padding(.top, 8)

                    // Current game score
                    ZStack {
                        RoundedRectangle(cornerRadius: 16)
                            .fill(Color(white: 0.1))
                        VStack(spacing: 4) {
                            Text(state.inTiebreak ? "TIEBREAK" : "CURRENT GAME")
                                .font(.caption2)
                                .foregroundColor(.secondary)
                            HStack(spacing: 24) {
                                Text(state.myTeamScoreDisplay)
                                    .font(.system(size: 64, weight: .black))
                                    .foregroundColor(state.myTeamHasAdvantage ? .green : .white)
                                Text("–")
                                    .font(.system(size: 32, weight: .light))
                                    .foregroundColor(.secondary)
                                Text(state.rivalsScoreDisplay)
                                    .font(.system(size: 64, weight: .black))
                                    .foregroundColor(state.rivalsHaveAdvantage ? .red : .white)
                            }
                            if state.isDeuced {
                                Text("DEUCE")
                                    .font(.caption)
                                    .foregroundColor(.orange)
                                    .fontWeight(.semibold)
                            }
                        }
                        .padding(.vertical, 12)
                    }
                    .padding(.horizontal, 20)
                    .padding(.top, 8)

                    // Undo
                    Button(action: { manager.undoLastPoint() }) {
                        Label("Undo Last Point", systemImage: "arrow.uturn.backward")
                            .font(.subheadline)
                            .foregroundColor(.secondary)
                    }
                    .padding(.vertical, 8)
                    .disabled(manager.history.isEmpty)

                    // Score buttons
                    HStack(spacing: 12) {
                        ScoreButton(
                            label: state.myTeamScoreDisplay,
                            teamName: state.myTeam.name,
                            color: .green,
                            isServing: state.servingTeam == 0,
                            serverName: state.servingTeam == 0 ? state.servingPlayerName : nil
                        ) {
                            manager.scorePoint(for: 0)
                        }

                        ScoreButton(
                            label: state.rivalsScoreDisplay,
                            teamName: state.rivals.name,
                            color: .red,
                            isServing: state.servingTeam == 1,
                            serverName: state.servingTeam == 1 ? state.servingPlayerName : nil
                        ) {
                            manager.scorePoint(for: 1)
                        }
                    }
                    .padding(.horizontal, 16)
                    .padding(.bottom, 16)
                }
            }
            .navigationTitle("LIVE")
            .navigationBarTitleDisplayMode(.inline)
            .toolbarColorScheme(.dark, for: .navigationBar)
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    liveIndicator
                }
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Stoppen") { showEndAlert = true }
                        .foregroundColor(.red)
                }
            }
            .sheet(isPresented: $showSetup) {
                MatchSetupView(isPresented: $showSetup)
            }
            .alert("Wedstrijd beëindigen?", isPresented: $showEndAlert) {
                Button("Annuleer", role: .cancel) {}
                Button("Beëindigen", role: .destructive) { manager.endMatch() }
            }
        }
    }

    private var liveIndicator: some View {
        HStack(spacing: 4) {
            Circle()
                .fill(.green)
                .frame(width: 8, height: 8)
            Text("LIVE")
                .font(.caption)
                .foregroundColor(.green)
        }
    }

    private var completedSetsBar: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(Array(state.completedSets.enumerated()), id: \.offset) { i, set in
                    VStack(spacing: 2) {
                        Text("Set \(i + 1)")
                            .font(.caption2)
                            .foregroundColor(.secondary)
                        Text("\(set.myTeam)–\(set.rivals)")
                            .font(.caption)
                            .fontWeight(.semibold)
                            .foregroundColor(set.myTeam > set.rivals ? .green : .red)
                    }
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                    .background(Color(white: 0.15))
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                }
            }
            .padding(.horizontal, 16)
        }
        .padding(.top, 8)
    }
}

struct ScoreButton: View {
    let label: String
    let teamName: String
    let color: Color
    let isServing: Bool
    let serverName: String?
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(spacing: 6) {
                Text(label)
                    .font(.system(size: 52, weight: .black))
                    .foregroundColor(.white)
                HStack(spacing: 4) {
                    if isServing {
                        Image(systemName: "tennisball.fill")
                            .font(.caption)
                            .foregroundColor(.yellow)
                    }
                    Text(teamName)
                        .font(.subheadline)
                        .fontWeight(.semibold)
                        .foregroundColor(.white)
                }
                if let server = serverName {
                    Text("\(server) serveert")
                        .font(.caption2)
                        .foregroundColor(.white.opacity(0.7))
                }
            }
            .frame(maxWidth: .infinity)
            .frame(height: 160)
            .background(color)
            .clipShape(RoundedRectangle(cornerRadius: 20))
        }
        .buttonStyle(.plain)
    }
}

struct PrimaryButtonStyle: ButtonStyle {
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.headline)
            .foregroundColor(.black)
            .padding(.horizontal, 32)
            .padding(.vertical, 14)
            .background(.green)
            .clipShape(RoundedRectangle(cornerRadius: 12))
            .opacity(configuration.isPressed ? 0.8 : 1)
    }
}
