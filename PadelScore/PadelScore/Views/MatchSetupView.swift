import SwiftUI

struct MatchSetupView: View {
    @Binding var isPresented: Bool

    @State private var myTeamName = "Mijn Team"
    @State private var myPlayer1 = ""
    @State private var myPlayer2 = ""
    @State private var rivalsName = "Tegenstanders"
    @State private var rivalsPlayer1 = ""
    @State private var rivalsPlayer2 = ""
    @State private var mode: MatchMode = .standard
    @State private var goldenPoint = false
    @State private var bestOf = 3
    @State private var servingTeam = 0
    @State private var servingPlayer = 0

    var body: some View {
        NavigationStack {
            Form {
                Section("Modus") {
                    Picker("Modus", selection: $mode) {
                        ForEach(MatchMode.allCases, id: \.self) { m in
                            Text(m.rawValue).tag(m)
                        }
                    }
                    .pickerStyle(.segmented)

                    if mode == .standard {
                        Toggle("Golden Point (bij deuce)", isOn: $goldenPoint)
                        Picker("Aantal sets", selection: $bestOf) {
                            Text("Best of 1").tag(1)
                            Text("Best of 3").tag(3)
                            Text("Best of 5").tag(5)
                        }
                    }
                }

                Section("Mijn Team") {
                    TextField("Teamnaam", text: $myTeamName)
                    TextField("Speler 1", text: $myPlayer1)
                    TextField("Speler 2", text: $myPlayer2)
                }

                Section("Tegenstanders") {
                    TextField("Teamnaam", text: $rivalsName)
                    TextField("Speler 1", text: $rivalsPlayer1)
                    TextField("Speler 2", text: $rivalsPlayer2)
                }

                Section("Service") {
                    Picker("Wie serveert eerst?", selection: $servingTeam) {
                        Text(myTeamName.isEmpty ? "Mijn Team" : myTeamName).tag(0)
                        Text(rivalsName.isEmpty ? "Tegenstanders" : rivalsName).tag(1)
                    }

                    Picker("Welke speler?", selection: $servingPlayer) {
                        Text(playerName(team: servingTeam, index: 0)).tag(0)
                        Text(playerName(team: servingTeam, index: 1)).tag(1)
                    }
                }
            }
            .navigationTitle("Nieuwe Wedstrijd")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Annuleer") { isPresented = false }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Start") { startMatch() }
                        .fontWeight(.bold)
                }
            }
        }
    }

    private func playerName(team: Int, index: Int) -> String {
        if team == 0 {
            let name = index == 0 ? myPlayer1 : myPlayer2
            return name.isEmpty ? "Speler \(index + 1)" : name
        } else {
            let name = index == 0 ? rivalsPlayer1 : rivalsPlayer2
            return name.isEmpty ? "Speler \(index + 1)" : name
        }
    }

    private func startMatch() {
        let my = Team(name: myTeamName.isEmpty ? "Mijn Team" : myTeamName,
                      player1: myPlayer1.isEmpty ? "Speler 1" : myPlayer1,
                      player2: myPlayer2.isEmpty ? "Speler 2" : myPlayer2)
        let rv = Team(name: rivalsName.isEmpty ? "Tegenstanders" : rivalsName,
                      player1: rivalsPlayer1.isEmpty ? "Speler 1" : rivalsPlayer1,
                      player2: rivalsPlayer2.isEmpty ? "Speler 2" : rivalsPlayer2)

        let state = MatchState(
            myTeam: my,
            rivals: rv,
            mode: mode,
            goldenPoint: goldenPoint,
            bestOf: bestOf,
            servingTeam: servingTeam,
            servingPlayerIndex: servingPlayer
        )

        MatchManager.shared.startMatch(state: state)
        isPresented = false
    }
}
