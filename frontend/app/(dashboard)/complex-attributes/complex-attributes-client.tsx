"use client"

import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { ReferenceDataManager } from "@/components/shared/reference-data-manager"
import { queryKeys } from "@/lib/query-keys"

export function ComplexAttributesClient() {
  return (
    <Tabs defaultValue="cp">
      <TabsList>
        <TabsTrigger value="cp">Complex Problems</TabsTrigger>
        <TabsTrigger value="ca">Complex Activities</TabsTrigger>
        <TabsTrigger value="kp">Knowledge Profiles</TabsTrigger>
      </TabsList>

      <TabsContent value="cp" className="mt-4">
        <ReferenceDataManager
          title="Complex Problems"
          description="Manage the master list of Complex Problem (CP) attributes."
          queryKey={queryKeys.refData.complexProblems}
          listPath="/config/complex-problems"
          createPath="/config/complex-problems"
          updatePath={(id) => `/config/complex-problems/${id}`}
          entityLabel="Complex Problem"
          permission="config.manage"
          fields={[
            { name: "code", label: "Attribute Code", placeholder: "e.g. CP1" },
            { name: "name", label: "Attribute Name", placeholder: "Short name", optional: true },
            { name: "description", label: "Characteristics", type: "textarea", placeholder: "Describe the characteristics..." },
          ]}
          columns={[
            { key: "code", header: "Code" },
            { key: "name", header: "Name" },
            { key: "description", header: "Characteristics", truncateAt: 80 },
          ]}
        />
      </TabsContent>

      <TabsContent value="ca" className="mt-4">
        <ReferenceDataManager
          title="Complex Activities"
          description="Manage the master list of Complex Activity (CA) attributes."
          queryKey={queryKeys.refData.complexActivities}
          listPath="/config/complex-activities"
          createPath="/config/complex-activities"
          updatePath={(id) => `/config/complex-activities/${id}`}
          entityLabel="Complex Activity"
          permission="config.manage"
          fields={[
            { name: "code", label: "Attribute Code", placeholder: "e.g. CA1" },
            { name: "name", label: "Attribute Name", placeholder: "Short name", optional: true },
            { name: "description", label: "Characteristics", type: "textarea", placeholder: "Describe the characteristics..." },
          ]}
          columns={[
            { key: "code", header: "Code" },
            { key: "name", header: "Name" },
            { key: "description", header: "Characteristics", truncateAt: 80 },
          ]}
        />
      </TabsContent>

      <TabsContent value="kp" className="mt-4">
        <ReferenceDataManager
          title="Knowledge Profiles"
          description="Manage the master list of Knowledge Profile (KP) attributes."
          queryKey={queryKeys.refData.knowledgeProfiles}
          listPath="/config/knowledge-profiles"
          createPath="/config/knowledge-profiles"
          updatePath={(id) => `/config/knowledge-profiles/${id}`}
          entityLabel="Knowledge Profile"
          permission="config.manage"
          fields={[
            { name: "code", label: "Code", placeholder: "e.g. KP1" },
            { name: "description", label: "Description", type: "textarea", placeholder: "Describe the knowledge profile..." },
          ]}
          columns={[
            { key: "code", header: "Code" },
            { key: "description", header: "Description", truncateAt: 80 },
          ]}
        />
      </TabsContent>
    </Tabs>
  )
}
