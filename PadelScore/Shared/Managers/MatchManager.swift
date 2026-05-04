import Foundation
import Combine

final class MatchManager: ObservableObject {
    static let shared = MatchManager()

    @Published var state: MatchState? = nil
    @Published var history: [MatchState] = []  // undo stack (last 10)

    private let connectivity = ConnectivityManager.shared
    private var cancellables = Set<AnyCancellable>()

    private init() {
        connectivity.$receivedState
            .compactMap { $0 }
            .receive(on: DispatchQueue.main)
            .sink { [weak self] incoming in
                self?.state = incoming
            }
            .store(in: &cancellables)
    }

    func startMatch(state: MatchState) {
        self.state = state
        self.history = []
        sync()
    }

    func scorePoint(for teamIndex: Int) {
        guard var s = state else { return }
        if let snap = state { pushUndo(snap) }
        ScoreEngine.scorePoint(for: teamIndex, state: &s)
        state = s
        sync()
        if s.isFinished { finishMatch(s) }
    }

    func undoLastPoint() {
        guard let snap = history.last else { return }
        history.removeLast()
        state = snap
        sync()
    }

    func finishMatch(_ s: MatchState) {
        let record = MatchRecord.from(state: s)
        MatchStore.shared.save(record: record)
    }

    func endMatch() {
        guard var s = state else { return }
        s.isFinished = true
        s.endTime = Date()
        state = s
        finishMatch(s)
        state = nil
        history = []
    }

    private func pushUndo(_ snap: MatchState) {
        history.append(snap)
        if history.count > 10 { history.removeFirst() }
    }

    private func sync() {
        guard let s = state else { return }
        connectivity.send(state: s)
        connectivity.sendBackground(state: s)
    }
}
