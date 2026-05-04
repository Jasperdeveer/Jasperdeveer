import SwiftUI

@main
struct PadelScoreWatchApp: App {
    var body: some Scene {
        WindowGroup {
            WatchRootView()
        }
    }
}

struct WatchRootView: View {
    @StateObject private var manager = MatchManager.shared

    var body: some View {
        if let state = manager.state {
            WatchScoringView(state: state)
        } else {
            WatchSetupView()
        }
    }
}
