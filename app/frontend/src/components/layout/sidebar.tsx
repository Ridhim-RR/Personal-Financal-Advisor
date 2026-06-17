"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { LayoutDashboard, Wallet, Bot, BarChart3, Target, UserCircle, Eye, LogOut } from "lucide-react"
import { Button } from "@/components/ui/button"
import * as api from "@/lib/api"

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/portfolio", label: "Portfolio", icon: Wallet },
  { href: "/advisor", label: "AI Advisor", icon: Bot },
  { href: "/recommendations", label: "Recommendations", icon: BarChart3 },
  { href: "/goals", label: "Goals", icon: Target },
  { href: "/profile", label: "Profile", icon: UserCircle },
  { href: "/watchlist", label: "Watchlist", icon: Eye },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="flex h-screen w-56 flex-col border-r bg-background">
      <div className="flex items-center gap-3 px-5 py-5 border-b">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary shadow-sm">
          <div className="h-4 w-4 rounded-full bg-primary-foreground/90" />
        </div>
        <div>
          <span className="text-sm font-semibold">AI Advisor</span>
          <p className="text-[11px] text-muted-foreground">Personal Finance</p>
        </div>
      </div>

      <nav className="flex-1 px-3 py-3 space-y-0.5">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href))
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                active
                  ? "bg-primary/10 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground",
              )}
            >
              <Icon size={18} />
              {label}
            </Link>
          )
        })}
      </nav>

      <div className="px-3 py-3 border-t">
        <button
          onClick={async () => { await api.logout(); window.location.href = "/login" }}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground hover:bg-accent hover:text-destructive transition-colors"
        >
          <LogOut size={18} /> Sign Out
        </button>
      </div>
    </aside>
  )
}
