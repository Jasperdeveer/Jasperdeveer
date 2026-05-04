import Foundation

final class MatchStore: ObservableObject {
    static let shared = MatchStore()

    @Published var history: [MatchRecord] = []

    private let key = "match_history"

    init() { load() }

    func save(record: MatchRecord) {
        history.insert(record, at: 0)
        persist()
    }

    func delete(at offsets: IndexSet) {
        history.remove(atOffsets: offsets)
        persist()
    }

    private func persist() {
        if let data = try? JSONEncoder().encode(history) {
            UserDefaults.standard.set(data, forKey: key)
        }
    }

    private func load() {
        guard let data = UserDefaults.standard.data(forKey: key),
              let records = try? JSONDecoder().decode([MatchRecord].self, from: data)
        else { return }
        history = records
    }
}
