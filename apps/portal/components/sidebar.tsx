"use client"

import { useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { BarChart3, ChevronLeft, Database, GitBranch, Home, Network, Search, Upload } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip"

const navigation = [
  { name: "Data Input", href: "/", icon: Upload },
  { name: "Dashboard", href: "/dashboard", icon: Home },
  { name: "Search", href: "/search", icon: Search },
  { name: "Knowledge Graph", href: "/knowledge-graph", icon: Network },
  { name: "Analytics", href: "/analytics", icon: BarChart3 },
  { name: "Repositories", href: "/repositories", icon: GitBranch },
]

export function Sidebar() {
  const [collapsed, setCollapsed] = useState(false)
  const pathname = usePathname()

  return (
    <TooltipProvider>
      <div
        className={cn("flex flex-col border-r bg-background transition-all duration-300", collapsed ? "w-16" : "w-64")}
      >
        <div className="flex h-16 items-center justify-between px-4 border-b">
          {!collapsed && (
            <Link href="/" className="flex items-center space-x-2">
              <Database className="h-6 w-6 text-primary" />
              <span className="font-bold text-lg">SemanticWeb</span>
            </Link>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setCollapsed(!collapsed)}
            className={cn("h-8 w-8", collapsed && "mx-auto")}
          >
            <ChevronLeft className={cn("h-4 w-4 transition-transform", collapsed && "rotate-180")} />
          </Button>
        </div>

        <nav className="flex-1 space-y-1 p-2">
          {navigation.map((item) => {
            const isActive = pathname === item.href
            const content = (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  "flex items-center rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  "hover:bg-accent hover:text-accent-foreground",
                  isActive ? "bg-accent text-accent-foreground" : "text-muted-foreground",
                  collapsed && "justify-center px-2",
                )}
              >
                <item.icon className={cn("h-4 w-4", !collapsed && "mr-3")} />
                {!collapsed && <span>{item.name}</span>}
              </Link>
            )

            if (collapsed) {
              return (
                <Tooltip key={item.name}>
                  <TooltipTrigger asChild>{content}</TooltipTrigger>
                  <TooltipContent side="right">
                    <p>{item.name}</p>
                  </TooltipContent>
                </Tooltip>
              )
            }

            return content
          })}
        </nav>
      </div>
    </TooltipProvider>
  )
}
