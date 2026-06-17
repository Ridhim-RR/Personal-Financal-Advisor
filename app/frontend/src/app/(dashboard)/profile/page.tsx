"use client"

import { useEffect, useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { useAuth } from "@/hooks/use-auth"
import * as api from "@/lib/api"
import { toast } from "sonner"
import { Save, X, User } from "lucide-react"

const SECTORS = ["Technology", "Healthcare", "Finance", "Energy", "Consumer Goods", "Industrial", "Utilities", "Real Estate", "Materials", "Communication"]

export default function ProfilePage() {
  const { user, fetchProfile } = useAuth()
  const [risk, setRisk] = useState("moderate"); const [goal, setGoal] = useState("growth"); const [horizon, setHorizon] = useState("medium")
  const [preferred, setPreferred] = useState<string[]>([]); const [excluded, setExcluded] = useState<string[]>([]); const [capital, setCapital] = useState("100000")
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (user?.profile) {
      const p = user.profile
      setRisk(p.risk_appetite || "moderate"); setGoal(p.investment_goal || "growth"); setHorizon(p.investment_horizon || "medium")
      setPreferred(p.preferred_sectors || []); setExcluded(p.excluded_sectors || []); setCapital(String(p.initial_capital || 100000))
    }
  }, [user])

  const toggle = (s: string, list: string[], set: (v: string[]) => void) => set(list.includes(s) ? list.filter(x => x !== s) : [...list, s])

  const handleSave = async () => {
    setSaving(true)
    try {
      await api.updateProfile({ risk_appetite: risk as any, investment_goal: goal, investment_horizon: horizon as any, preferred_sectors: preferred, excluded_sectors: excluded, initial_capital: parseFloat(capital) || 100000 })
      toast.success("Profile updated"); await fetchProfile()
    } catch (err: any) { toast.error(err.message) } finally { setSaving(false) }
  }

  return (
    <div className="max-w-2xl space-y-6">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold tracking-tight">Profile</h1><p className="text-muted-foreground mt-1">Your financial profile and preferences</p></div>
        <Button onClick={handleSave} disabled={saving}><Save size={16} className="mr-1.5" />{saving ? "Saving..." : "Save Profile"}</Button>
      </div>

      <Card className="shadow-soft">
        <CardHeader><CardTitle className="text-sm font-semibold flex items-center gap-2"><User size={16} className="text-primary" />Account</CardTitle></CardHeader>
        <CardContent>
          <div className="flex items-center gap-3">
            <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center"><span className="text-lg font-bold text-primary">{user?.email?.charAt(0).toUpperCase()}</span></div>
            <div><p className="font-medium">{user?.email}</p><p className="text-xs text-muted-foreground">ID: {user?.user_id?.slice(0, 8)}...</p></div>
          </div>
        </CardContent>
      </Card>

      <Card className="shadow-soft">
        <CardHeader><CardTitle className="text-sm font-semibold">Investment Profile</CardTitle></CardHeader>
        <CardContent className="space-y-5">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="space-y-1.5"><label className="text-sm font-medium">Risk Appetite</label><Select value={risk} onValueChange={setRisk}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="low">Conservative</SelectItem><SelectItem value="moderate">Moderate</SelectItem><SelectItem value="high">Aggressive</SelectItem></SelectContent></Select></div>
            <div className="space-y-1.5"><label className="text-sm font-medium">Goal</label><Select value={goal} onValueChange={setGoal}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="growth">Growth</SelectItem><SelectItem value="income">Income</SelectItem><SelectItem value="wealth_creation">Wealth Creation</SelectItem><SelectItem value="retirement">Retirement</SelectItem></SelectContent></Select></div>
            <div className="space-y-1.5"><label className="text-sm font-medium">Horizon</label><Select value={horizon} onValueChange={setHorizon}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="short">Short Term</SelectItem><SelectItem value="medium">Medium Term</SelectItem><SelectItem value="long">Long Term</SelectItem></SelectContent></Select></div>
          </div>
          <div className="space-y-1.5"><label className="text-sm font-medium">Initial Capital ($)</label><Input value={capital} onChange={(e) => setCapital(e.target.value)} type="number" className="max-w-xs" /></div>
        </CardContent>
      </Card>

      {[{ title: "Preferred Sectors", list: preferred, setter: setPreferred, variant: "default" as const },
        { title: "Excluded Sectors", list: excluded, setter: setExcluded, variant: "destructive" as const }].map(({ title, list, setter, variant }) => (
        <Card key={title} className="shadow-soft">
          <CardHeader><CardTitle className="text-sm font-semibold">{title}</CardTitle></CardHeader>
          <CardContent><div className="flex flex-wrap gap-1.5">{SECTORS.map((s) => (
            <Badge key={s} variant={list.includes(s) ? variant : "outline"} className="cursor-pointer" onClick={() => toggle(s, list, setter)}>
              {s}{list.includes(s) && <X size={12} className="ml-1" />}
            </Badge>
          ))}</div></CardContent>
        </Card>
      ))}
    </div>
  )
}
