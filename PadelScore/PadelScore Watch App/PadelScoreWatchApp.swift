import SwiftUI

@main
struct PadelScoreWatchApp: App {
    @StateObject private var themes = ThemeManager.shared

    var body: some Scene {
        WindowGroup {
            WatchRootView()
                .environmentObject(themes)
        }
    }
}

struct WatchRootView: View {
    @StateObject private var manager = MatchManager.shared

    var body: some View {
        NavigationStack {
            if let state = manager.state {
                WatchScoringView(state: state)
            } else {
                WatchSetupView()
            }
        }
    }
}
