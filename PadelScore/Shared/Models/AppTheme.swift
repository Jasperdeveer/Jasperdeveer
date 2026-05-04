import SwiftUI

struct AppTheme: Identifiable, Codable {
    let id: String
    let name: String
    let emoji: String

    // Stored as hex strings for Codable
    let backgroundHex: String
    let cardHex: String
    let myTeamHex: String
    let rivalsHex: String
    let primaryTextHex: String
    let secondaryTextHex: String
    let accentHex: String

    var background: Color    { Color(hex: backgroundHex) }
    var card: Color          { Color(hex: cardHex) }
    var myTeamColor: Color   { Color(hex: myTeamHex) }
    var rivalsColor: Color   { Color(hex: rivalsHex) }
    var primaryText: Color   { Color(hex: primaryTextHex) }
    var secondaryText: Color { Color(hex: secondaryTextHex) }
    var accent: Color        { Color(hex: accentHex) }

    static let all: [AppTheme] = [.night, .neon, .court, .ocean, .light]

    // MARK: - Themes

    static let night = AppTheme(
        id: "night",
        name: "Nacht",
        emoji: "🌑",
        backgroundHex: "#000000",
        cardHex: "#1C1C1E",
        myTeamHex: "#30D158",
        rivalsHex: "#FF453A",
        primaryTextHex: "#FFFFFF",
        secondaryTextHex: "#8E8E93",
        accentHex: "#FF9F0A"
    )

    static let neon = AppTheme(
        id: "neon",
        name: "Neon",
        emoji: "⚡",
        backgroundHex: "#0D0D0D",
        cardHex: "#141414",
        myTeamHex: "#00FF87",
        rivalsHex: "#FF6B35",
        primaryTextHex: "#FFFFFF",
        secondaryTextHex: "#888888",
        accentHex: "#BF5AF2"
    )

    static let court = AppTheme(
        id: "court",
        name: "Court",
        emoji: "🎾",
        backgroundHex: "#1A4731",
        cardHex: "#0F2E1F",
        myTeamHex: "#FFFFFF",
        rivalsHex: "#FFD700",
        primaryTextHex: "#FFFFFF",
        secondaryTextHex: "#A8D5B5",
        accentHex: "#FFD700"
    )

    static let ocean = AppTheme(
        id: "ocean",
        name: "Oceaan",
        emoji: "🌊",
        backgroundHex: "#0A1628",
        cardHex: "#0F2040",
        myTeamHex: "#00D4FF",
        rivalsHex: "#FF6B9D",
        primaryTextHex: "#FFFFFF",
        secondaryTextHex: "#5F8AAA",
        accentHex: "#FFE566"
    )

    static let light = AppTheme(
        id: "light",
        name: "Licht",
        emoji: "☀️",
        backgroundHex: "#F2F2F7",
        cardHex: "#FFFFFF",
        myTeamHex: "#16A34A",
        rivalsHex: "#DC2626",
        primaryTextHex: "#000000",
        secondaryTextHex: "#6B7280",
        accentHex: "#EA580C"
    )
}

// MARK: - Color hex support
extension Color {
    init(hex: String) {
        var h = hex.trimmingCharacters(in: .whitespacesAndNewlines)
        if h.hasPrefix("#") { h = String(h.dropFirst()) }
        var rgb: UInt64 = 0
        Scanner(string: h).scanHexInt64(&rgb)
        let r = Double((rgb >> 16) & 0xFF) / 255
        let g = Double((rgb >> 8) & 0xFF) / 255
        let b = Double(rgb & 0xFF) / 255
        self.init(red: r, green: g, blue: b)
    }
}
