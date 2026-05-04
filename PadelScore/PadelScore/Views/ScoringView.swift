import SwiftUI

struct ScoringView: View {
    let state: MatchState
    @StateObject private var manager = MatchManager.shared
    @StateObject private var themes = ThemeManager.shared
    @State private var showEndAlert = false

    var theme: AppTheme { themes.current }

    var body: some View {
        ZStack {
            theme.background.ignoresSafeArea()

            VStack(spacing: 0) {
                // Completed sets bar
                if !state.completedSets.isEmpty {
                    completedSetsBar.padding(.top, 8)
                }

                // Set header
                Text("SET \(state.currentSetIndex + 1)")
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundColor(theme.secondaryText)
                    .tracking(2)
                    .padding(.top, state.completedSets.isEmpty ? 12 : 6)

                // Games row
                HStack(spacing: 0) {
                    Spacer()
                    gamesLabel(count: state.myTeamGames, name: state.myTeam.name, color: theme.myTeamColor)
                    Text("GAMES")
                        .font(.system(size: 10, weight: .medium))
                        .foregroundColor(theme.secondaryText)
                        .tracking(1)
                        .frame(width: 60)
                    gamesLabel(count: state.rivalsGames, name: state.rivals.name, color: theme.rivalsColor)
                    Spacer()
                }
                .padding(.top, 6)

                // Game score card
                ZStack {
                    RoundedRectangle(cornerRadius: 20)
                        .fill(theme.card)
                    VStack(spacing: 6) {
                        if state.inTiebreak {
                            statusBadge("TIEBREAK", color: theme.accent)
                        }

                        HStack(spacing: 20) {
                            gameScoreText(state.myTeamScoreDisplay,
                                          color: state.myTeamHasAdvantage ? theme.myTeamColor : theme.primaryText)
                            Text("–")
                                .font(.system(size: 28, weight: .thin))
                                .foregroundColor(theme.secondaryText)
                            gameScoreText(state.rivalsScoreDisplay,
                                          color: state.rivalsHaveAdvantage ? theme.rivalsColor : theme.primaryText)
                        }

                        if state.isDeuced && !state.inTiebreak {
                            statusBadge("DEUCE", color: theme.accent)
                        } else if state.myTeamHasAdvantage {
                            statusBadge("VOORDEEL \(state.myTeam.name)", color: theme.myTeamColor)
                        } else if state.rivalsHaveAdvantage {
                            statusBadge("VOORDEEL \(state.rivals.name)", color: theme.rivalsColor)
                        }
                    }
                    .padding(.vertical, 14)
                }
                .padding(.horizontal, 20)
                .padding(.top, 10)

                // Undo
                Button(action: { manager.undoLastPoint() }) {
                    Label("Undo", systemImage: "arrow.uturn.backward")
                        .font(.subheadline)
                        .foregroundColor(manager.history.isEmpty
                                         ? theme.secondaryText.opacity(0.3)
                                         : theme.secondaryText)
                }
                .padding(.vertical, 10)
                .disabled(manager.history.isEmpty)

                // Serve label
                HStack(spacing: 5) {
                    Image(systemName: "tennisball.fill")
                        .font(.caption)
                        .foregroundColor(theme.accent)
                    Text("\(state.servingPlayerName) serveert")
                        .font(.caption)
                        .foregroundColor(theme.secondaryText)
                }
                .padding(.bottom, 8)

                // Score buttons
                HStack(spacing: 14) {
                    ScoreButton(
                        label: state.myTeamScoreDisplay,
                        teamName: state.myTeam.name,
                        color: theme.myTeamColor,
                        textColor: theme.background,
                        isServing: state.servingTeam == 0
                    ) { manager.scorePoint(for: 0) }

                    ScoreButton(
                        label: state.rivalsScoreDisplay,
                        teamName: state.rivals.name,
                        color: theme.rivalsColor,
                        textColor: theme.background,
                        isServing: state.servingTeam == 1
                    ) { manager.scorePoint(for: 1) }
                }
                .padding(.horizontal, 16)
                .padding(.bottom, 16)
            }
        }
        .navigationTitle("LIVE")
        .navigationBarTitleDisplayMode(.inline)
        .toolbarBackground(theme.background, for: .navigationBar)
        .toolbarColorScheme(theme.id == "light" ? .light : .dark, for: .navigationBar)
        .toolbar {
            ToolbarItem(placement: .topBarLeading) {
                liveIndicator
            }
            ToolbarItem(placement: .topBarTrailing) {
                Button("Stoppen") { showEndAlert = true }
                    .foregroundColor(theme.rivalsColor)
            }
        }
        .alert("Wedstrijd beëindigen?", isPresented: $showEndAlert) {
            Button("Annuleer", role: .cancel) {}
            Button("Beëindigen", role: .destructive) { manager.endMatch() }
        }
    }

    // MARK: - Helpers

    private func gamesLabel(count: Int, name: String, color: Color) -> some View {
        VStack(spacing: 2) {
            Text("\(count)")
                .font(.system(size: 44, weight: .black))
                .foregroundColor(color)
            Text(name)
                .font(.caption2)
                .foregroundColor(theme.secondaryText)
                .lineLimit(1)
        }
        .frame(minWidth: 70)
    }

    private func gameScoreText(_ score: String, color: Color) -> some View {
        Text(score)
            .font(.system(size: 68, weight: .black))
            .foregroundColor(color)
            .frame(minWidth: 80, alignment: .center)
    }

    private func statusBadge(_ text: String, color: Color) -> some View {
        Text(text)
            .font(.system(size: 11, weight: .bold))
            .tracking(1)
            .foregroundColor(color)
            .padding(.horizontal, 10)
            .padding(.vertical, 4)
            .overlay(RoundedRectangle(cornerRadius: 6).stroke(color, lineWidth: 1.5))
    }

    private var liveIndicator: some View {
        HStack(spacing: 4) {
            Circle().fill(theme.myTeamColor).frame(width: 7, height: 7)
            Text("LIVE")
                .font(.caption)
                .foregroundColor(theme.myTeamColor)
        }
    }

    private var completedSetsBar: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 8) {
                ForEach(Array(state.completedSets.enumerated()), id: \.offset) { i, set in
                    VStack(spacing: 1) {
                        Text("Set \(i + 1)")
                            .font(.system(size: 9))
                            .foregroundColor(theme.secondaryText)
                        Text("\(set.myTeam)–\(set.rivals)")
                            .font(.system(size: 12, weight: .bold))
                            .foregroundColor(set.myTeam > set.rivals ? theme.myTeamColor : theme.rivalsColor)
                    }
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(theme.card)
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                }
            }
            .padding(.horizontal, 20)
        }
    }
}

// MARK: - Score button

struct ScoreButton: View {
    let label: String
    let teamName: String
    let color: Color
    let textColor: Color
    let isServing: Bool
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(spacing: 6) {
                Text(label)
                    .font(.system(size: 52, weight: .black))
                    .foregroundColor(textColor)
                HStack(spacing: 4) {
                    if isServing {
                        Image(systemName: "tennisball.fill")
                            .font(.caption)
                            .foregroundColor(textColor.opacity(0.8))
                    }
                    Text(teamName)
                        .font(.subheadline)
                        .fontWeight(.bold)
                        .foregroundColor(textColor)
                }
            }
            .frame(maxWidth: .infinity)
            .frame(height: 150)
            .background(color)
            .clipShape(RoundedRectangle(cornerRadius: 20))
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Primary button style (reusable)

struct PrimaryButtonStyle: ButtonStyle {
    var color: Color = .green

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.headline)
            .foregroundColor(.black)
            .padding(.horizontal, 32)
            .padding(.vertical, 14)
            .background(color)
            .clipShape(RoundedRectangle(cornerRadius: 12))
            .opacity(configuration.isPressed ? 0.8 : 1)
    }
}
