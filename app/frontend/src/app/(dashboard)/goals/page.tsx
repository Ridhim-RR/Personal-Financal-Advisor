"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { formatCurrency } from "@/lib/utils"
import { toast } from "sonner"
import { Plus, PiggyBank, Home, Umbrella, GraduationCap, Target } from "lucide-react"

interface Goal { id: string; name: string; target: number; current: number; date: string; icon: string }
const ICONS: Record<string, any> = { retirement: PiggyBank, house: Home, emergency: Umbrella, education: GraduationCap, other: Target }
const DEFAULT_GOALS: Goal[] = [
  { id: "1", name: "Retirement Fund", target: 500000, current: 310000, date: "2045-12-31", icon: "retirement" },
  { id: "2", name: "House Down Payment", target: 100000, current: 31000, date: "2028-06-30", icon: "house" },
  { id: "3", name: "Emergency Fund", target: 50000, current: 45000, date: "2025-12-31", icon: "emergency" },
]

export default function GoalsPage() {
  const [goals, setGoals] = useState<Goal[]>(DEFAULT_GOALS)
  const [open, setOpen] = useState(false)
  const [name, setName] = useState(""); const [target, setTarget] = useState(""); const [current, setCurrent] = useState(""); const [date, setDate] = useState(""); const [category, setCategory] = useState("other")

  const handleAdd = () => {
    if (!name.trim() || !target) return
    setGoals((prev) => [...prev, { id: Math.random().toString(36).slice(2), name: name.trim(), target: parseFloat(target), current: parseFloat(current) || 0, date: date || "2030-12-31", icon: category }])
    setOpen(false); setName(""); setTarget(""); setCurrent(""); setDate(""); toast.success("Goal created")
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div><h1 className="text-2xl font-bold tracking-tight">Financial Goals</h1><p className="text-muted-foreground mt-1">Track your financial targets</p></div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger asChild><Button><Plus size={16} className="mr-1.5" /> New Goal</Button></DialogTrigger>
          <DialogContent>
            <DialogHeader><DialogTitle>Create Financial Goal</DialogTitle></DialogHeader>
            <div className="space-y-4 pt-2">
              <div className="space-y-1.5"><label className="text-sm font-medium">Goal Name</label><Input value={name} onChange={(e) => setName(e.target.value)} placeholder="e.g., Retirement" /></div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5"><label className="text-sm font-medium">Target ($)</label><Input value={target} onChange={(e) => setTarget(e.target.value)} type="number" placeholder="500000" /></div>
                <div className="space-y-1.5"><label className="text-sm font-medium">Saved ($)</label><Input value={current} onChange={(e) => setCurrent(e.target.value)} type="number" placeholder="100000" /></div>
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5"><label className="text-sm font-medium">Target Date</label><Input value={date} onChange={(e) => setDate(e.target.value)} type="date" /></div>
                <div className="space-y-1.5"><label className="text-sm font-medium">Category</label><Select value={category} onValueChange={setCategory}><SelectTrigger><SelectValue /></SelectTrigger><SelectContent><SelectItem value="retirement">Retirement</SelectItem><SelectItem value="house">House</SelectItem><SelectItem value="emergency">Emergency Fund</SelectItem><SelectItem value="education">Education</SelectItem><SelectItem value="other">Other</SelectItem></SelectContent></Select></div>
              </div>
              <Button onClick={handleAdd} className="w-full">Create Goal</Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {goals.map((goal) => {
          const Icon = ICONS[goal.icon] || Target
          const pct = Math.min((goal.current / goal.target) * 100, 100)
          const remaining = goal.target - goal.current
          const yearsLeft = Math.max(1, (new Date(goal.date).getTime() - Date.now()) / (365 * 24 * 60 * 60 * 1000))
          return (
            <Card key={goal.id} className="shadow-soft hover:shadow-md transition-shadow">
              <CardContent className="p-5">
                <div className="flex items-center gap-3 mb-4">
                  <div className="h-10 w-10 rounded-xl bg-primary/10 flex items-center justify-center"><Icon size={20} className="text-primary" /></div>
                  <div><p className="font-semibold">{goal.name}</p><p className="text-xs text-muted-foreground">Target: {formatCurrency(goal.target)}</p></div>
                </div>
                <div className="mb-2"><div className="flex justify-between text-sm mb-1.5"><span className="text-muted-foreground">Progress</span><span className="font-medium">{pct.toFixed(0)}%</span></div><Progress value={pct} className="h-2.5" /></div>
                <div className="flex justify-between text-xs text-muted-foreground mt-3"><span>{formatCurrency(goal.current)} saved</span><span>{formatCurrency(remaining)} to go</span></div>
                <div className="mt-3 pt-3 border-t text-xs text-muted-foreground">Save {formatCurrency(remaining / (yearsLeft * 12))}/month to reach by {new Date(goal.date).toLocaleDateString("en-US", { year: "numeric", month: "short" })}</div>
              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}
