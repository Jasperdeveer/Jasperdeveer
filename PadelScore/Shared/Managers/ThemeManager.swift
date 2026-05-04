import SwiftUI
import Combine

final class ThemeManager: ObservableObject {
    static let shared = ThemeManager()

    @Published var current: AppTheme

    private var cancellables = Set<AnyCancellable>()

    private init() {
        let saved = UserDefaults.standard.string(forKey: "selectedTheme") ?? "night"
        current = AppTheme.all.first { $0.id == saved } ?? .night

        ConnectivityManager.shared.$receivedThemeId
            .compactMap { $0 }
            .filter { [weak self] id in id != self?.current.id }
            .receive(on: DispatchQueue.main)
            .sink { [weak self] id in self?.applyRemote(id: id) }
            .store(in: &cancellables)
    }

    func select(_ theme: AppTheme) {
        current = theme
        UserDefaults.standard.set(theme.id, forKey: "selectedTheme")
        ConnectivityManager.shared.sendTheme(id: theme.id)
    }

    private func applyRemote(id: String) {
        guard let theme = AppTheme.all.first(where: { $0.id == id }) else { return }
        current = theme
        UserDefaults.standard.set(id, forKey: "selectedTheme")
    }
}
