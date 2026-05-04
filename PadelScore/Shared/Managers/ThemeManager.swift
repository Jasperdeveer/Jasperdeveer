import SwiftUI
import Combine

final class ThemeManager: ObservableObject {
    static let shared = ThemeManager()

    @Published var current: AppTheme

    private init() {
        let saved = UserDefaults.standard.string(forKey: "selectedTheme") ?? "night"
        current = AppTheme.all.first { $0.id == saved } ?? .night
    }

    func select(_ theme: AppTheme) {
        current = theme
        UserDefaults.standard.set(theme.id, forKey: "selectedTheme")
    }
}
