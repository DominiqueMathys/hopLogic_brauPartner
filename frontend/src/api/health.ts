export type HealthResult =
  | { ok: true; application?: string }
  | { ok: false }

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

export async function fetchHealth(path: string): Promise<HealthResult> {
  try {
    const response = await fetch(path)
    if (!response.ok) {
      return { ok: false }
    }

    const body: unknown = await response.json()
    if (!isRecord(body) || body.status !== 'ok' || typeof body.service !== 'string') {
      return { ok: false }
    }

    return {
      ok: true,
      application: typeof body.application === 'string' ? body.application : undefined,
    }
  } catch {
    return { ok: false }
  }
}
