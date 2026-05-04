import SwiftUI

@main
struct PadelScoreApp: App {
    @StateObject private var themes = ThemeManager.shared

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(themes)
        }
    }
}
