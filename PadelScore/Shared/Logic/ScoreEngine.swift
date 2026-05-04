import Foundation

// All scoring logic. Pure functions on MatchState.
enum ScoreEngine {

    static func scorePoint(for teamIndex: Int, state: inout MatchState) {
        guard !state.isFinished else { return }

        if state.mode == .americano {
            scoreAmericano(for: teamIndex, state: &state)
            return
        }

        if state.inTiebreak {
            scoreTiebreakPoint(for: teamIndex, state: &state)
        } else {
            scoreGamePoint(for: teamIndex, state: &state)
        }
    }

    static func undoLastPoint(state: inout MatchState, snapshot: MatchState) {
        state = snapshot
    }

    // MARK: - Americano

    private static func scoreAmericano(for teamIndex: Int, state: inout MatchState) {
        if teamIndex == 0 { state.americanoMyTeam += 1 }
        else { state.americanoRivals += 1 }
    }

    // MARK: - Game scoring

    private static func scoreGamePoint(for teamIndex: Int, state: inout MatchState) {
        if teamIndex == 0 { state.myTeamPoints += 1 }
        else { state.rivalsPoints += 1 }

        let my = state.myTeamPoints
        let rv = state.rivalsPoints

        // Golden point: at deuce (3-3), one point decides
        if state.goldenPoint && my == 3 && rv == 3 {
            return  // next point wins the game
        }

        // Check win
        if gameWon(my: my, rivals: rv, golden: state.goldenPoint) {
            winGame(for: teamIndex, state: &state)
        } else if gameWon(my: rv, rivals: my, golden: state.goldenPoint) {
            winGame(for: 1 - teamIndex, state: &state)
        }
    }

    private static func gameWon(my: Int, rivals: Int, golden: Bool) -> Bool {
        if golden {
            // At deuce (3-3) next point wins; or normal win before deuce
            if my >= 4 && rivals <= 2 { return true }
            if my >= 4 && rivals == 3 { return true }  // was already deuce, one more
            if my == 4 && rivals == 3 { return true }
            return my > 3 && my > rivals
        } else {
            return my >= 4 && my - rivals >= 2
        }
    }

    private static func winGame(for teamIndex: Int, state: inout MatchState) {
        state.myTeamPoints = 0
        state.rivalsPoints = 0

        if teamIndex == 0 { state.myTeamGames += 1 }
        else { state.rivalsGames += 1 }

        advanceServeAfterGame(state: &state)
        checkSetWin(state: &state)
    }

    // MARK: - Tiebreak scoring

    private static func scoreTiebreakPoint(for teamIndex: Int, state: inout MatchState) {
        if teamIndex == 0 { state.myTeamPoints += 1 }
        else { state.rivalsPoints += 1 }

        state.tiebreakPointsPlayed += 1

        // Serve changes: first point, then every 2
        if state.tiebreakPointsPlayed == 1 {
            switchServingTeam(state: &state)
        } else if state.tiebreakPointsPlayed > 1 && (state.tiebreakPointsPlayed - 1) % 2 == 0 {
            switchServingTeam(state: &state)
        }

        let my = state.myTeamPoints
        let rv = state.rivalsPoints

        // Win tiebreak: first to 7 (or 10 for super tiebreak), win by 2
        let target = 7
        if (my >= target || rv >= target) && abs(my - rv) >= 2 {
            let winner = my > rv ? 0 : 1
            winTiebreak(for: winner, state: &state)
        }
    }

    private static func winTiebreak(for teamIndex: Int, state: inout MatchState) {
        state.myTeamPoints = 0
        state.rivalsPoints = 0
        state.inTiebreak = false
        state.tiebreakPointsPlayed = 0

        if teamIndex == 0 { state.myTeamGames += 1 }
        else { state.rivalsGames += 1 }

        checkSetWin(state: &state)
    }

    // MARK: - Set logic

    private static func checkSetWin(state: inout MatchState) {
        let my = state.myTeamGames
        let rv = state.rivalsGames

        // Tiebreak condition: 6-6
        if my == 6 && rv == 6 && !state.inTiebreak {
            state.inTiebreak = true
            return
        }

        // Set win: first to 6 with 2 game lead, or 7-5
        let winner: Int?
        if my >= 6 && my - rv >= 2 { winner = 0 }
        else if rv >= 6 && rv - my >= 2 { winner = 1 }
        else if my == 7 { winner = 0 }
        else if rv == 7 { winner = 1 }
        else { winner = nil }

        guard let w = winner else { return }

        state.completedSets.append(SetScore(myTeam: my, rivals: rv))
        state.myTeamGames = 0
        state.rivalsGames = 0

        checkMatchWin(setWinner: w, state: &state)
    }

    private static func checkMatchWin(setWinner: Int, state: inout MatchState) {
        let setsNeeded = (state.bestOf + 1) / 2

        if setWinner == 0 && state.myTeamSetsWon >= setsNeeded {
            state.isFinished = true
            state.winnerTeam = 0
            state.endTime = Date()
        } else if setWinner == 1 && state.rivalsSetsWon >= setsNeeded {
            state.isFinished = true
            state.winnerTeam = 1
            state.endTime = Date()
        } else {
            advanceServeAfterGame(state: &state)
        }
    }

    // MARK: - Serve rotation

    private static func advanceServeAfterGame(state: inout MatchState) {
        switchServingTeam(state: &state)
    }

    private static func switchServingTeam(state: inout MatchState) {
        state.servingTeam = 1 - state.servingTeam
        // Rotate player within team every two games they serve
        // Simple approach: alternate player each time this team serves
        state.servingPlayerIndex = 1 - state.servingPlayerIndex
    }
}
