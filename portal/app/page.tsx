"use client"

import { DataInputPanel } from "@/components/data-input-panel"
import { useOrganization } from "@/components/organization-provider"
import { DashboardLayout } from "@/components/dashboard-layout"

export default function Page() {
  const { organization } = useOrganization()

  return (
    <DashboardLayout>
      <DataInputPanel />
    </DashboardLayout>
  )
}
