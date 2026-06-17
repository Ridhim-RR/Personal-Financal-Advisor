"use client"

import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import * as api from "@/lib/api"
import type { Watchlist } from "@/types"
import { toast } from "sonner"
import { Plus, Trash2, Eye, X } from "lucide-react"

export default function WatchlistPage() {
  const [watchlists, setWatchlists] = useState<Watchlist[]>([])
  const [loading, setLoading] = useState(true)
  const [createOpen, setCreateOpen] = useState(false)
  const [newName, setNewName] = useState("")
  const [addTarget, setAddTarget] = useState<string | null>(null)
  const [newTicker, setNewTicker] = useState("")

  const load = () => { api.getWatchlists().then(r => setWatchlists(r.watchlists)).catch(() => toast.error("Failed to load")).finally(() => setLoading(false)) }
  useEffect(() => { load() }, [])

  const handleCreate = async () => {
    if (!newName.trim()) return
    try { await api.createWatchlist(newName.trim()); toast.success("Created"); setCreateOpen(false); setNewName(""); load() }
    catch (err: any) { toast.error(err.message) }
  }

  const handleDelete = async (id: string) => {
    try { await api.deleteWatchlist(id); toast.success("Deleted"); load() }
    catch (err: any) { toast.error(err.message) }
  }

  const handleAddTicker = async (id: string) => {
    if (!newTicker.trim()) return
    try { await api.addTickerToWatchlist(id, newTicker.trim().toUpperCase()); toast.success("Ticker added"); setAddTarget(null); setNewTicker(""); load() }
    catch (err: any) { toast.error(err.message) }
  }

  const handleRemoveTicker = async (wid: string, t: string) => {
    try { await api.removeTickerFromWatchlist(wid, t); load() }
    catch (err: any) { toast.error(err.message) }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold tracking-tight">Watchlist</h1><p className="text-muted-foreground mt-1">Track stocks you're interested in</p></div>
        <Dialog open={createOpen} onOpenChange={setCreateOpen}>
          <DialogTrigger asChild><Button><Plus size={16} className="mr-1.5" /> New Watchlist</Button></DialogTrigger>
          <DialogContent><DialogHeader><DialogTitle>Create Watchlist</DialogTitle></DialogHeader>
            <div className="space-y-4 pt-2"><Input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Watchlist name" /><Button onClick={handleCreate} className="w-full">Create</Button></div>
          </DialogContent>
        </Dialog>
      </div>

      {loading ? <p className="text-sm text-muted-foreground">Loading...</p>
      : watchlists.length === 0 ? <Card className="shadow-soft"><CardContent className="py-12 text-center text-sm text-muted-foreground">No watchlists yet.</CardContent></Card>
      : <div className="grid grid-cols-1 md:grid-cols-2 gap-4">{watchlists.map((wl) => (
        <Card key={wl.id} className="shadow-soft hover:shadow-md transition-shadow">
          <CardHeader className="flex flex-row items-center justify-between pb-3">
            <CardTitle className="text-sm font-semibold flex items-center gap-2"><Eye size={16} className="text-primary" />{wl.name}</CardTitle>
            <Button variant="ghost" size="icon" className="h-7 w-7 text-muted-foreground hover:text-destructive" onClick={() => handleDelete(wl.id)}><Trash2 size={14} /></Button>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-1.5 mb-4">
              {wl.tickers.map((t) => (
                <span key={t} className="inline-flex items-center gap-1 rounded-lg bg-secondary px-2.5 py-1 text-sm font-medium">{t}
                  <button onClick={() => handleRemoveTicker(wl.id, t)} className="hover:text-destructive"><X size={13} /></button>
                </span>
              ))}
              {wl.tickers.length === 0 && <p className="text-xs text-muted-foreground">No tickers yet</p>}
            </div>
            <Dialog open={addTarget === wl.id} onOpenChange={(o) => { setAddTarget(o ? wl.id : null); setNewTicker("") }}>
              <DialogTrigger asChild><Button variant="outline" size="sm" className="w-full"><Plus size={14} className="mr-1" /> Add Ticker</Button></DialogTrigger>
              <DialogContent><DialogHeader><DialogTitle>Add to {wl.name}</DialogTitle></DialogHeader>
                <div className="space-y-4 pt-2"><Input value={newTicker} onChange={(e) => setNewTicker(e.target.value.toUpperCase())} placeholder="AAPL" /><Button onClick={() => handleAddTicker(wl.id)} className="w-full">Add</Button></div>
              </DialogContent>
            </Dialog>
          </CardContent>
        </Card>
      ))}</div>}
    </div>
  )
}
