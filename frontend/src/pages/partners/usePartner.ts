import { useEffect, useState } from 'react'
import { ApiError, fetchPartner } from '../../api/partners.ts'
import type { Partner } from '../../domain/partners.ts'

export function usePartner(partnerId: string | undefined) {
  const [partner, setPartner] = useState<Partner | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(true)

  useEffect(() => {
    if (!partnerId) {
      return
    }
    let active = true
    void fetchPartner(partnerId)
      .then((result) => {
        if (!active) {
          return
        }
        setPartner(result)
        setError(null)
        setPending(false)
      })
      .catch((caught: unknown) => {
        if (!active) {
          return
        }
        setPartner(null)
        if (caught instanceof ApiError && (caught.status === 404 || caught.status === 422)) {
          setError('Der Vertriebspartner wurde nicht gefunden.')
        } else if (caught instanceof ApiError) {
          setError(caught.message)
        } else {
          setError('Die Verbindung zur API ist fehlgeschlagen.')
        }
        setPending(false)
      })
    return () => {
      active = false
    }
  }, [partnerId])

  return { partner, setPartner, error, pending }
}
