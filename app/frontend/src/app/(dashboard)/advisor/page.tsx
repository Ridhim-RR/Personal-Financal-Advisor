"use client"

import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { Badge } from "@/components/ui/badge"
import { Bot, User, Send, Loader2, Sparkles } from "lucide-react"
import * as api from "@/lib/api"
import { toast } from "sonner"

interface Message {
  role: "user" | "assistant"
  content: string
  decisions?: Record<string, any>
}

const COMPANY_TICKERS: Record<string, string> = {
  tesla: "TSLA", apple: "AAPL", microsoft: "MSFT",
  google: "GOOGL", alphabet: "GOOGL", nvidia: "NVDA",
  amazon: "AMZN", meta: "META", netflix: "NFLX",
  amd: "AMD", intel: "INTC", paypal: "PYPL",
  disney: "DIS", uber: "UBER", lyft: "LYFT",
  shopify: "SHOP", zoom: "ZM", palantir: "PLTR",
  coinbase: "COIN", snowflake: "SNOW", datadog: "DDOG",
  stripe: "STRIPE", nio: "NIO", rivian: "RIVN",
  lucid: "LCID", ford: "F", toyota: "TM",
  honda: "HMC", boeing: "BA", lockheed: "LMT",
  exxon: "XOM", chevron: "CVX", shell: "SHEL",
  berkshire: "BRK.B", visa: "V", mastercard: "MA",
  jpmorgan: "JPM", goldman: "GS", morgan: "MS",
  wells: "WFC", citi: "C", amex: "AXP",
  walmart: "WMT", target: "TGT", costco: "COST",
  mcdonalds: "MCD", starbucks: "SBUX", nike: "NKE",
  coca: "KO", pepsi: "PEP", pfizer: "PFE",
  moderna: "MRNA", johnson: "JNJ", merck: "MRK",
  abbott: "ABT", eli: "LLY", novartis: "NVS",
  astrazeneca: "AZN", gsk: "GSK", sanofi: "SNY",
  atandt: "T", verizon: "VZ", tmobile: "TMUS",
  comcast: "CMCSA", honeywell: "HON",
  caterpillar: "CAT", ge: "GE", "3m": "MMM", ibm: "IBM",
  oracle: "ORCL", sap: "SAP", qualcomm: "QCOM",
  broadcom: "AVGO", micron: "MU", asml: "ASML",
  intuit: "INTU", adobe: "ADBE", salesforce: "CRM",
  square: "SQ", block: "SQ",
  robinhood: "HOOD", sofi: "SOFI", draftkings: "DKNG",
  peloton: "PTON", beyond: "BYND", roku: "ROKU",
  snap: "SNAP", pinterest: "PINS", twitter: "TWTR",
  spotify: "SPOT", activision: "ATVI", ea: "EA",
  take: "TTWO", unity: "U", roblox: "RBLX",
}

const SUGGESTED = ["Should I buy Tesla?", "Analyze my portfolio risk", "How can I diversify?", "What stocks fit my goals?"]

export default function AdvisorPage() {
  const [messages, setMessages] = useState<Message[]>([{
    role: "assistant",
    content: "Hello! I'm your personal AI financial advisor. I can help you analyze stocks, review your portfolio, and make investment decisions aligned with your goals. What would you like to explore?",
  }])
  const [input, setInput] = useState("")
  const [sending, setSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }) }, [messages])

  const extractTickers = (msg: string): string[] => {
    const allCaps = msg.match(/\b[A-Z]{2,5}\b/g) || []
    const lower = msg.toLowerCase()
    const fromNames = Object.entries(COMPANY_TICKERS)
      .filter(([name]) => lower.includes(name))
      .map(([, ticker]) => ticker)
    const merged = [...new Set([...allCaps, ...fromNames])]
    return merged.slice(0, 5)
  }

  const handleSend = async (text?: string) => {
    const msg = (text || input).trim()
    if (!msg || sending) return
    setInput("")
    setMessages((prev) => [...prev, { role: "user", content: msg }])
    setSending(true)
    try {
      let tickers = extractTickers(msg)
      if (tickers.length === 0) {
        const portfolio = await api.getHoldings()
        tickers = portfolio.holdings.map((h) => h.ticker).slice(0, 5)
      }
      const res = await api.chat({ message: msg, tickers })
      const decisions = res.decisions
      let summary = ""
      if (decisions && Object.keys(decisions).length > 0) {
        summary = Object.entries(decisions).map(([t, d]) => {
          const a = (d as any).action || (d as any).signal || "hold"
          const c = (d as any).confidence || 0
          const r = (d as any).reasoning || ""
          return `**${t}**: ${a.toUpperCase()} (${c}% confidence)${r ? `\n> ${r}` : ""}`
        }).join("\n\n")
      } else {
        summary = "I've analyzed the information. Based on your portfolio and financial profile, I recommend reviewing the specific assets you're interested in. Feel free to ask about any particular stock or investment strategy."
      }
      setMessages((prev) => [...prev, { role: "assistant", content: summary, decisions }])
    } catch (err: any) {
      toast.error(err.message || "Failed to get response")
      setMessages((prev) => [...prev, { role: "assistant", content: "I apologize, but I encountered an error processing your request. Please try again or rephrase your question." }])
    } finally { setSending(false) }
  }

  const badgeVariant = (a: string) => a === "buy" || a === "strong_buy" ? "success" as const : a === "sell" || a === "strong_sell" ? "destructive" as const : "warning" as const

  return (
    <div className="flex flex-col h-[calc(100vh-4rem)]">
      <div className="mb-4"><h1 className="text-2xl font-bold tracking-tight">AI Advisor</h1><p className="text-muted-foreground mt-1">Your personal investment assistant</p></div>
      <Card className="flex-1 flex flex-col border-none shadow-card bg-card overflow-hidden">
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.map((msg, i) => (
            <div key={i} className={`flex gap-4 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
              <Avatar className={msg.role === "assistant" ? "bg-primary/10" : "bg-muted"}>
                <AvatarFallback>{msg.role === "assistant" ? <Bot size={18} className="text-primary" /> : <User size={18} className="text-muted-foreground" />}</AvatarFallback>
              </Avatar>
              <div className={`max-w-[75%] ${msg.role === "user" ? "items-end" : ""}`}>
                <div className={`rounded-2xl px-5 py-3 text-sm leading-relaxed ${msg.role === "user" ? "bg-primary text-primary-foreground" : "bg-muted/50 border"}`}>
                  <div className="whitespace-pre-wrap">{msg.content}</div>
                  {msg.decisions && Object.keys(msg.decisions).length > 0 && (
                    <div className="mt-4 space-y-2 border-t pt-3">
                      <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Recommendations</p>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                        {Object.entries(msg.decisions).map(([ticker, d]) => {
                          const action = (d as any).action || (d as any).signal || "hold"
                          const conf = (d as any).confidence || 0
                          return (
                            <div key={ticker} className="rounded-lg border p-2.5 bg-background/50">
                              <div className="flex items-center justify-between mb-1"><span className="font-bold text-sm">{ticker}</span><Badge variant={badgeVariant(action)}>{action.toUpperCase()}</Badge></div>
                              <p className="text-xs text-muted-foreground">{conf.toFixed(0)}% confidence</p>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
          {sending && (
            <div className="flex gap-4">
              <Avatar className="bg-primary/10"><AvatarFallback><Bot size={18} className="text-primary" /></AvatarFallback></Avatar>
              <div className="rounded-2xl px-5 py-3 bg-muted/50 border"><Loader2 size={18} className="animate-spin text-muted-foreground" /></div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {messages.length === 1 && (
          <div className="px-6 pb-4">
            <p className="text-xs text-muted-foreground mb-3 text-center">Suggested prompts</p>
            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTED.map((p) => (
                <button key={p} onClick={() => handleSend(p)} className="inline-flex items-center gap-1.5 rounded-full border bg-background px-4 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:border-primary/50 transition-colors">
                  <Sparkles size={12} className="text-primary" />{p}
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="border-t p-4">
          <form onSubmit={(e) => { e.preventDefault(); handleSend() }} className="flex gap-3">
            <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Ask your AI advisor anything..." disabled={sending}
              className="flex-1 h-11 rounded-xl border bg-background px-4 text-sm outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/50 transition-all placeholder:text-muted-foreground" />
            <Button type="submit" size="icon" disabled={sending || !input.trim()} className="h-11 w-11 rounded-xl"><Send size={18} /></Button>
          </form>
        </div>
      </Card>
    </div>
  )
}
