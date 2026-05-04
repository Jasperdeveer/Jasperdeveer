import SwiftUI

struct WatchSetupView: View {
    @State private var myTeamName = "Mijn Team"
    @State private var rivalsName = "Tegenstanders"
    @State private var servingTeam = 0
    @State private var goldenPoint = false

    var body: some View {
        ScrollView {
            VStack(spacing: 10) {
                Image(systemName: "tennisball.fill")
                    .font(.system(size: 28))
                    .foregroundColor(.green)

                Text("Nieuw spel")
                    .font(.headline)

                Picker("Serveert", selection: $servingTeam) {
                    Text(myTeamName).tag(0)
                    Text(rivalsName).tag(1)
                }

                Toggle("Golden point", isOn: $goldenPoint)
                    .font(.caption)

                Button("Start") { startQuickMatch() }
                    .buttonStyle(.borderedProminent)
                    .tint(.green)

                Text("Stel teamsnamen in via iPhone")
                    .font(.system(size: 10))
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
            }
            .padding(.horizontal, 4)
        }
        .navigationTitle("Padel")
    }

    private func startQuickMatch() {
        let my = Team(name: myTeamName, player1: "Speler 1", player2: "Speler 2")
        let rv = Team(name: rivalsName, player1: "Speler 1", player2: "Speler 2")
        let state = MatchState(
            myTeam: my, rivals: rv,
            mode: .standard, goldenPoint: goldenPoint,
            servingTeam: servingTeam
        )
        MatchManager.shared.startMatch(state: state)
    }
}
