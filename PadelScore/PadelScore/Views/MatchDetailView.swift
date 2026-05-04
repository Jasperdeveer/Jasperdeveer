import SwiftUI

struct MatchDetailView: View {
    let record: MatchRecord
    @State private var showShare = false

    var body: some View {
        ScrollView {
            VStack(spacing: 20) {
                // Score card
                scoreCard

                // Set breakdown
                if !record.completedSets.isEmpty {
                    setBreakdown
                }

                // Teams
                teamsSection

                // Share button
                Button(action: { showShare = true }) {
                    Label("Resultaat delen", systemImage: "square.and.arrow.up")
                        .frame(maxWidth: .infinity)
                }
                .buttonStyle(PrimaryButtonStyle())
                .padding(.horizontal)
            }
            .padding(.vertical)
        }
        .background(Color.black.ignoresSafeArea())
        .navigationTitle("Wedstrijd detail")
        .navigationBarTitleDisplayMode(.inline)
        .sheet(isPresented: $showShare) {
            ShareResultView(record: record)
        }
    }

    private var scoreCard: some View {
        VStack(spacing: 12) {
            Text(record.dateDisplay)
                .font(.caption)
                .foregroundColor(.secondary)

            HStack(spacing: 24) {
                VStack {
                    Text(record.myTeam.name)
                        .font(.headline)
                    Text("\(record.myTeamSetsWon)")
                        .font(.system(size: 64, weight: .black))
                        .foregroundColor(record.winnerTeam == 0 ? .green : .white)
                    if record.winnerTeam == 0 {
                        Text("GEWONNEN")
                            .font(.caption)
                            .foregroundColor(.green)
                            .fontWeight(.bold)
                    }
                }
                Text("–")
                    .font(.system(size: 32, weight: .light))
                    .foregroundColor(.secondary)
                VStack {
                    Text(record.rivals.name)
                        .font(.headline)
                    Text("\(record.rivalsSetsWon)")
                        .font(.system(size: 64, weight: .black))
                        .foregroundColor(record.winnerTeam == 1 ? .red : .white)
                    if record.winnerTeam == 1 {
                        Text("GEWONNEN")
                            .font(.caption)
                            .foregroundColor(.red)
                            .fontWeight(.bold)
                    }
                }
            }

            Text("Duur: \(record.durationDisplay)")
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .padding()
        .background(Color(white: 0.1))
        .clipShape(RoundedRectangle(cornerRadius: 16))
        .padding(.horizontal)
    }

    private var setBreakdown: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Sets")
                .font(.headline)
                .padding(.horizontal)

            ForEach(Array(record.completedSets.enumerated()), id: \.offset) { i, set in
                HStack {
                    Text("Set \(i + 1)")
                        .foregroundColor(.secondary)
                    Spacer()
                    Text("\(set.myTeam)")
                        .fontWeight(.bold)
                        .foregroundColor(set.myTeam > set.rivals ? .green : .white)
                    Text("–").foregroundColor(.secondary)
                    Text("\(set.rivals)")
                        .fontWeight(.bold)
                        .foregroundColor(set.rivals > set.myTeam ? .red : .white)
                }
                .padding(.horizontal)
                .padding(.vertical, 6)
                .background(Color(white: 0.1))
                .clipShape(RoundedRectangle(cornerRadius: 8))
                .padding(.horizontal)
            }
        }
    }

    private var teamsSection: some View {
        HStack(alignment: .top, spacing: 16) {
            teamCard(team: record.myTeam, color: .green)
            teamCard(team: record.rivals, color: .red)
        }
        .padding(.horizontal)
    }

    private func teamCard(team: Team, color: Color) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(team.name)
                .font(.headline)
                .foregroundColor(color)
            Text(team.player1)
                .font(.subheadline)
            Text(team.player2)
                .font(.subheadline)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(Color(white: 0.1))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}
