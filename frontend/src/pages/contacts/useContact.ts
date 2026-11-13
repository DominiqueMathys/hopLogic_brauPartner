import { useEffect, useState } from 'react'
import { ApiError, fetchContact } from '../../api/crm.ts'
import type { Contact } from '../../domain/crm.ts'

export function useContact(contactId: string | undefined) {
  const [contact, setContact] = useState<Contact | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(true)

  useEffect(() => {
    if (!contactId) {
      return
    }
    let active = true
    void fetchContact(contactId)
      .then((result) => {
        if (!active) {
          return
        }
        setContact(result)
        setError(null)
        setPending(false)
      })
      .catch((caught: unknown) => {
        if (!active) {
          return
        }
        setContact(null)
        setError(caught instanceof ApiError ? caught.message : 'Die Verbindung zur API ist fehlgeschlagen.')
        setPending(false)
      })
    return () => {
      active = false
    }
  }, [contactId])

  return { contact, setContact, error, pending }
}
