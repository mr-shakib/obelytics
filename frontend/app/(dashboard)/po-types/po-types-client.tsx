"use client"

import { ReferenceDataManager } from "@/components/shared/reference-data-manager"
import { queryKeys } from "@/lib/query-keys"

export function PoTypesClient() {
  return (
    <ReferenceDataManager
      title="PO Types"
      description="Manage the master list of Program Outcome (PO) types."
      queryKey={queryKeys.refData.poTypes}
      listPath="/config/po-types"
      createPath="/config/po-types"
      updatePath={(id) => `/config/po-types/${id}`}
      entityLabel="PO Type"
      permission="config.manage"
      fields={[
        { name: "name", label: "Name", placeholder: "e.g. Generic" },
        { name: "description", label: "Description", type: "textarea", placeholder: "Optional", optional: true },
      ]}
      columns={[
        { key: "name", header: "Name" },
        { key: "description", header: "Description" },
      ]}
    />
  )
}
