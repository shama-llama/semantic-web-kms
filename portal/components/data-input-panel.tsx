"use client"

import type React from "react"
import { useState, useRef, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Progress } from "@/components/ui/progress"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Github, FolderOpen, FileText, CheckCircle, AlertCircle, Loader2, X, RefreshCw } from "lucide-react"

// If you want to use context/toast from portal, import and adapt here
// import { useOrganization } from "@/components/organization-provider"
// import { useToast } from "@/hooks/use-toast"

interface ProcessingStage {
  status: string
  progress: number
  message?: string
}

interface JobStatus {
  job_id: string
  status: string
  overall_progress: number
  start_time?: string
  end_time?: string
  stages: Record<string, ProcessingStage>
}

export function DataInputPanel() {
  // State for GitHub org input
  const [githubOrg, setGithubOrg] = useState("")
  // State for uploaded files
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([])
  // State for upload progress
  const [uploadProgress, setUploadProgress] = useState(0)
  // State for error messages
  const [error, setError] = useState<string | null>(null)
  // State for processing
  const [isProcessing, setIsProcessing] = useState(false)
  // State for processing pipeline stages
  const [processingStages, setProcessingStages] = useState<Record<string, ProcessingStage>>({})
  // State for current job
  const [currentJobId, setCurrentJobId] = useState<string | null>(null)
  // State for current input directory
  const [currentInputDir, setCurrentInputDir] = useState<string | null>(null)
  // Ref for folder input
  const folderInputRef = useRef<HTMLInputElement>(null)

  // Simulate pipeline stages for demo
  const stages = [
    { key: "fileExtraction", label: "File Extraction", description: "Extracting files from organization source" },
    { key: "contentExtraction", label: "Content Analysis", description: "Analyzing web development file contents" },
    { key: "codeExtraction", label: "Code Parsing", description: "Parsing frontend and backend structures" },
    { key: "documentationExtraction", label: "Documentation", description: "Processing README and API docs" },
    { key: "gitExtraction", label: "Git Analysis", description: "Analyzing development history and patterns" },
    { key: "semanticAnnotation", label: "Semantic Processing", description: "Creating web development knowledge graph" },
  ]

  // Reset job state on mount to prevent polling on page load
  useEffect(() => {
    setCurrentJobId(null)
    setIsProcessing(false)
  }, [])

  // Polling effect for progress updates
  useEffect(() => {
    if (!currentJobId || !isProcessing) return

    let pollCount = 0
    const maxPolls = 1200 // 30 minutes at 1.5 second intervals

    const pollProgress = async () => {
      try {
        pollCount++
        
        // Timeout after 30 minutes to prevent infinite polling
        if (pollCount > maxPolls) {
          console.warn("Progress polling timeout reached")
          setIsProcessing(false)
          setCurrentJobId(null)
          setError("Pipeline timeout. The job may still be running in the background.")
          return
        }

        const response = await fetch(`/api/progress/${currentJobId}`)
        if (response.ok) {
          const jobStatus: JobStatus = await response.json()
          setProcessingStages(jobStatus.stages)
          
          // Check if job is complete
          if (jobStatus.status === "completed" || jobStatus.status === "error") {
            setIsProcessing(false)
            setCurrentJobId(null)
            
            // Show success or error message
            if (jobStatus.status === "completed") {
              // Could add a toast notification here
              console.log("Pipeline completed successfully")
            } else {
              // Get error message from the failed stage if available
              const failedStage = Object.values(jobStatus.stages).find(
                stage => stage.status === "error"
              )
              const errorMessage = failedStage?.message || "Pipeline failed. Check the logs for details."
              setError(errorMessage)
            }
            
            // Stop polling immediately
            return
          }
        } else {
          console.error("Failed to get progress:", response.status, response.statusText)
        }
      } catch (err) {
        console.error("Failed to poll progress:", err)
        // Don't set error here as it might be a temporary network issue
      }
    }

    // Poll immediately and then every 1.5 seconds for more responsive updates
    pollProgress()
    const interval = setInterval(pollProgress, 1500)
    return () => clearInterval(interval)
  }, [currentJobId, isProcessing])

  // Effect to get current input directory
  useEffect(() => {
    const getInputDirectory = async () => {
      try {
        const response = await fetch('/api/input-directory')
        if (response.ok) {
          const data = await response.json()
          setCurrentInputDir(data.input_directory)
        }
      } catch (err) {
        console.error("Failed to get input directory:", err)
      }
    }

    getInputDirectory()
  }, [])

  // Handlers
  const handleGitHubSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!githubOrg.trim()) return
    
    setIsProcessing(true)
    setError(null)
    setProcessingStages({})
    
    try {
      const response = await fetch("/api/organizations/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: githubOrg }),
      })

      if (!response.ok) {
        throw new Error("Failed to start analysis")
      }

      const data = await response.json()
      setCurrentJobId(data.job_id)
      
      // The main useEffect will handle polling automatically
      
    } catch (err) {
      setError(err instanceof Error ? err.message : "An error occurred")
      setIsProcessing(false)
    }
  }

  const handleFolderUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files
    if (files && files.length > 0) {
      setUploadedFiles(Array.from(files))
      setUploadProgress(0)
      setIsProcessing(true)
      setError(null)
      setProcessingStages({})
      
      try {
        // Create FormData for upload
        const formData = new FormData()
        Array.from(files).forEach((file) => {
          formData.append('files', file)
        })
        
        // Upload files to backend
        const response = await fetch('/api/upload/organization', {
          method: 'POST',
          body: formData,
        })
        
        if (!response.ok) {
          const errorData = await response.json()
          throw new Error(errorData.error || 'Upload failed')
        }
        
        const data = await response.json()
        setCurrentJobId(data.job_id)
        
        // The main useEffect will handle polling automatically
        
      } catch (err) {
        setError(err instanceof Error ? err.message : "Upload failed")
        setIsProcessing(false)
        setUploadedFiles([])
      }
    }
  }

  const handleFolderSelect = () => {
    folderInputRef.current?.click()
  }

  const removeFile = (index: number) => {
    setUploadedFiles((prev) => prev.filter((_, i) => i !== index))
  }

  const getStageIcon = (status: string) => {
    switch (status) {
      case "completed":
        return <CheckCircle className="h-4 w-4 text-green-600" aria-hidden="true" />
      case "processing":
        return <Loader2 className="h-4 w-4 text-blue-600 animate-spin" aria-hidden="true" />
      case "error":
        return <AlertCircle className="h-4 w-4 text-red-600" aria-hidden="true" />
      default:
        return <div className="h-4 w-4 rounded-full bg-gray-300" aria-hidden="true" />
    }
  }

  // Real progress tracking - no simulation needed

  return (
    <div className="space-y-6">
      {/* Error Alert */}
      {error && (
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Input Methods */}
      <Card>
        <CardHeader>
          <CardTitle>Data Input Methods</CardTitle>
          <CardDescription>
            Choose how to provide organization data for analysis
          </CardDescription>
        </CardHeader>
        <CardContent>
          <Tabs defaultValue="github" className="w-full">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="github" className="flex items-center gap-2">
                <Github className="h-4 w-4" />
                GitHub Organization
              </TabsTrigger>
              <TabsTrigger value="folder" className="flex items-center gap-2">
                <FolderOpen className="h-4 w-4" />
                Local Folder
              </TabsTrigger>
            </TabsList>

            <TabsContent value="github" className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="github-org" className="text-sm font-medium">
                  GitHub Organization Name
                </label>
                <form onSubmit={handleGitHubSubmit} className="flex gap-2">
                  <Input
                    id="github-org"
                    type="text"
                    placeholder="e.g., facebook, microsoft, google"
                    value={githubOrg}
                    onChange={(e) => setGithubOrg(e.target.value)}
                    disabled={isProcessing}
                    className="flex-1"
                    aria-label="GitHub organization name"
                  />
                  <Button type="submit" disabled={!githubOrg.trim() || isProcessing}>
                    {isProcessing ? (
                      <>
                        <Loader2 className="h-4 w-4 animate-spin mr-2" />
                        Analyzing...
                      </>
                    ) : (
                      "Analyze"
                    )}
                  </Button>
                </form>
                <p className="text-xs text-muted-foreground">
                  Enter a GitHub organization name to analyze all public repositories
                </p>
              </div>
            </TabsContent>

            <TabsContent value="folder" className="space-y-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Local Organization Folder</label>
                <div className="flex gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleFolderSelect}
                    disabled={isProcessing}
                    className="flex-1"
                  >
                    <FolderOpen className="h-4 w-4 mr-2" />
                    Select Folder
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={() => setUploadedFiles([])}
                    disabled={uploadedFiles.length === 0 || isProcessing}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  Select a local folder containing organization repositories
                </p>

                <input
                  ref={el => {
                    if (el) {
                      (el as HTMLInputElement).webkitdirectory = true;
                      if (folderInputRef) folderInputRef.current = el;
                    }
                  }}
                  type="file"
                  multiple
                  onChange={handleFolderUpload}
                  className="hidden"
                  accept=".js,.ts,.jsx,.tsx,.py,.java,.go,.rs,.cpp,.c,.h,.md,.txt,.json,.yaml,.yml"
                  aria-label="Organization folder input"
                />

                {uploadedFiles.length > 0 && (
                  <div className="space-y-4">
                    <div className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2">
                      <h4 className="font-medium">Organization Files ({uploadedFiles.length})</h4>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setUploadedFiles([])}
                        aria-label="Clear all uploaded files"
                      >
                        Clear All
                      </Button>
                    </div>

                    {uploadProgress > 0 && uploadProgress < 100 && (
                      <div
                        className="space-y-2"
                        role="progressbar"
                        aria-valuenow={uploadProgress}
                        aria-valuemin={0}
                        aria-valuemax={100}
                      >
                        <div className="flex justify-between text-sm">
                          <span>Upload Progress</span>
                          <span>{uploadProgress}%</span>
                        </div>
                        <Progress value={uploadProgress} aria-label={`Upload progress: ${uploadProgress}%`} />
                      </div>
                    )}

                    <div className="grid gap-2 max-h-40 overflow-y-auto">
                      {uploadedFiles.slice(0, 10).map((file, index) => (
                        <div
                          key={index}
                          className="flex items-center justify-between p-2 bg-muted/50 rounded text-sm"
                        >
                          <div className="flex items-center gap-2 min-w-0 flex-1">
                            <FileText className="h-4 w-4 flex-shrink-0" />
                            <span className="truncate">{file.name}</span>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => removeFile(index)}
                            aria-label={`Remove ${file.name}`}
                          >
                            <X className="h-3 w-3" />
                          </Button>
                        </div>
                      ))}
                      {uploadedFiles.length > 10 && (
                        <p className="text-xs text-muted-foreground text-center">
                          ... and {uploadedFiles.length - 10} more files
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>

      {/* Current Input Directory */}
      {currentInputDir && (
        <Card>
          <CardHeader>
            <CardTitle>Current Input Directory</CardTitle>
            <CardDescription>
              The directory currently being analyzed
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2 p-2 bg-muted rounded text-sm font-mono">
              <FolderOpen className="h-4 w-4 text-blue-600" />
              <span className="truncate">{currentInputDir}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Processing Status */}
      {isProcessing && Object.keys(processingStages).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <RefreshCw className="h-5 w-5 animate-spin" aria-hidden="true" />
              Web Development Analysis Pipeline
            </CardTitle>
            <CardDescription>Real-time progress of knowledge extraction and semantic analysis</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4" role="list" aria-label="Processing stages">
              {stages.map((stage) => {
                const stageData = processingStages[stage.key]
                if (!stageData) return null

                return (
                  <div key={stage.key} className="space-y-2" role="listitem">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 min-w-0 flex-1">
                        {getStageIcon(stageData.status)}
                        <div className="min-w-0 flex-1">
                          <h4 className="font-medium text-sm">{stage.label}</h4>
                          <p className="text-xs text-muted-foreground">{stage.description}</p>
                          {stageData.message && (
                            <p className="text-xs text-blue-600 mt-1" role="status" aria-live="polite">
                              {stageData.message}
                            </p>
                          )}
                        </div>
                      </div>
                      <div className="text-right flex-shrink-0">
                        <Badge
                          variant={
                            stageData.status === "completed"
                              ? "default"
                              : stageData.status === "error"
                                ? "destructive"
                                : "secondary"
                          }
                        >
                          {stageData.status}
                        </Badge>
                        {stageData.status === "processing" && (
                          <div className="text-xs text-muted-foreground mt-1">{stageData.progress}%</div>
                        )}
                      </div>
                    </div>
                    {stageData.status === "processing" && (
                      <Progress
                        value={stageData.progress}
                        className="h-2"
                        aria-label={`${stage.label} progress: ${stageData.progress}%`}
                      />
                    )}
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Quick Start Guide */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Start Guide</CardTitle>
          <CardDescription>
            Get started with semantic web knowledge management
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <h4 className="font-medium text-sm">1. Input Data</h4>
              <p className="text-xs text-muted-foreground">
                Provide GitHub organization name or upload local repository folder
              </p>
            </div>
            <div className="space-y-2">
              <h4 className="font-medium text-sm">2. Analysis Pipeline</h4>
              <p className="text-xs text-muted-foreground">
                Automated extraction of code, documentation, and git history
              </p>
            </div>
            <div className="space-y-2">
              <h4 className="font-medium text-sm">3. Knowledge Graph</h4>
              <p className="text-xs text-muted-foreground">
                Semantic annotation creates interconnected knowledge graph
              </p>
            </div>
            <div className="space-y-2">
              <h4 className="font-medium text-sm">4. Explore & Search</h4>
              <p className="text-xs text-muted-foreground">
                Use semantic search and visualization tools to explore knowledge
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
