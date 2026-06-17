"use client"

import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import * as api from "@/lib/api"
import { formatCurrency } from "@/lib/utils"
import type { Holding } from "@/types"
import { toast } from "sonner"
import { Plus, Trash2 } from "lucide-react"
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts"

const COLORS = ["hsl(var(--chart-1))", "hsl(var(--chart-2))", "hsl(var(--chart-3))", "hsl(var(--chart-4))", "hsl(var(--chart-5))"]

export default function PortfolioPage() {
  const [holdings, setHoldings] = useState<Holding[]>([])
  const [loading, setLoading] = useState(true)
  const [dialogOpen, setDialogOpen] = useState(false)
  const [ticker, setTicker] = useState("")
  const [shares, setShares] = useState("")
  const [price, setPrice] = useState("")
  const [saving, setSaving] = useState(false)

  const load = () => { api.getHoldings().then(r => setHoldings(r.holdings)).catch(() => toast.error("Failed to load")).finally(() => setLoading(false)) }
  useEffect(() => { load() }, [])

  const handleAdd = async () => {
    if (!ticker.trim() || !shares || !price) return
    setSaving(true)
    try {
      await api.addHolding(ticker.toUpperCase(), parseFloat(shares), parseFloat(price))
      toast.success("Holding added"); setDialogOpen(false); setTicker(""); setShares(""); setPrice(""); load()
    } catch (err: any) { toast.error(err.message) } finally { setSaving(false) }
  }

  const handleDelete = async (t: string) => {
    try { await api.deleteHolding(t); toast.success("Removed"); load() } catch (err: any) { toast.error(err.message) }
  }

  const totalValue = holdings.reduce((s, h) => s + h.shares * h.avg_cost, 0)
  const chartData = holdings.map((h) => ({ name: h.ticker, value: h.shares * h.avg_cost }))

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold tracking-tight">Portfolio</h1><p className="text-muted-foreground mt-1">Manage your investments</p></div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild><Button><Plus size={16} className="mr-1.5" /> Add Holding</Button></DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Add Holding</DialogTitle></DialogHeader>
            <div className="space-y-4 pt-2">
              <div className="space-y-1.5"><label className="text-sm font-medium">Ticker</label><Input value={ticker} onChange={(e) => setTicker(e.target.value.toUpperCase())} placeholder="AAPL" /></div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5"><label className="text-sm font-medium">Shares</label><Input value={shares} onChange={(e) => setShares(e.target.value)} type="number" step="any" placeholder="10" /></div>
                <div className="space-y-1.5"><label className="text-sm font-medium">Avg. Price ($)</label><Input value={price} onChange={(e) => setPrice(e.target.value)} type="number" step="any" placeholder="150.00" /></div>
              </div>
              <Button onClick={handleAdd} className="w-full" disabled={saving}>{saving ? "Adding..." : "Add to Portfolio"}</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-2 shadow-soft">
          <CardHeader><CardTitle className="text-sm font-semibold">Holdings</CardTitle></CardHeader>
          <CardContent className="p-0">
            {loading ? <div className="p-6 text-sm text-muted-foreground">Loading...</div>
            : holdings.length === 0 ? <div className="p-6 text-sm text-muted-foreground text-center">No holdings yet. Add your first investment.</div>
            : <div className="divide-y">{holdings.map((h) => (
              <div key={h.ticker} className="flex items-center justify-between px-6 py-4 hover:bg-muted/30 transition-colors">
                <div className="flex items-center gap-4">
                  <div className="h-9 w-9 rounded-lg bg-primary/10 flex items-center justify-center"><span className="text-sm font-bold text-primary">{h.ticker.slice(0, 2)}</span></div>
                  <div><p className="font-semibold">{h.ticker}</p><p className="text-xs text-muted-foreground">{h.shares} shares @ ${h.avg_cost.toFixed(2)}</p></div>
                </div>
                <div className="flex items-center gap-6">
                  <div className="text-right"><p className="font-semibold">{formatCurrency(h.shares * h.avg_cost)}</p><p className="text-xs text-muted-foreground">{((h.shares * h.avg_cost / totalValue) * 100).toFixed(1)}%</p></div>
                  <Button variant="ghost" size="icon" className="h-8 w-8 text-muted-foreground hover:text-destructive" onClick={() => handleDelete(h.ticker)}><Trash2 size={14} /></Button>
                </div>
              </div>
            ))}</div>}
          </CardContent>
        </Card>

        <Card className="shadow-soft">
          <CardHeader><CardTitle className="text-sm font-semibold">Allocation</CardTitle></CardHeader>
          <CardContent>
            {chartData.length === 0 ? <p className="text-sm text-muted-foreground text-center py-8">No data</p>
            : <><div className="h-48"><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={chartData} cx="50%" cy="50%" innerRadius={50} outerRadius={75} paddingAngle={3} dataKey="value">{chartData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}</Pie><Tooltip formatter={(v: number) => formatCurrency(v)} /></PieChart></ResponsiveContainer></div>
              <div className="mt-4 space-y-2">{chartData.map((d, i) => (
                <div key={d.name} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2"><div className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: COLORS[i] }} /><span>{d.name}</span></div>
                  <span className="font-medium">{formatCurrency(d.value)}</span>
                </div>
              ))}</div></>}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
