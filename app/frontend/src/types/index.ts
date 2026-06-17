export interface User { user_id: string; email: string; profile?: UserProfile }

export interface UserProfile {
  risk_appetite: "low" | "moderate" | "high"
  investment_goal: string
  investment_horizon: "short" | "medium" | "long"
  preferred_sectors: string[]
  excluded_sectors: string[]
  initial_capital: number
}

export interface Holding { ticker: string; shares: number; avg_cost: number; target_allocation: number }

export interface Watchlist { id: string; name: string; tickers: string[] }

export interface Recommendation {
  id: string; ticker: string
  signal: "strong_buy" | "buy" | "hold" | "sell" | "strong_sell"
  confidence: number; reasoning: string; user_action: string | null; created_at: string
}

export interface ChatRequest { message: string; tickers?: string[] }

export interface ChatResponse {
  decisions: Record<string, { action: string; confidence: number; reasoning: string }>
  analyst_signals: Record<string, any>
}

export interface AuthResponse { access_token: string; token_type: string; user_id: string }
