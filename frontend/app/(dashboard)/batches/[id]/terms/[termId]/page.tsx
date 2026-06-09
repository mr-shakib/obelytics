import { TermOfferingsClient } from "./term-offerings-client"

interface Props {
  params: Promise<{ id: string; termId: string }>
}

export default async function TermOfferingsPage({ params }: Props) {
  const { id, termId } = await params
  return <TermOfferingsClient batchId={id} termId={termId} />
}
