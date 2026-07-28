"use client"

import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs"
import { ReferenceDataManager } from "@/components/shared/reference-data-manager"
import { queryKeys } from "@/lib/query-keys"

export function ComplexAttributesClient() {
  return (
    <Tabs defaultValue="cp">
      <TabsList>
        <TabsTrigger value="cp">CEP</TabsTrigger>
        <TabsTrigger value="ca">Complex Activities</TabsTrigger>
        <TabsTrigger value="kp">Knowledge Profiles</TabsTrigger>
      </TabsList>

      <TabsContent value="cp" className="mt-4">
        <ReferenceDataManager
          title="Complex Engineering Problems"
          description="Manage the master list of Complex Engineering Problem (CEP) attributes."
          queryKey={queryKeys.refData.complexProblems}
          listPath="/ref-data/complex-problems"
          createPath="/ref-data/complex-problems"
          updatePath={(id) => `/ref-data/complex-problems/${id}`}
          entityLabel="Complex Engineering Problem"
          permission="config.manage"
          fields={[
            { name: "code", label: "Attribute Code", placeholder: "e.g. CEP1" },
            { name: "name", label: "Attribute Name", placeholder: "Short name", optional: true },
            { name: "description", label: "Characteristics", type: "textarea", placeholder: "Describe the characteristics..." },
          ]}
          columns={[
            { key: "code", header: "Code" },
            { key: "name", header: "Name" },
            { key: "description", header: "Characteristics", truncateAt: 80 },
          ]}
          exportFileName="complex_engineering_problems"
          bulkUpload={{
            importPath: "/ref-data/complex-problems/bulk-import",
            entityLabelPlural: "Complex Engineering Problems",
            templateFileName: "complex_engineering_problem_template",
            columns: [
              { key: "code", required: true, description: "Unique attribute code (max 20 chars)", example: "CEP1" },
              { key: "name", required: false, description: "Short name for the attribute (max 150 chars)", example: "Depth of knowledge required" },
              { key: "description", required: true, description: "The characteristics of this attribute", example: "Cannot be resolved without in-depth engineering knowledge" },
            ],
            sampleRows: [
              ["CEP1", "Depth of knowledge required", "Cannot be resolved without in-depth engineering knowledge at the level of one or more of WK3, WK4, WK5, WK6 or WK8"],
              ["CEP2", "Range of conflicting requirements", "Involves wide-ranging or conflicting technical, engineering and other issues"],
              ["CEP3", "Depth of analysis required", "Has no obvious solution and requires abstract thinking and originality in analysis"],
            ],
          }}
        />
      </TabsContent>

      <TabsContent value="ca" className="mt-4">
        <ReferenceDataManager
          title="Complex Activities"
          description="Manage the master list of Complex Activity (CA) attributes."
          queryKey={queryKeys.refData.complexActivities}
          listPath="/ref-data/complex-activities"
          createPath="/ref-data/complex-activities"
          updatePath={(id) => `/ref-data/complex-activities/${id}`}
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
          exportFileName="complex_activities"
          bulkUpload={{
            importPath: "/ref-data/complex-activities/bulk-import",
            entityLabelPlural: "Complex Activities",
            templateFileName: "complex_activity_template",
            columns: [
              { key: "code", required: true, description: "Unique attribute code (max 20 chars)", example: "CA1" },
              { key: "name", required: false, description: "Short name for the attribute (max 150 chars)", example: "Range of resources" },
              { key: "description", required: true, description: "The characteristics of this attribute", example: "Involves the use of diverse resources" },
            ],
            sampleRows: [
              ["CA1", "Range of resources", "Involves the use of diverse resources including people, money, equipment, materials, information and technologies"],
              ["CA2", "Level of interaction", "Requires resolution of significant problems arising from interactions between wide-ranging or conflicting technical, engineering or other issues"],
              ["CA3", "Innovation", "Involves creative use of engineering principles and research-based knowledge in novel ways"],
            ],
          }}
        />
      </TabsContent>

      <TabsContent value="kp" className="mt-4">
        <ReferenceDataManager
          title="Knowledge Profiles"
          description="Manage the master list of Knowledge Profile (KP) attributes."
          queryKey={queryKeys.refData.knowledgeProfiles}
          listPath="/ref-data/knowledge-profiles"
          createPath="/ref-data/knowledge-profiles"
          updatePath={(id) => `/ref-data/knowledge-profiles/${id}`}
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
          exportFileName="knowledge_profiles"
          bulkUpload={{
            importPath: "/ref-data/knowledge-profiles/bulk-import",
            entityLabelPlural: "Knowledge Profiles",
            templateFileName: "knowledge_profile_template",
            columns: [
              { key: "code", required: true, description: "Unique knowledge profile code (max 20 chars)", example: "KP1" },
              { key: "description", required: true, description: "What this knowledge profile covers", example: "A systematic, theory-based understanding of the natural sciences applicable to the discipline" },
            ],
            sampleRows: [
              ["KP1", "A systematic, theory-based understanding of the natural sciences applicable to the discipline"],
              ["KP2", "Conceptually-based mathematics, numerical analysis, statistics and formal aspects of computer and information science to support analysis and modelling applicable to the discipline"],
              ["KP3", "A systematic, theory-based formulation of engineering fundamentals required in the engineering discipline"],
            ],
          }}
        />
      </TabsContent>
    </Tabs>
  )
}
