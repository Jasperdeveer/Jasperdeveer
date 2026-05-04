import SwiftUI

struct ShareResultView: View {
    let record: MatchRecord
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            VStack(spacing: 24) {
                resultCard
                    .padding(.horizontal)

                ShareLink(
                    item: shareText,
                    subject: Text("Padel uitslag"),
                    message: Text(shareText)
                ) {
                    Label("Delen", systemImage: "square.and.arrow.up")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(PrimaryButtonStyle())
                .padding(.horizontal)

                Spacer()
            }
            .padding(.top)
            .background(Color.black.ignoresSafeArea())
            .navigationTitle("Resultaat")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Sluiten") { dismiss() }
                }
            }
        }
    }

    private var resultCard: some View {
        VStack(spacing: 16) {
            Text("🎾 Padel uitslag")
                .font(.title2)
                .fontWeight(.bold)

            HStack(spacing: 32) {
                VStack(spacing: 4) {
                    Text(record.myTeam.name)
                        .font(.headline)
                        .foregroundColor(record.winnerTeam == 0 ? .green : .primary)
                    Text("\(record.myTeamSetsWon)")
                        .font(.system(size: 56, weight: .black))
                        .foregroundColor(record.winnerTeam == 0 ? .green : .white)
                }
                Text("–")
                    .font(.title)
                    .foregroundColor(.secondary)
                VStack(spacing: 4) {
                    Text(record.rivals.name)
                        .font(.headline)
                        .foregroundColor(record.winnerTeam == 1 ? .red : .primary)
                    Text("\(record.rivalsSetsWon)")
                        .font(.system(size: 56, weight: .black))
                        .foregroundColor(record.winnerTeam == 1 ? .red : .white)
                }
            }

            Text(record.setScoreDisplay)
                .font(.subheadline)
                .foregroundColor(.secondary)

            Text(record.dateDisplay)
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .padding(24)
        .background(Color(white: 0.12))
        .clipShape(RoundedRectangle(cornerRadius: 20))
    }

    private var shareText: String {
        let winner = record.winnerTeam == 0 ? record.myTeam.name : record.rivals.name
        return """
        🎾 Padel uitslag
        \(record.myTeam.name) \(record.myTeamSetsWon) – \(record.rivalsSetsWon) \(record.rivals.name)
        (\(record.setScoreDisplay))
        Winnaar: \(winner) 🏆
        """
    }
}
