const KEY = 'hoplogic-actor-name'

export function actorName(): string {
  try {
    return sessionStorage.getItem(KEY)?.trim() ?? ''
  } catch {
    return ''
  }
}

export function rememberActor(name: string): void {
  sessionStorage.setItem(KEY, name.trim())
}
