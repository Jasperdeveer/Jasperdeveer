import ActivityKit
import Combine
import Foundation

@available(iOS 16.1, *)
final class LiveActivityManager {
    static let shared = LiveActivityManager()

    private var activity: Activity<PadelScoreAttributes>?
    private var cancellables = Set<AnyCancellable>()

    private init() {
        MatchManager.shared.$state
            .receive(on: DispatchQueue.main)
            .sink { [weak self] state in
                guard let self else { return }
                if let state {
                    if self.activity == nil && !state.isFinished {
                        self.start(state)
                    } else {
                        self.update(state)
                    }
                } else {
                    self.end()
                }
            }
            .store(in: &cancellables)
    }

    // MARK: - Private

    private func start(_ state: MatchState) {
        guard ActivityAuthorizationInfo().areActivitiesEnabled else { return }

        let attrs = PadelScoreAttributes(
            myTeamName: state.myTeam.name,
            rivalsName: state.rivals.name
        )
        let content = ActivityContent(state: contentState(from: state), staleDate: nil)

        do {
            activity = try Activity.request(attributes: attrs, content: content)
        } catch {
            // Silently fail — Live Activity is non-critical
        }
    }

    private func update(_ state: MatchState) {
        guard let activity else { return }
        let content = ActivityContent(state: contentState(from: state), staleDate: nil)
        Task {
            if state.isFinished {
                await activity.end(content, dismissalPolicy: .after(.now + 60))
                self.activity = nil
            } else {
                await activity.update(content)
            }
        }
    }

    private func end() {
        Task {
            await activity?.end(dismissalPolicy: .immediate)
            activity = nil
        }
    }

    private func contentState(from state: MatchState) -> PadelScoreAttributes.ContentState {
        PadelScoreAttributes.ContentState(
            myTeamScore: state.myTeamScoreDisplay,
            rivalsScore: state.rivalsScoreDisplay,
            myTeamGames: state.myTeamGames,
            rivalsGames: state.rivalsGames,
            myTeamSetsWon: state.myTeamSetsWon,
            rivalsSetsWon: state.rivalsSetsWon,
            setScores: state.completedSets.map { "\($0.myTeam)-\($0.rivals)" },
            servingPlayerName: state.servingPlayerName,
            servingTeam: state.servingTeam,
            isDeuced: state.isDeuced,
            myTeamHasAdvantage: state.myTeamHasAdvantage,
            rivalsHaveAdvantage: state.rivalsHaveAdvantage,
            inTiebreak: state.inTiebreak,
            isFinished: state.isFinished,
            themeId: ThemeManager.shared.current.id
        )
    }
}
