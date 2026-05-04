import SwiftUI

@main
struct PadelScoreApp: App {
    @StateObject private var themes = ThemeManager.shared

    init() {
        if #available(iOS 16.1, *) {
            _ = LiveActivityManager.shared
        }
    }

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(themes)
        }
    }
}
