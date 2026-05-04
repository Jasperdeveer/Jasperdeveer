import ActivityKit
import WidgetKit
import SwiftUI

// MARK: - Widget bundle

@main
struct PadelScoreWidgetBundle: WidgetBundle {
    var body: some Widget {
        PadelScoreLiveActivityWidget()
    }
}

// MARK: - Live Activity widget

struct PadelScoreLiveActivityWidget: Widget {
    var body: some WidgetConfiguration {
        ActivityConfiguration(for: PadelScoreAttributes.self) { context in
            LockScreenView(context: context)
                .activityBackgroundTint(Color.black)
        } dynamicIsland: { context in
            DynamicIsland {
                DynamicIslandExpandedRegion(.center) {
                    ExpandedCenterView(context: context)
                }
                DynamicIslandExpandedRegion(.bottom) {
                    ExpandedBottomView(context: context)
                }
            } compactLeading: {
                CompactScoreView(
                    score: context.state.myTeamScore,
                    isServing: context.state.servingTeam == 0,
                    color: myTeamColor(context.state.themeId)
                )
            } compactTrailing: {
                CompactScoreView(
                    score: context.state.rivalsScore,
                    isServing: context.state.servingTeam == 1,
                    color: rivalsColor(context.state.themeId)
                )
            } minimal: {
                Text(context.state.myTeamScore)
                    .font(.system(size: 14, weight: .black))
                    .foregroundColor(myTeamColor(context.state.themeId))
            }
        }
    }
}

// MARK: - Lock Screen / Notification Banner

struct LockScreenView: View {
    let context: ActivityViewContext<PadelScoreAttributes>

    var state: PadelScoreAttributes.ContentState { context.state }
    var attrs: PadelScoreAttributes { context.attributes }

    var myColor: Color { myTeamColor(state.themeId) }
    var rvColor: Color { rivalsColor(state.themeId) }

    var body: some View {
        VStack(spacing: 10) {
            // Header
            HStack {
                Image(systemName: "tennisball.fill")
                    .foregroundColor(myColor)
                Text("PADEL LIVE")
                    .font(.system(size: 11, weight: .bold))
                    .tracking(2)
                    .foregroundColor(.white.opacity(0.6))
                Spacer()
                if !state.setScores.isEmpty {
                    Text(state.setScores.joined(separator: "  "))
                        .font(.system(size: 11, weight: .medium))
                        .foregroundColor(.white.opacity(0.5))
                }
            }

            // Main score
            HStack(alignment: .center, spacing: 0) {
                // My team
                VStack(spacing: 2) {
                    Text(attrs.myTeamName)
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundColor(myColor)
                    HStack(spacing: 4) {
                        if state.servingTeam == 0 {
                            Circle().fill(Color.yellow).frame(width: 6, height: 6)
                        }
                        Text(state.myTeamScore)
                            .font(.system(size: 44, weight: .black))
                            .foregroundColor(state.myTeamHasAdvantage ? myColor : .white)
                    }
                    Text("\(state.myTeamGames) games")
                        .font(.system(size: 10))
                        .foregroundColor(.white.opacity(0.5))
                }
                .frame(maxWidth: .infinity)

                // Divider + sets
                VStack(spacing: 4) {
                    Text("\(state.myTeamSetsWon) – \(state.rivalsSetsWon)")
                        .font(.system(size: 16, weight: .black))
                        .foregroundColor(.white)
                    Text("sets")
                        .font(.system(size: 9))
                        .foregroundColor(.white.opacity(0.4))
                }
                .frame(width: 60)

                // Rivals
                VStack(spacing: 2) {
                    Text(attrs.rivalsName)
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundColor(rvColor)
                    HStack(spacing: 4) {
                        Text(state.rivalsScore)
                            .font(.system(size: 44, weight: .black))
                            .foregroundColor(state.rivalsHaveAdvantage ? rvColor : .white)
                        if state.servingTeam == 1 {
                            Circle().fill(Color.yellow).frame(width: 6, height: 6)
                        }
                    }
                    Text("\(state.rivalsGames) games")
                        .font(.system(size: 10))
                        .foregroundColor(.white.opacity(0.5))
                }
                .frame(maxWidth: .infinity)
            }

            // Status bar
            statusBar
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
    }

    @ViewBuilder
    private var statusBar: some View {
        if state.isFinished {
            Text("Wedstrijd afgelopen")
                .font(.system(size: 11, weight: .medium))
                .foregroundColor(.white.opacity(0.5))
        } else if state.inTiebreak {
            statusPill("TIEBREAK", color: .yellow)
        } else if state.isDeuced {
            statusPill("DEUCE", color: .orange)
        } else if state.myTeamHasAdvantage {
            statusPill("VOORDEEL \(attrs.myTeamName)", color: myColor)
        } else if state.rivalsHaveAdvantage {
            statusPill("VOORDEEL \(attrs.rivalsName)", color: rvColor)
        } else {
            HStack(spacing: 4) {
                Circle().fill(Color.yellow).frame(width: 5, height: 5)
                Text("\(state.servingPlayerName) serveert")
                    .font(.system(size: 11))
                    .foregroundColor(.white.opacity(0.5))
            }
        }
    }

    private func statusPill(_ text: String, color: Color) -> some View {
        Text(text)
            .font(.system(size: 10, weight: .bold))
            .tracking(1)
            .foregroundColor(color)
            .padding(.horizontal, 10)
            .padding(.vertical, 3)
            .overlay(Capsule().stroke(color.opacity(0.6), lineWidth: 1))
    }
}

// MARK: - Dynamic Island Expanded

struct ExpandedCenterView: View {
    let context: ActivityViewContext<PadelScoreAttributes>

    var state: PadelScoreAttributes.ContentState { context.state }
    var attrs: PadelScoreAttributes { context.attributes }

    var body: some View {
        HStack(spacing: 0) {
            VStack(spacing: 1) {
                Text(attrs.myTeamName)
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundColor(myTeamColor(state.themeId))
                Text(state.myTeamScore)
                    .font(.system(size: 32, weight: .black))
                    .foregroundColor(state.myTeamHasAdvantage ? myTeamColor(state.themeId) : .white)
            }
            .frame(maxWidth: .infinity)

            VStack(spacing: 1) {
                Text("\(state.myTeamSetsWon)–\(state.rivalsSetsWon)")
                    .font(.system(size: 14, weight: .bold))
                    .foregroundColor(.white)
                Text("sets")
                    .font(.system(size: 8))
                    .foregroundColor(.white.opacity(0.4))
            }
            .frame(width: 44)

            VStack(spacing: 1) {
                Text(attrs.rivalsName)
                    .font(.system(size: 10, weight: .semibold))
                    .foregroundColor(rivalsColor(state.themeId))
                Text(state.rivalsScore)
                    .font(.system(size: 32, weight: .black))
                    .foregroundColor(state.rivalsHaveAdvantage ? rivalsColor(state.themeId) : .white)
            }
            .frame(maxWidth: .infinity)
        }
    }
}

struct ExpandedBottomView: View {
    let context: ActivityViewContext<PadelScoreAttributes>

    var state: PadelScoreAttributes.ContentState { context.state }

    var body: some View {
        HStack(spacing: 8) {
            // Games
            Text("\(state.myTeamGames) – \(state.rivalsGames) games")
                .font(.system(size: 11))
                .foregroundColor(.white.opacity(0.6))

            if state.inTiebreak {
                Text("• TIEBREAK")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundColor(.yellow)
            } else if state.isDeuced {
                Text("• DEUCE")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundColor(.orange)
            } else {
                Circle().fill(Color.yellow).frame(width: 5, height: 5)
                Text(state.servingPlayerName)
                    .font(.system(size: 11))
                    .foregroundColor(.white.opacity(0.6))
            }
        }
    }
}

// MARK: - Compact

struct CompactScoreView: View {
    let score: String
    let isServing: Bool
    let color: Color

    var body: some View {
        HStack(spacing: 3) {
            if isServing {
                Circle().fill(Color.yellow).frame(width: 5, height: 5)
            }
            Text(score)
                .font(.system(size: 16, weight: .black))
                .foregroundColor(color)
        }
        .padding(.horizontal, 4)
    }
}

// MARK: - Theme color helpers

private func myTeamColor(_ themeId: String) -> Color {
    switch themeId {
    case "neon":  return Color(red: 0.00, green: 1.00, blue: 0.53)
    case "court": return .white
    case "ocean": return Color(red: 0.00, green: 0.83, blue: 1.00)
    case "light": return Color(red: 0.09, green: 0.64, blue: 0.29)
    default:      return Color(red: 0.19, green: 0.82, blue: 0.35)
    }
}

private func rivalsColor(_ themeId: String) -> Color {
    switch themeId {
    case "neon":  return Color(red: 1.00, green: 0.42, blue: 0.21)
    case "court": return Color(red: 1.00, green: 0.84, blue: 0.00)
    case "ocean": return Color(red: 1.00, green: 0.42, blue: 0.61)
    case "light": return Color(red: 0.86, green: 0.15, blue: 0.15)
    default:      return Color(red: 1.00, green: 0.27, blue: 0.23)
    }
}
