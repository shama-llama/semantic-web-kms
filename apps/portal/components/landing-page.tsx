"use client"
import { useOrganization } from "@/components/organization-provider"
import { Brain, Github, Search, BarChart3, Network, Database } from "lucide-react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { DataInputPanel } from "@/components/data-input-panel"
import { ThemeToggle } from "@/components/theme-toggle"

export function LandingPage() {
  useOrganization()

  const features = [
    {
      icon: Search,
      title: "Semantic Search",
      description: "Natural language search across your entire codebase with AI-powered understanding",
    },
    {
      icon: Network,
      title: "Knowledge Graph",
      description: "Interactive 3D visualization of code relationships and architectural patterns",
    },
    {
      icon: BarChart3,
      title: "Analytics Dashboard",
      description: "Comprehensive metrics on code quality, complexity, and technical debt",
    },
    {
      icon: Database,
      title: "Repository Management",
      description: "Centralized management of multiple repositories with processing status",
    },
  ]

  return (
    <div className="min-h-screen bg-gradient-to-br from-background via-background to-muted/20">
      {/* Header */}
      <header className="border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary rounded-lg">
              <Brain className="h-6 w-6 text-primary-foreground" />
            </div>
            <div>
              <h1 className="text-xl font-bold">SemanticWeb</h1>
              <p className="text-xs text-muted-foreground">Knowledge Management System</p>
            </div>
          </div>
          <ThemeToggle />
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 space-y-12">
        {/* Hero Section */}
        <section className="text-center space-y-6 py-12">
          <div className="space-y-4">
            <Badge variant="outline" className="px-3 py-1">
              <Github className="h-3 w-3 mr-1" />
              Web Development Organizations
            </Badge>
            <h2 className="text-4xl md:text-6xl font-bold tracking-tight">
              Transform Your
              <span className="text-primary block">Code Knowledge</span>
            </h2>
            <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
              Analyze GitHub organizations and local projects to create semantic knowledge graphs, enabling intelligent
              search and deep architectural insights.
            </p>
          </div>
        </section>

        {/* Features Grid */}
        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {features.map((feature, index) => (
            <Card key={index} className="text-center hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="mx-auto p-3 bg-primary/10 rounded-full w-fit">
                  <feature.icon className="h-6 w-6 text-primary" />
                </div>
                <CardTitle className="text-lg">{feature.title}</CardTitle>
              </CardHeader>
              <CardContent>
                <CardDescription>{feature.description}</CardDescription>
              </CardContent>
            </Card>
          ))}
        </section>

        {/* Data Input Section */}
        <section className="max-w-4xl mx-auto">
          <DataInputPanel />
        </section>

        {/* Benefits Section */}
        <section className="py-12">
          <div className="text-center space-y-4 mb-12">
            <h3 className="text-3xl font-bold">Why Choose SemanticWeb?</h3>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              Unlock the hidden knowledge in your codebase with AI-powered analysis
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center space-y-4">
              <div className="p-4 bg-green-100 dark:bg-green-900/20 rounded-full w-fit mx-auto">
                <Search className="h-8 w-8 text-green-600 dark:text-green-400" />
              </div>
              <h4 className="text-xl font-semibold">Intelligent Discovery</h4>
              <p className="text-muted-foreground">
                Find code patterns, architectural decisions, and implementation details using natural language queries.
              </p>
            </div>

            <div className="text-center space-y-4">
              <div className="p-4 bg-blue-100 dark:bg-blue-900/20 rounded-full w-fit mx-auto">
                <Network className="h-8 w-8 text-blue-600 dark:text-blue-400" />
              </div>
              <h4 className="text-xl font-semibold">Visual Understanding</h4>
              <p className="text-muted-foreground">
                Explore your codebase through interactive 3D knowledge graphs that reveal hidden connections and
                dependencies.
              </p>
            </div>

            <div className="text-center space-y-4">
              <div className="p-4 bg-purple-100 dark:bg-purple-900/20 rounded-full w-fit mx-auto">
                <BarChart3 className="h-8 w-8 text-purple-600 dark:text-purple-400" />
              </div>
              <h4 className="text-xl font-semibold">Actionable Insights</h4>
              <p className="text-muted-foreground">
                Get comprehensive analytics on code quality, technical debt, and architectural patterns across your
                entire organization.
              </p>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="border-t bg-muted/50 py-8">
        <div className="container mx-auto px-4 text-center text-muted-foreground">
          <p>&copy; 2024 SemanticWeb. Transforming code into knowledge.</p>
        </div>
      </footer>
    </div>
  )
}
