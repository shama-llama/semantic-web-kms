"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import { GitBranch, Plus, RefreshCw, Trash2, ExternalLink, Clock } from "lucide-react"

export function RepositoryManager() {
  const [newRepoUrl, setNewRepoUrl] = useState("")

  const repositories = [
    {
      name: "react-admin",
      url: "https://github.com/user/react-admin",
      status: "completed",
      progress: 100,
      entities: 234,
      lastProcessed: "2 hours ago",
      quality: 92,
    },
    {
      name: "vue-dashboard",
      url: "https://github.com/user/vue-dashboard",
      status: "processing",
      progress: 68,
      entities: 156,
      lastProcessed: "Processing...",
      quality: 88,
    },
    {
      name: "node-api",
      url: "https://github.com/user/node-api",
      status: "completed",
      progress: 100,
      entities: 189,
      lastProcessed: "1 day ago",
      quality: 85,
    },
    {
      name: "angular-app",
      url: "https://github.com/user/angular-app",
      status: "failed",
      progress: 0,
      entities: 0,
      lastProcessed: "Failed",
      quality: 0,
    },
  ]

  const getStatusColor = (status: string) => {
    switch (status) {
      case "completed":
        return "bg-green-500"
      case "processing":
        return "bg-blue-500"
      case "failed":
        return "bg-red-500"
      default:
        return "bg-gray-500"
    }
  }

  const getStatusVariant = (status: string) => {
    switch (status) {
      case "completed":
        return "default"
      case "processing":
        return "secondary"
      case "failed":
        return "destructive"
      default:
        return "outline"
    }
  }

  return (
    <div className="p-6 space-y-6 overflow-auto h-full">
      <div>
        <h2 className="text-3xl font-bold text-foreground">Repository Manager</h2>
        <p className="text-muted-foreground mt-2">
          Manage and monitor your GitHub repositories for knowledge extraction
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Add New Repository</CardTitle>
          <CardDescription>Enter a GitHub repository URL to start knowledge extraction</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <Input
              placeholder="https://github.com/username/repository"
              value={newRepoUrl}
              onChange={(e) => setNewRepoUrl(e.target.value)}
              className="flex-1"
            />
            <Button className="gap-2">
              <Plus className="h-4 w-4" />
              Add Repository
            </Button>
          </div>
        </CardContent>
      </Card>

      <Tabs defaultValue="repositories" className="space-y-4">
        <TabsList>
          <TabsTrigger value="repositories">Repositories</TabsTrigger>
          <TabsTrigger value="processing">Processing Queue</TabsTrigger>
          <TabsTrigger value="settings">Settings</TabsTrigger>
        </TabsList>

        <TabsContent value="repositories" className="space-y-4">
          <div className="grid gap-4">
            {repositories.map((repo) => (
              <Card key={repo.name}>
                <CardHeader>
                  <div className="flex justify-between items-start">
                    <div className="space-y-1">
                      <CardTitle className="flex items-center gap-2">
                        <GitBranch className="h-4 w-4" />
                        {repo.name}
                      </CardTitle>
                      <CardDescription className="flex items-center gap-2">
                        {repo.url}
                        <ExternalLink className="h-3 w-3" />
                      </CardDescription>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={getStatusVariant(repo.status)}>{repo.status}</Badge>
                      <div className="flex gap-1">
                        <Button variant="outline" size="sm">
                          <RefreshCw className="h-4 w-4" />
                        </Button>
                        <Button variant="outline" size="sm">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    {repo.status === "processing" && (
                      <div>
                        <div className="flex justify-between text-sm mb-2">
                          <span>Processing Progress</span>
                          <span>{repo.progress}%</span>
                        </div>
                        <Progress value={repo.progress} className="h-2" />
                      </div>
                    )}

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                      <div>
                        <p className="text-muted-foreground">Entities</p>
                        <p className="font-medium">{repo.entities}</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Quality Score</p>
                        <p className="font-medium">{repo.quality}%</p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Last Processed</p>
                        <p className="font-medium flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {repo.lastProcessed}
                        </p>
                      </div>
                      <div>
                        <p className="text-muted-foreground">Status</p>
                        <div className="flex items-center gap-2">
                          <div className={`w-2 h-2 rounded-full ${getStatusColor(repo.status)}`} />
                          <p className="font-medium capitalize">{repo.status}</p>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="processing" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Processing Queue</CardTitle>
              <CardDescription>Current processing status and queue information</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="flex justify-between items-center p-4 bg-muted/50 rounded-lg">
                  <div>
                    <h4 className="font-medium">vue-dashboard</h4>
                    <p className="text-sm text-muted-foreground">Semantic annotation in progress</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium">68% complete</p>
                    <p className="text-xs text-muted-foreground">Est. 5 minutes remaining</p>
                  </div>
                </div>

                <div className="flex justify-between items-center p-4 bg-muted/20 rounded-lg">
                  <div>
                    <h4 className="font-medium">next-portfolio</h4>
                    <p className="text-sm text-muted-foreground">Queued for processing</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium">Waiting</p>
                    <p className="text-xs text-muted-foreground">Position #1 in queue</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="settings" className="space-y-4">
          <div className="grid gap-6">
            <Card>
              <CardHeader>
                <CardTitle>Processing Settings</CardTitle>
                <CardDescription>Configure how repositories are processed and analyzed</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Auto-processing</label>
                  <p className="text-xs text-muted-foreground">
                    Automatically start processing when a new repository is added
                  </p>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Quality Threshold</label>
                  <p className="text-xs text-muted-foreground">
                    Minimum quality score required for semantic annotations
                  </p>
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Batch Size</label>
                  <p className="text-xs text-muted-foreground">Number of files to process simultaneously</p>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>GitHub Integration</CardTitle>
                <CardDescription>Configure GitHub API access and webhook settings</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">API Token</label>
                  <Input type="password" placeholder="ghp_xxxxxxxxxxxx" />
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Webhook URL</label>
                  <Input placeholder="https://your-domain.com/webhook" />
                </div>

                <Button>Save Settings</Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
