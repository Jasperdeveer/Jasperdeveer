import SwiftUI

struct ThemePickerView: View {
    @StateObject private var themes = ThemeManager.shared

    var body: some View {
        NavigationStack {
            ZStack {
                themes.current.background.ignoresSafeArea()

                ScrollView {
                    VStack(spacing: 16) {
                        ForEach(AppTheme.all) { theme in
                            ThemeCard(theme: theme, isSelected: themes.current.id == theme.id)
                                .onTapGesture { themes.select(theme) }
                        }
                    }
                    .padding(.horizontal, 20)
                    .padding(.vertical, 16)
                }
            }
            .navigationTitle("Stijl")
            .navigationBarTitleDisplayMode(.large)
        }
    }
}

struct ThemeCard: View {
    let theme: AppTheme
    let isSelected: Bool

    var body: some View {
        ZStack {
            // Background
            RoundedRectangle(cornerRadius: 20)
                .fill(theme.background)

            // Selection ring
            if isSelected {
                RoundedRectangle(cornerRadius: 20)
                    .stroke(theme.myTeamColor, lineWidth: 3)
            }

            HStack(spacing: 16) {
                // Mini scoreboard preview
                miniPreview

                // Theme info
                VStack(alignment: .leading, spacing: 6) {
                    HStack(spacing: 8) {
                        Text(theme.emoji)
                            .font(.title2)
                        Text(theme.name)
                            .font(.title3)
                            .fontWeight(.bold)
                            .foregroundColor(theme.primaryText)
                    }

                    // Color dots
                    HStack(spacing: 6) {
                        Circle().fill(theme.myTeamColor).frame(width: 14, height: 14)
                        Circle().fill(theme.rivalsColor).frame(width: 14, height: 14)
                        Circle().fill(theme.accent).frame(width: 14, height: 14)
                    }
                }

                Spacer()

                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.title2)
                        .foregroundColor(theme.myTeamColor)
                }
            }
            .padding(20)
        }
        .frame(height: 100)
        .shadow(color: isSelected ? theme.myTeamColor.opacity(0.4) : .clear, radius: 12)
        .animation(.spring(duration: 0.25), value: isSelected)
    }

    private var miniPreview: some View {
        VStack(spacing: 4) {
            HStack(spacing: 4) {
                scoreChip("40", color: theme.myTeamColor, bg: theme.card)
                scoreChip("30", color: theme.primaryText, bg: theme.card)
            }
            HStack(spacing: 4) {
                miniButton(color: theme.myTeamColor)
                miniButton(color: theme.rivalsColor)
            }
        }
    }

    private func scoreChip(_ text: String, color: Color, bg: Color) -> some View {
        Text(text)
            .font(.system(size: 13, weight: .black))
            .foregroundColor(color)
            .frame(width: 32, height: 24)
            .background(bg)
            .clipShape(RoundedRectangle(cornerRadius: 5))
    }

    private func miniButton(color: Color) -> some View {
        RoundedRectangle(cornerRadius: 5)
            .fill(color)
            .frame(width: 32, height: 14)
    }
}
