"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import * as api from "@/lib/api"
import { formatDate } from "@/lib/utils"
import type { Recommendation } from "@/types"
import { toast } from "sonner"
import { Sparkles, ThumbsUp, ThumbsDown } from "lucide-react"

export default function RecommendationsPage() {
  const [recs, setRecs] = useState<Recommendation[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState("all")
  const [tickersInput, setTickersInput] = useState("")
  const [message, setMessage] = useState("")
  const [generating, setGenerating] = useState(false)

  const load = () => { api.getRecommendationHistory(100).then(r => setRecs(r.recommendations)).catch(() => {}).finally(() => setLoading(false)) }
  useEffect(() => { load() }, [])

  const filtered = filter === "all" ? recs : recs.filter(r =>
    filter === "buy" ? r.signal === "buy" || r.signal === "strong_buy" :
    filter === "sell" ? r.signal === "sell" || r.signal === "strong_sell" :
    r.signal === "hold"
  )

  const handleGenerate = async () => {
    const tickers = tickersInput.split(",").map(t => t.trim().toUpperCase()).filter(Boolean)
    if (!tickers.length) { toast.error("Enter at least one ticker"); return }
    setGenerating(true)
    try {
      await api.getRecommendation({ tickers, user_message: message || undefined })
      toast.success("Recommendation generated"); setTickersInput(""); setMessage(""); load()
    } catch (err: any) { toast.error(err.message) } finally { setGenerating(false) }
  }

  const badgeV = (s: string) => s === "buy" || s === "strong_buy" ? "success" as const : s === "sell" || s === "strong_sell" ? "destructive" as const : "warning" as const
  const badgeL = (s: string) => s === "strong_buy" ? "STRONG BUY" : s === "buy" ? "BUY" : s === "strong_sell" ? "STRONG SELL" : s === "sell" ? "SELL" : "HOLD"

  return (
    <div className="space-y-6">
      <div><h1 className="text-2xl font-bold tracking-tight">Recommendations</h1><p className="text-muted-foreground mt-1">AI-powered investment insights</p></div>

      <Card className="shadow-soft">
        <CardHeader><CardTitle className="text-sm font-semibold">Get New Recommendation</CardTitle></CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row gap-3">
            <Input value={tickersInput} onChange={(e) => setTickersInput(e.target.value)} placeholder="Tickers (e.g., AAPL, MSFT)" className="flex-1" />
            <Input value={message} onChange={(e) => setMessage(e.target.value)} placeholder="Optional context..." className="flex-1" />
            <Button onClick={handleGenerate} disabled={generating}><Sparkles size={16} className="mr-1.5" />{generating ? "Analyzing..." : "Analyze"}</Button>
          </div>
        </CardContent>
      </Card>

      <Tabs value={filter} onValueChange={setFilter}><TabsList><TabsTrigger value="all">All</TabsTrigger><TabsTrigger value="buy">Buy</TabsTrigger><TabsTrigger value="hold">Hold</TabsTrigger><TabsTrigger value="sell">Sell</TabsTrigger></TabsList></Tabs>

      {loading ? <p className="text-sm text-muted-foreground">Loading...</p>
      : filtered.length === 0 ? <Card className="shadow-soft"><CardContent className="py-12 text-center text-sm text-muted-foreground">No recommendations found.</CardContent></Card>
      : <div className="grid grid-cols-1 md:grid-cols-2 gap-4">{filtered.map((r) => (
        <Card key={r.id} className="shadow-soft hover:shadow-md transition-shadow">
          <CardContent className="p-5">
            <div className="flex items-start justify-between mb-3">
              <div>
                <div className="flex items-center gap-3"><span className="text-xl font-bold">{r.ticker}</span><Badge variant={badgeV(r.signal)}>{badgeL(r.signal)}</Badge></div>
                <p className="text-xs text-muted-foreground mt-1">{formatDate(r.created_at)}</p>
              </div>
              <span className="text-sm font-semibold">{(r.confidence * 100).toFixed(0)}%</span>
            </div>
            <p className="text-sm text-muted-foreground line-clamp-3 mb-4">{r.reasoning}</p>
            <div className="flex items-center gap-2 pt-3 border-t">
              <span className="text-xs text-muted-foreground">Helpful?</span>
              <Button variant="ghost" size="icon" className={`h-7 w-7 ${r.user_action === "followed" ? "text-success" : ""}`} onClick={async () => { await api.sendFeedback(r.id, "followed"); load() }}><ThumbsUp size={14} /></Button>
              <Button variant="ghost" size="icon" className={`h-7 w-7 ${r.user_action === "ignored" ? "text-destructive" : ""}`} onClick={async () => { await api.sendFeedback(r.id, "ignored"); load() }}><ThumbsDown size={14} /></Button>
            </div>
          </CardContent>
        </Card>
      ))}</div>}
    </div>
  )
}
