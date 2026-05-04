import Foundation
import WatchConnectivity

final class ConnectivityManager: NSObject, ObservableObject, WCSessionDelegate {
    static let shared = ConnectivityManager()

    @Published var receivedState: MatchState? = nil

    private override init() {
        super.init()
        if WCSession.isSupported() {
            WCSession.default.delegate = self
            WCSession.default.activate()
        }
    }

    func send(state: MatchState) {
        guard WCSession.default.isReachable,
              let data = try? JSONEncoder().encode(state)
        else { return }
        WCSession.default.sendMessage(["state": data], replyHandler: nil)
    }

    func sendBackground(state: MatchState) {
        guard WCSession.default.activationState == .activated,
              let data = try? JSONEncoder().encode(state)
        else { return }
        try? WCSession.default.updateApplicationContext(["state": data])
    }

    // MARK: - WCSessionDelegate

    func session(_ session: WCSession, didReceiveMessage message: [String: Any]) {
        guard let data = message["state"] as? Data,
              let state = try? JSONDecoder().decode(MatchState.self, from: data)
        else { return }
        DispatchQueue.main.async { self.receivedState = state }
    }

    func session(_ session: WCSession, didReceiveApplicationContext applicationContext: [String: Any]) {
        guard let data = applicationContext["state"] as? Data,
              let state = try? JSONDecoder().decode(MatchState.self, from: data)
        else { return }
        DispatchQueue.main.async { self.receivedState = state }
    }

    func session(_ session: WCSession, activationDidCompleteWith activationState: WCSessionActivationState, error: Error?) {}

    #if os(iOS)
    func sessionDidBecomeInactive(_ session: WCSession) {}
    func sessionDidDeactivate(_ session: WCSession) { session.activate() }
    #endif
}
