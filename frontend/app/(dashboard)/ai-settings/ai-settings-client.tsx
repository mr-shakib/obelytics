"use client"

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { CheckCircle2, CircleAlert, Loader2, ShieldCheck } from "lucide-react"
import { toast } from "sonner"

import { PageHeader } from "@/components/shared/page-header"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { queryKeys } from "@/lib/query-keys"

import { type AIUsage, aiApi, type Feature, type FeatureSetting, type ProviderName, type ProviderStatus } from "./api"

const USAGE_DAYS = 30
const DEFAULT = "default"

const FEATURES: Record<Feature, { title: string; description: string }> = {
  integrity: {
    title: "Assessment integrity auditor",
    description: "Reads question papers and judges each question's Bloom level and course outcome.",
  },
  copilot: {
    title: "OBE Copilot",
    description: "Answers questions about your curriculum and outcomes in chat.",
  },
}

const PROVIDER_LABEL: Record<ProviderName, string> = {
  local: "Local model",
  hosted: "Hosted model",
  off: "Off",
}

export function AISettingsClient() {
  const qc = useQueryClient()
  const { data: settings, isLoading } = useQuery({ queryKey: queryKeys.ai.settings, queryFn: aiApi.settings })
  const { data: usage } = useQuery({
    queryKey: queryKeys.ai.usage(USAGE_DAYS),
    queryFn: () => aiApi.usage(USAGE_DAYS),
  })

  const update = useMutation({
    mutationFn: ({ feature, provider }: { feature: Feature; provider: ProviderName | null }) =>
      aiApi.updateSettings({ [`${feature}_provider`]: provider }),
    onSuccess: (data, { feature }) => {
      qc.setQueryData(queryKeys.ai.settings, data)
      const effective = data.features.find((f) => f.feature === feature)?.effective
      toast.success(`${FEATURES[feature].title}: ${effective ? PROVIDER_LABEL[effective] : "updated"}`)
    },
  })

  const providers = new Map(settings?.providers.map((p) => [p.name, p]))

  return (
    <div className="max-w-5xl space-y-6">
      <PageHeader
        title="AI Settings"
        description="Choose which model each AI feature uses. Every call goes through one gateway that logs it; AI never changes marks or attainment."
      />

      <Card>
        <CardHeader>
          <CardTitle>Features</CardTitle>
          <CardDescription>
            A local model keeps all data on your server. With a hosted model, emails, phone numbers,
            student IDs and known names are removed before anything is sent.
          </CardDescription>
        </CardHeader>
        <CardContent className="divide-y">
          {isLoading || !settings ? (
            <div className="h-24 animate-pulse rounded-md bg-muted" />
          ) : (
            settings.features.map((feature) => (
              <FeatureRow
                key={feature.feature}
                setting={feature}
                provider={feature.effective === "off" ? undefined : providers.get(feature.effective)}
                pending={update.isPending && update.variables?.feature === feature.feature}
                onChange={(provider) => update.mutate({ feature: feature.feature, provider })}
              />
            ))
          )}
        </CardContent>
      </Card>

      <div className="grid gap-4 md:grid-cols-2">
        {settings?.providers.map((provider) => <ProviderCard key={provider.name} provider={provider} />)}
      </div>

      <UsageCard usage={usage} />
    </div>
  )
}

function FeatureRow({
  setting,
  provider,
  pending,
  onChange,
}: {
  setting: FeatureSetting
  provider: ProviderStatus | undefined
  pending: boolean
  onChange: (provider: ProviderName | null) => void
}) {
  const info = FEATURES[setting.feature]
  const notReady = provider !== undefined && (!provider.configured || provider.reachable === false)
  return (
    <div className="flex flex-col gap-3 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between">
      <div className="space-y-1">
        <p className="font-medium">{info.title}</p>
        <p className="text-sm text-muted-foreground">{info.description}</p>
        {notReady && (
          <p className="flex items-center gap-1 text-xs text-amber-700 dark:text-amber-400">
            <CircleAlert className="size-3" />
            The {provider.name} provider is not ready, so this feature will not work until it is.
          </p>
        )}
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {pending && <Loader2 className="size-4 animate-spin text-muted-foreground" />}
        <Select
          value={setting.chosen ?? DEFAULT}
          disabled={pending}
          onValueChange={(value) => onChange(value === DEFAULT ? null : (value as ProviderName))}
        >
          <SelectTrigger className="w-full sm:w-64">
            <SelectValue>
              {setting.chosen
                ? PROVIDER_LABEL[setting.chosen]
                : `Server default: ${PROVIDER_LABEL[setting.default]}`}
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={DEFAULT}>Server default: {PROVIDER_LABEL[setting.default]}</SelectItem>
            <SelectItem value="local">{PROVIDER_LABEL.local}</SelectItem>
            <SelectItem value="hosted">{PROVIDER_LABEL.hosted}</SelectItem>
            <SelectItem value="off">{PROVIDER_LABEL.off}</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  )
}

function ProviderCard({ provider }: { provider: ProviderStatus }) {
  const ready = provider.configured && provider.reachable !== false
  const missing =
    provider.installed_models != null
      ? Object.values(provider.models).filter(
          (m): m is string => !!m && !provider.installed_models?.includes(m),
        )
      : []
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2">
          {provider.name === "local" ? "Local model" : "Hosted model"}
          <Badge variant={ready ? "secondary" : "outline"}>
            {ready ? <CheckCircle2 className="text-emerald-600" /> : <CircleAlert className="text-amber-600" />}
            {!provider.configured ? "Not configured" : provider.reachable === false ? "Not reachable" : "Ready"}
          </Badge>
        </CardTitle>
        <CardDescription>
          {provider.external ? (
            <span className="flex items-center gap-1">
              <ShieldCheck className="size-3.5" /> External service: personal data is redacted before sending.
            </span>
          ) : (
            "Runs on infrastructure you control: data stays on your servers."
          )}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2 text-sm">
        {(["text", "vision", "chat"] as const).map((kind) => (
          <div key={kind} className="flex justify-between gap-3">
            <span className="text-muted-foreground">
              {kind === "text" ? "Text" : kind === "vision" ? "Reading photos" : "Chat"}
            </span>
            <span className="font-mono text-xs">{provider.models[kind] ?? "not set"}</span>
          </div>
        ))}
        {missing.length > 0 && (
          <Alert>
            <AlertDescription>
              Not installed on the model server yet: {missing.join(", ")}. Pull it with{" "}
              <code className="font-mono">ollama pull {missing[0]}</code>.
            </AlertDescription>
          </Alert>
        )}
        {!provider.configured && (
          <p className="text-xs text-muted-foreground">
            {provider.name === "hosted"
              ? "Set AI_HOSTED_BASE_URL, AI_HOSTED_API_KEY and the model names on the server."
              : "Set AI_LOCAL_BASE_URL on the server."}
          </p>
        )}
      </CardContent>
    </Card>
  )
}

function formatNumber(value: number) {
  return new Intl.NumberFormat(undefined, { notation: value >= 100_000 ? "compact" : "standard" }).format(value)
}

function UsageCard({ usage }: { usage: AIUsage | undefined }) {
  const tiles = usage
    ? [
        { label: "Model calls", value: formatNumber(usage.calls) },
        { label: "Failed calls", value: formatNumber(usage.errors) },
        { label: "Tokens in / out", value: `${formatNumber(usage.input_tokens)} / ${formatNumber(usage.output_tokens)}` },
        { label: "Personal data redacted", value: formatNumber(usage.redactions) },
        { label: "Estimated cost", value: `$${usage.cost_usd.toFixed(2)}` },
      ]
    : []
  return (
    <Card>
      <CardHeader>
        <CardTitle>Usage, last {USAGE_DAYS} days</CardTitle>
        <CardDescription>Every AI call in this organization, from the gateway&apos;s log.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {!usage ? (
          <div className="h-24 animate-pulse rounded-md bg-muted" />
        ) : (
          <>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
              {tiles.map((tile) => (
                <div key={tile.label} className="rounded-lg border p-3">
                  <p className="text-lg font-semibold tabular-nums">{tile.value}</p>
                  <p className="text-xs text-muted-foreground">{tile.label}</p>
                </div>
              ))}
            </div>
            {usage.rows.length === 0 ? (
              <p className="text-sm text-muted-foreground">No AI calls yet.</p>
            ) : (
              <div className="rounded-lg border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Feature</TableHead>
                      <TableHead>Provider · model</TableHead>
                      <TableHead className="text-right">Calls</TableHead>
                      <TableHead className="text-right">Failed</TableHead>
                      <TableHead className="text-right">Tokens in / out</TableHead>
                      <TableHead className="text-right">Avg time</TableHead>
                      <TableHead className="text-right">Cost</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {usage.rows.map((row) => (
                      <TableRow key={`${row.feature}-${row.provider}-${row.model}`}>
                        <TableCell>{FEATURES[row.feature as Feature]?.title ?? row.feature}</TableCell>
                        <TableCell className="font-mono text-xs">{row.provider} · {row.model}</TableCell>
                        <TableCell className="text-right tabular-nums">{formatNumber(row.calls)}</TableCell>
                        <TableCell className="text-right tabular-nums">{formatNumber(row.errors)}</TableCell>
                        <TableCell className="text-right tabular-nums">
                          {formatNumber(row.input_tokens)} / {formatNumber(row.output_tokens)}
                        </TableCell>
                        <TableCell className="text-right tabular-nums">{(row.avg_latency_ms / 1000).toFixed(1)} s</TableCell>
                        <TableCell className="text-right tabular-nums">${row.cost_usd.toFixed(4)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  )
}
