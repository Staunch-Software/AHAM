import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Download, ExternalLink, FileText, Image as ImageIcon, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Button, Card, ErrorBox, Skeleton } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { useAuth } from '../../services/auth'
import { formatBytes } from '../../utils/imageProcessing'
import { DocumentAttachModal } from './DocumentAttachModal'

export interface AttachedDoc {
  id: string
  entry_id: string
  category: string
  sub_type: string | null
  file_name: string
  mime_type: string
  size_bytes: number
  notes: string | null
  created_at: string | null
  uploaded_by: string
  uploaded_by_name: string | null
  url: string
}

const CATEGORY_COLORS: Record<string, { bg: string; text: string }> = {
  kyc: { bg: 'bg-emerald-50 border-emerald-200', text: 'text-emerald-700' },
  income: { bg: 'bg-blue-50 border-blue-200', text: 'text-blue-700' },
  property: { bg: 'bg-amber-50 border-amber-200', text: 'text-amber-700' },
  application: { bg: 'bg-purple-50 border-purple-200', text: 'text-purple-700' },
  other: { bg: 'bg-slate-50 border-slate-200', text: 'text-slate-700' },
}

interface Props {
  entryId: string
  entryCode: string
  readOnly?: boolean
}

export function DocumentGallery({ entryId, entryCode, readOnly }: Props) {
  const qc = useQueryClient()
  const { me, can } = useAuth()
  const [modalOpen, setModalOpen] = useState(false)
  const [previewDoc, setPreviewDoc] = useState<AttachedDoc | null>(null)

  // Document upload/attachment is restricted exclusively to Branch Manager and Sales Officer
  const canManage = can('documents.manage') || ['branch_manager', 'sales_officer'].includes(me?.role ?? '')
  // Document viewing is applicable to Regional Manager, Cluster Manager, Business Manager, System Admin, BM, and SO
  const canView =
    can('documents.view') ||
    [
      'sales_officer',
      'branch_manager',
      'cluster_manager',
      'region_manager',
      'business_manager',
      'admin',
      'product_manager',
    ].includes(me?.role ?? '')

  const isReadOnly = readOnly !== undefined ? readOnly : !canManage

  const { data: docs, isLoading, error } = useQuery<AttachedDoc[]>({
    queryKey: ['entry-documents', entryId],
    queryFn: async () => (await api.get<AttachedDoc[]>(`/entries/${entryId}/documents`)).data,
    enabled: canView,
  })

  const del = useMutation({
    mutationFn: (docId: string) => api.delete(`/entries/${entryId}/documents/${docId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['entry-documents', entryId] })
    },
  })

  if (!canView) {
    return null
  }

  return (
    <Card
      title="Attached Documents & Certificates"
      subtitle={
        isReadOnly
          ? 'Customer KYC, income statements, property certificates, and agreements (read-only view).'
          : 'Customer KYC, income statements, property certificates, and scanned agreements.'
      }
      actions={
        !isReadOnly ? (
          <Button small onClick={() => setModalOpen(true)}>
            <Plus size={14} /> Attach / Scan Document
          </Button>
        ) : undefined
      }
    >
      <ErrorBox error={error ? errorMessage(error) : null} />

      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 p-4">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      ) : !docs || docs.length === 0 ? (
        <div className="p-6 text-center text-slate-500 space-y-2">
          <FileText size={32} className="mx-auto text-slate-300" />
          <p className="text-sm font-medium">No documents attached yet.</p>
          <p className="text-xs text-slate-400">
            {!isReadOnly
              ? 'Use the "Attach / Scan Document" button to upload or photograph customer documents.'
              : 'Documents can be uploaded by the Branch Manager or Sales Officer.'}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 p-4">
          {docs.map((d) => {
            const cat = CATEGORY_COLORS[d.category] || CATEGORY_COLORS.other
            const isPdf = d.mime_type.includes('pdf')

            return (
              <div
                key={d.id}
                className="flex flex-col justify-between rounded-xl border border-slate-200 bg-white p-3 shadow-xs hover:border-brand-300 transition-all"
              >
                <div>
                  <div className="flex items-center justify-between gap-2">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-semibold border ${cat.bg} ${cat.text}`}
                    >
                      {d.sub_type || d.category.toUpperCase()}
                    </span>
                    <span className="text-[11px] text-slate-400 font-mono">
                      {formatBytes(d.size_bytes)}
                    </span>
                  </div>

                  <div className="mt-2 flex items-start gap-2.5">
                    <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-slate-100 text-slate-600">
                      {isPdf ? <FileText size={18} /> : <ImageIcon size={18} />}
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="truncate text-xs font-semibold text-slate-800" title={d.file_name}>
                        {d.file_name}
                      </div>
                      <div className="text-[11px] text-slate-500">
                        {d.uploaded_by_name ? `By ${d.uploaded_by_name}` : 'Uploaded'} ·{' '}
                        {d.created_at ? new Date(d.created_at).toLocaleDateString() : ''}
                      </div>
                    </div>
                  </div>

                  {d.notes && (
                    <p className="mt-2 text-xs text-slate-600 line-clamp-2 bg-slate-50 p-1.5 rounded">
                      {d.notes}
                    </p>
                  )}
                </div>

                <div className="mt-3 flex items-center justify-between border-t border-slate-100 pt-2 text-xs">
                  <a
                    href={d.url}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex items-center gap-1 font-semibold text-brand-700 hover:text-brand-900"
                  >
                    <ExternalLink size={13} /> View
                  </a>

                  <div className="flex items-center gap-2">
                    <a
                      href={d.url.replace('/view', '/download')}
                      download={d.file_name}
                      className="inline-flex items-center gap-1 text-slate-500 hover:text-slate-800"
                      title="Download document"
                    >
                      <Download size={13} />
                    </a>
                    {!isReadOnly && (
                      <button
                        type="button"
                        onClick={() => {
                          if (window.confirm(`Delete document "${d.file_name}"?`)) {
                            del.mutate(d.id)
                          }
                        }}
                        className="text-slate-400 hover:text-roof-600 transition-colors"
                        title="Delete document"
                      >
                        <Trash2 size={13} />
                      </button>
                    )}
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}

      {modalOpen && (
        <DocumentAttachModal
          entryId={entryId}
          entryCode={entryCode}
          onClose={() => setModalOpen(false)}
        />
      )}
    </Card>
  )
}
