import type { AuthResponse, ChatRequest, ChatResponse, Holding, Recommendation, User, UserProfile, Watchlist } from "@/types"

const API_BASE = "http://localhost:8000/api/v1"

function getToken(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem("advisor_token")
}

export function isAuthenticated(): boolean {
  if (typeof window === "undefined") return false
  return !!localStorage.getItem("advisor_token")
}

function redirectToLogin() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("advisor_token")
    localStorage.removeItem("advisor_user_id")
    window.location.href = "/login"
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = { "Content-Type": "application/json" }
  Object.assign(headers, options.headers as Record<string, string>)
  if (token) headers["Authorization"] = `Bearer ${token}`
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers, credentials: "include" })
  if (res.status === 401) { redirectToLogin(); throw new Error("Unauthorized") }
  if (!res.ok) { const body = await res.json().catch(() => ({ detail: res.statusText })); throw new Error(body.detail || res.statusText) }
  return res.json()
}

export async function register(email: string, password: string): Promise<AuthResponse> {
  const data = await request<AuthResponse>("/auth/register", { method: "POST", body: JSON.stringify({ email, password }) })
  localStorage.setItem("advisor_token", data.access_token); localStorage.setItem("advisor_user_id", data.user_id)
  return data
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const data = await request<AuthResponse>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) })
  localStorage.setItem("advisor_token", data.access_token); localStorage.setItem("advisor_user_id", data.user_id)
  return data
}

export async function logout(): Promise<void> {
  await request("/auth/logout", { method: "POST" }).catch(() => {})
  localStorage.removeItem("advisor_token"); localStorage.removeItem("advisor_user_id")
}

export async function getProfile(): Promise<User> { return request<User>("/users/me") }
export async function updateProfile(data: Partial<UserProfile>): Promise<{ message: string }> {
  return request("/users/me", { method: "PUT", body: JSON.stringify(data) })
}
export async function getHoldings(): Promise<{ holdings: Holding[] }> { return request("/portfolio/") }
export async function addHolding(ticker: string, shares: number, avgCost: number): Promise<{ message: string }> {
  return request("/portfolio/holdings", { method: "POST", body: JSON.stringify({ ticker, shares, avg_cost: avgCost, target_allocation: 0 }) })
}
export async function deleteHolding(ticker: string): Promise<{ message: string }> {
  return request(`/portfolio/holdings/${ticker}`, { method: "DELETE" })
}
export async function getWatchlists(): Promise<{ watchlists: Watchlist[] }> { return request("/watchlists/") }
export async function createWatchlist(name: string): Promise<Watchlist> {
  return request("/watchlists/", { method: "POST", body: JSON.stringify({ name, tickers: [] }) })
}
export async function deleteWatchlist(id: string): Promise<{ message: string }> { return request(`/watchlists/${id}`, { method: "DELETE" }) }
export async function addTickerToWatchlist(watchlistId: string, ticker: string): Promise<Watchlist> {
  return request(`/watchlists/${watchlistId}/tickers`, { method: "POST", body: JSON.stringify({ ticker }) })
}
export async function removeTickerFromWatchlist(watchlistId: string, ticker: string): Promise<Watchlist> {
  return request(`/watchlists/${watchlistId}/tickers/${ticker}`, { method: "DELETE" })
}
export async function getRecommendationHistory(limit = 50): Promise<{ recommendations: Recommendation[] }> {
  return request(`/recommendations/history?limit=${limit}`)
}
export async function getRecommendation(req: { tickers: string[]; user_message?: string }): Promise<ChatResponse> {
  return request("/recommendations/", { method: "POST", body: JSON.stringify(req) })
}
export async function sendFeedback(recommendationId: string, action: string): Promise<{ message: string }> {
  return request(`/recommendations/${recommendationId}/feedback`, { method: "POST", body: JSON.stringify({ action }) })
}
export async function chat(req: ChatRequest): Promise<ChatResponse> {
  return request("/chat/", { method: "POST", body: JSON.stringify(req) })
}
