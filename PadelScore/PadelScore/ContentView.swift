import SwiftUI

struct ContentView: View {
    @StateObject private var manager = MatchManager.shared
    @StateObject private var themes = ThemeManager.shared
    @State private var showSetup = false

    var theme: AppTheme { themes.current }

    var body: some View {
        TabView {
            scoringTab
                .tabItem { Label("Wedstrijd", systemImage: "sportscourt") }
            MatchHistoryView()
                .tabItem { Label("Geschiedenis", systemImage: "list.bullet") }
            ThemePickerView()
                .tabItem { Label("Stijl", systemImage: "paintpalette") }
        }
        .preferredColorScheme(theme.id == "light" ? .light : .dark)
        .sheet(isPresented: $showSetup) {
            MatchSetupView(isPresented: $showSetup)
        }
        .onAppear {
            if manager.state == nil { showSetup = true }
        }
    }

    private var scoringTab: some View {
        NavigationStack {
            Group {
                if let state = manager.state {
                    ScoringView(state: state)
                } else {
                    ZStack {
                        theme.background.ignoresSafeArea()
                        VStack(spacing: 24) {
                            Text(theme.emoji)
                                .font(.system(size: 64))
                            Text("Geen actieve wedstrijd")
                                .font(.title2)
                                .foregroundColor(theme.secondaryText)
                            Button("Nieuwe wedstrijd") { showSetup = true }
                                .buttonStyle(PrimaryButtonStyle(color: theme.myTeamColor))
                        }
                    }
                    .navigationTitle("PadelScore")
                }
            }
        }
    }
}
