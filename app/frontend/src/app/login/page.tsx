"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { useAuth } from "@/hooks/use-auth"
import { Toaster, toast } from "sonner"

export default function LoginPage() {
  const { login, register } = useAuth()
  const [isLogin, setIsLogin] = useState(true)
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      if (isLogin) { await login(email, password); toast.success("Welcome back!") }
      else { await register(email, password); toast.success("Account created!") }
    } catch (err: any) {
      toast.error(err.message || "Something went wrong")
    } finally { setSubmitting(false) }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-gradient-to-br from-background via-background to-primary/5 p-4">
      <Toaster richColors position="top-right" />
      <div className="mb-8 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary shadow-lg shadow-primary/20">
          <div className="h-5 w-5 rounded-full bg-primary-foreground/90" />
        </div>
        <div>
          <h1 className="text-xl font-bold">AI Advisor</h1>
          <p className="text-xs text-muted-foreground">Personal Investment Assistant</p>
        </div>
      </div>
      <Card className="w-full max-w-sm border-none shadow-xl">
        <CardHeader className="text-center">
          <CardTitle>{isLogin ? "Welcome back" : "Get started"}</CardTitle>
          <CardDescription>{isLogin ? "Sign in to your account" : "Create your financial advisor account"}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <label className="text-sm font-medium">Email</label>
              <Input type="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} required />
            </div>
            <div className="space-y-2">
              <label className="text-sm font-medium">Password</label>
              <Input type="password" placeholder="••••••••" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={6} />
            </div>
            <Button type="submit" className="w-full" disabled={submitting}>{submitting ? "Please wait..." : isLogin ? "Sign In" : "Create Account"}</Button>
          </form>
          <div className="mt-4 text-center text-sm text-muted-foreground">
            {isLogin ? <>Don't have an account? <button onClick={() => setIsLogin(false)} className="text-primary hover:underline font-medium">Sign up</button></>
              : <>Already have an account? <button onClick={() => setIsLogin(true)} className="text-primary hover:underline font-medium">Sign in</button></>}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
