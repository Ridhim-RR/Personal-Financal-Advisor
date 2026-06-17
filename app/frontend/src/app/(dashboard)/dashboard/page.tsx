"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"
import { Skeleton } from "@/components/ui/skeleton"
import * as api from "@/lib/api"
import { formatCurrency } from "@/lib/utils"
import { Wallet, BarChart3, Eye, TrendingUp, ArrowRight, Shield, AlertTriangle } from "lucide-react"
import Link from "next/link"
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts"
import type { Holding, Recommendation } from "@/types"

const COLORS = ["hsl(var(--chart-1))", "hsl(var(--chart-2))", "hsl(var(--chart-3))", "hsl(var(--chart-4))", "hsl(var(--chart-5))"]

export default function DashboardPage() {
  const [holdings, setHoldings] = useState<Holding[]>([])
  const [recommendations, setRecommendations] = useState<Recommendation[]>([])
  const [watchlistCount, setWatchlistCount] = useState(0)
  const [userName, setUserName] = useState("")
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.getProfile().then((u) => setUserName(u.email.split("@")[0])).catch(() => {}),
      api.getHoldings().then((r) => setHoldings(r.holdings)).catch(() => {}),
      api.getRecommendationHistory(3).then((r) => setRecommendations(r.recommendations)).catch(() => {}),
      api.getWatchlists().then((r) => setWatchlistCount(r.watchlists.reduce((s, w) => s + w.tickers.length, 0))).catch(() => {}),
    ]).finally(() => setLoading(false))
  }, [])

  const totalValue = holdings.reduce((s, h) => s + h.shares * h.avg_cost, 0)
  const sectorData = [{ name: "Technology", value: 45 }, { name: "Healthcare", value: 20 }, { name: "Finance", value: 15 }, { name: "Consumer", value: 12 }, { name: "Energy", value: 8 }]
  const greeting = () => { const h = new Date().getHours(); if (h < 12) return "Good morning"; if (h < 17) return "Good afternoon"; return "Good evening" }
  const signalBadge = (s: string) => (s === "buy" || s === "strong_buy") ? "success" as const : (s === "sell" || s === "strong_sell") ? "destructive" as const : "warning" as const
  const signalLabel = (s: string) => s === "strong_buy" ? "STRONG BUY" : s === "buy" ? "BUY" : s === "sell" ? "SELL" : s === "strong_sell" ? "STRONG SELL" : "HOLD"

  if (loading) return <div className="space-y-6">{Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-28 rounded-xl" />)}</div>

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">{greeting()}, {userName || "Investor"}.</h1>
        <p className="text-muted-foreground mt-1">Here's an overview of your financial journey.</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: "Portfolio Value", value: formatCurrency(totalValue), sub: `${holdings.length} holdings`, icon: Wallet },
          { label: "Total Holdings", value: holdings.length, sub: `${new Set(holdings.map(h => h.ticker)).size} tickers`, icon: BarChart3 },
          { label: "AI Recommendations", value: recommendations.length, sub: recommendations[0] ? `Latest: ${recommendations[0].ticker}` : "None yet", icon: TrendingUp },
          { label: "Watchlist Items", value: watchlistCount, sub: "Tracked stocks", icon: Eye },
        ].map(({ label, value, sub, icon: Icon }) => (
          <Card key={label} className="shadow-soft">
            <CardContent className="p-5">
              <div className="flex items-center justify-between mb-3">
                <p className="text-xs font-medium text-muted-foreground">{label}</p>
                <Icon size={16} className="text-muted-foreground/60" />
              </div>
              <p className="text-2xl font-bold">{value}</p>
              <p className="text-xs text-muted-foreground mt-1">{sub}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 shadow-soft">
          <CardHeader><CardTitle className="text-sm font-semibold">Portfolio Allocation</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="h-48">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={sectorData} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value">
                      {sectorData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                    </Pie>
                    <Tooltip />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="space-y-3">
                {sectorData.map((s, i) => (
                  <div key={s.name} className="flex items-center justify-between">
                    <div className="flex items-center gap-2"><div className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: COLORS[i] }} /><span className="text-sm">{s.name}</span></div>
                    <span className="text-sm font-medium">{s.value}%</span>
                  </div>
                ))}
                {holdings.length > 0 && (
                  <div className="pt-3 border-t mt-3">
                    <p className="text-xs text-muted-foreground mb-2">Top Holdings</p>
                    {holdings.slice(0, 3).map((h) => (
                      <div key={h.ticker} className="flex items-center justify-between py-1">
                        <span className="text-sm font-medium">{h.ticker}</span>
                        <span className="text-sm text-muted-foreground">{formatCurrency(h.shares * h.avg_cost)}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        <div className="space-y-4">
          <Card className="shadow-soft">
            <CardHeader><CardTitle className="text-sm font-semibold flex items-center gap-2"><Shield size={14} className="text-primary" />AI Insights</CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <div className="rounded-lg bg-amber-500/5 border border-amber-500/10 p-3">
                <div className="flex gap-2"><AlertTriangle size={14} className="text-amber-500 mt-0.5 shrink-0" /><p className="text-xs text-muted-foreground">Your portfolio is heavily concentrated in technology stocks. Consider increasing diversification.</p></div>
              </div>
              <div className="rounded-lg bg-green-500/5 border border-green-500/10 p-3">
                <div className="flex gap-2"><Shield size={14} className="text-green-500 mt-0.5 shrink-0" /><p className="text-xs text-muted-foreground">Your risk level matches your investment horizon. Great alignment!</p></div>
              </div>
            </CardContent>
          </Card>

          <Card className="shadow-soft">
            <CardHeader className="flex flex-row items-center justify-between"><CardTitle className="text-sm font-semibold">Goals Progress</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              {[{ name: "Retirement", pct: 62 }, { name: "House Purchase", pct: 31 }].map((g) => (
                <div key={g.name}>
                  <div className="flex justify-between text-sm mb-1.5"><span className="font-medium">{g.name}</span><span className="text-muted-foreground">{g.pct}%</span></div>
                  <Progress value={g.pct} className="h-2" />
                </div>
              ))}
              <Link href="/goals"><Button variant="ghost" size="sm" className="w-full text-xs">Manage Goals <ArrowRight size={12} className="ml-1" /></Button></Link>
            </CardContent>
          </Card>
        </div>
      </div>

      <Card className="shadow-soft">
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle className="text-sm font-semibold">Recent Recommendations</CardTitle>
          <Link href="/recommendations"><Button variant="ghost" size="sm" className="text-xs">View All <ArrowRight size={12} className="ml-1" /></Button></Link>
        </CardHeader>
        <CardContent>
          {recommendations.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4 text-center">No recommendations yet. Ask the AI Advisor.</p>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
              {recommendations.slice(0, 3).map((r) => (
                <div key={r.id} className="rounded-xl border p-4 hover:shadow-md transition-shadow">
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-lg font-bold">{r.ticker}</span>
                    <Badge variant={signalBadge(r.signal)}>{signalLabel(r.signal)}</Badge>
                  </div>
                  <p className="text-xs text-muted-foreground mb-2">Confidence: {(r.confidence * 100).toFixed(0)}%</p>
                  <p className="text-xs text-muted-foreground line-clamp-2">{r.reasoning}</p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
