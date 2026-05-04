import SwiftUI

struct ContentView: View {
    @StateObject private var manager = MatchManager.shared
    @State private var showSetup = false

    var body: some View {
        TabView {
            scoringTab
                .tabItem { Label("Wedstrijd", systemImage: "sportscourt") }
            MatchHistoryView()
                .tabItem { Label("Geschiedenis", systemImage: "list.bullet") }
        }
        .sheet(isPresented: $showSetup) {
            MatchSetupView(isPresented: $showSetup)
        }
        .onAppear {
            if manager.state == nil { showSetup = true }
        }
    }

    private var scoringTab: some View {
        Group {
            if let state = manager.state {
                ScoringView(state: state)
            } else {
                VStack(spacing: 20) {
                    Image(systemName: "sportscourt.fill")
                        .font(.system(size: 60))
                        .foregroundColor(.green)
                    Text("Geen actieve wedstrijd")
                        .font(.title2)
                        .foregroundColor(.secondary)
                    Button("Nieuwe wedstrijd") { showSetup = true }
                        .buttonStyle(PrimaryButtonStyle())
                }
            }
        }
    }
}
