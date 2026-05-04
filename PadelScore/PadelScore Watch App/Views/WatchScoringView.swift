import SwiftUI

// Fits entirely on one screen — no ScrollView. Designed for Series 10/11 (46mm).
struct WatchScoringView: View {
    let state: MatchState
    @StateObject private var manager = MatchManager.shared
    @StateObject private var themes = ThemeManager.shared
    @State private var showMenu = false

    var theme: AppTheme { themes.current }

    var body: some View {
        ZStack {
            theme.background.ignoresSafeArea()

            VStack(spacing: 3) {
                // Row 1: completed sets + tiebreak/deuce badge
                topRow

                // Row 2: game score boxes
                HStack(spacing: 6) {
                    scoreBox(score: state.myTeamScoreDisplay,
                             color: state.myTeamHasAdvantage ? theme.myTeamColor : theme.primaryText,
                             isServing: state.servingTeam == 0)
                    scoreBox(score: state.rivalsScoreDisplay,
                             color: state.rivalsHaveAdvantage ? theme.rivalsColor : theme.primaryText,
                             isServing: state.servingTeam == 1)
                }

                // Row 3: status + serve
                statusRow

                // Row 4: games in set
                gamesRow

                // Row 5: score buttons
                HStack(spacing: 6) {
                    tapButton(label: state.myTeam.name, color: theme.myTeamColor, teamIndex: 0)
                    tapButton(label: state.rivals.name, color: theme.rivalsColor, teamIndex: 1)
                }

                // Row 6: undo
                Button(action: { manager.undoLastPoint() }) {
                    HStack(spacing: 3) {
                        Image(systemName: "arrow.uturn.backward")
                        Text("Undo")
                    }
                    .font(.system(size: 11))
                    .foregroundColor(manager.history.isEmpty ? theme.secondaryText.opacity(0.4) : theme.secondaryText)
                }
                .buttonStyle(.plain)
                .disabled(manager.history.isEmpty)
            }
            .padding(.horizontal, 4)
        }
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button(action: { showMenu = true }) {
                    Image(systemName: "ellipsis.circle")
                        .foregroundColor(theme.secondaryText)
                }
            }
        }
        .sheet(isPresented: $showMenu) {
            WatchMenuView()
        }
    }

    // MARK: - Sub-views

    private var topRow: some View {
        HStack(spacing: 4) {
            ForEach(Array(state.completedSets.enumerated()), id: \.offset) { _, set in
                Text("\(set.myTeam)-\(set.rivals)")
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundColor(set.myTeam > set.rivals ? theme.myTeamColor : theme.rivalsColor)
                    .padding(.horizontal, 5)
                    .padding(.vertical, 2)
                    .background(theme.card)
                    .clipShape(RoundedRectangle(cornerRadius: 4))
            }

            Spacer()

            if state.inTiebreak {
                badge("TIE", color: theme.accent)
            } else if state.isDeuced {
                badge("DEUCE", color: theme.accent)
            } else if state.myTeamHasAdvantage {
                badge("ADV \(state.myTeam.name)", color: theme.myTeamColor)
            } else if state.rivalsHaveAdvantage {
                badge("ADV \(state.rivals.name)", color: theme.rivalsColor)
            }
        }
    }

    private func badge(_ text: String, color: Color) -> some View {
        Text(text)
            .font(.system(size: 9, weight: .bold))
            .foregroundColor(color)
            .padding(.horizontal, 5)
            .padding(.vertical, 2)
            .overlay(RoundedRectangle(cornerRadius: 4).stroke(color, lineWidth: 1))
    }

    private func scoreBox(score: String, color: Color, isServing: Bool) -> some View {
        ZStack(alignment: .topTrailing) {
            Text(score)
                .font(.system(size: 38, weight: .black))
                .foregroundColor(color)
                .frame(maxWidth: .infinity)
                .frame(height: 52)
                .background(theme.card)
                .clipShape(RoundedRectangle(cornerRadius: 10))

            if isServing {
                Circle()
                    .fill(theme.accent)
                    .frame(width: 8, height: 8)
                    .padding(4)
            }
        }
    }

    private var statusRow: some View {
        HStack(spacing: 4) {
            Image(systemName: "tennisball.fill")
                .font(.system(size: 9))
                .foregroundColor(theme.accent)
            Text(state.servingPlayerName)
                .font(.system(size: 11))
                .foregroundColor(theme.secondaryText)
                .lineLimit(1)
        }
    }

    private var gamesRow: some View {
        HStack(spacing: 8) {
            Text("\(state.myTeamGames)")
                .font(.system(size: 16, weight: .bold))
                .foregroundColor(theme.myTeamColor)
            Text("–")
                .font(.system(size: 12))
                .foregroundColor(theme.secondaryText)
            Text("\(state.rivalsGames)")
                .font(.system(size: 16, weight: .bold))
                .foregroundColor(theme.rivalsColor)
            Text("games")
                .font(.system(size: 10))
                .foregroundColor(theme.secondaryText)
        }
    }

    private func tapButton(label: String, color: Color, teamIndex: Int) -> some View {
        Button(action: { manager.scorePoint(for: teamIndex) }) {
            Text(label)
                .font(.system(size: 12, weight: .bold))
                .foregroundColor(theme.background)
                .frame(maxWidth: .infinity)
                .frame(height: 40)
                .background(color)
                .clipShape(RoundedRectangle(cornerRadius: 8))
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Menu (end match / change theme)
struct WatchMenuView: View {
    @StateObject private var themes = ThemeManager.shared
    @StateObject private var manager = MatchManager.shared
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        ScrollView {
            VStack(spacing: 8) {
                Text("Opties")
                    .font(.headline)

                // Theme picker
                Text("Thema")
                    .font(.caption)
                    .foregroundColor(.secondary)

                ForEach(AppTheme.all) { theme in
                    Button(action: {
                        themes.select(theme)
                        dismiss()
                    }) {
                        HStack {
                            Text(theme.emoji)
                            Text(theme.name)
                                .font(.system(size: 13))
                            Spacer()
                            if themes.current.id == theme.id {
                                Image(systemName: "checkmark")
                                    .font(.system(size: 11))
                            }
                        }
                        .foregroundColor(.primary)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 8)
                        .background(Color(white: 0.15))
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                    }
                    .buttonStyle(.plain)
                }

                Divider()

                Button(role: .destructive, action: {
                    manager.endMatch()
                    dismiss()
                }) {
                    Text("Wedstrijd stoppen")
                        .font(.system(size: 12))
                }
            }
            .padding(.horizontal, 4)
        }
    }
}
