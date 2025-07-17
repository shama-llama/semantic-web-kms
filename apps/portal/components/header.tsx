"use client"

import { useOrganization } from "@/components/organization-provider"
import { ThemeToggle } from "@/components/theme-toggle"
import { Building2, Database } from "lucide-react"

export function Header() {
  const { organization } = useOrganization()

  return (
    <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-16 items-center justify-between px-6">
        <div className="flex items-center space-x-4">
          {organization && (
            <>
              <div className="flex items-center space-x-2">
                <Building2 className="h-5 w-5 text-muted-foreground" />
                <span className="font-medium">{organization.name}</span>
              </div>
              <div className="flex items-center space-x-2 text-sm text-muted-foreground">
                <Database className="h-4 w-4" />
                <span>{organization.repositories.length} repositories</span>
                <span>•</span>
                <span>{organization.totalFiles} files</span>
              </div>
            </>
          )}
        </div>
        <div className="flex items-center space-x-4">
          <ThemeToggle />
        </div>
      </div>
    </header>
  )
}
