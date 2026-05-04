import SwiftUI

struct MatchHistoryView: View {
    @StateObject private var store = MatchStore.shared

    var body: some View {
        NavigationStack {
            Group {
                if store.history.isEmpty {
                    ContentUnavailableView(
                        "Geen wedstrijden",
                        systemImage: "sportscourt",
                        description: Text("Gespeelde wedstrijden verschijnen hier")
                    )
                } else {
                    List {
                        ForEach(store.history) { record in
                            NavigationLink(destination: MatchDetailView(record: record)) {
                                MatchRowView(record: record)
                            }
                        }
                        .onDelete(perform: store.delete)
                    }
                    .listStyle(.insetGrouped)
                }
            }
            .navigationTitle("Geschiedenis")
        }
    }
}

struct MatchRowView: View {
    let record: MatchRecord

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(record.myTeam.name)
                    .fontWeight(.semibold)
                    .foregroundColor(record.winnerTeam == 0 ? .green : .primary)
                Spacer()
                Text("\(record.myTeamSetsWon) – \(record.rivalsSetsWon)")
                    .font(.headline)
                    .fontWeight(.bold)
                Spacer()
                Text(record.rivals.name)
                    .fontWeight(.semibold)
                    .foregroundColor(record.winnerTeam == 1 ? .red : .primary)
            }

            Text(record.setScoreDisplay)
                .font(.caption)
                .foregroundColor(.secondary)

            HStack {
                Text(record.dateDisplay)
                Spacer()
                Text(record.durationDisplay)
            }
            .font(.caption2)
            .foregroundColor(.secondary)
        }
        .padding(.vertical, 4)
    }
}
