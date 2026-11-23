import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Camera, Check, FileText, Image as ImageIcon, RefreshCw, Sliders, Upload, X } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { Button, Dialog, ErrorBox, Field, Input, Select, Textarea } from '../../components/ui'
import { api, errorMessage } from '../../services/api'
import { type DocumentFilter, formatBytes, processDocumentImage, type ProcessedImage } from '../../utils/imageProcessing'

const CATEGORIES = [
  { value: 'kyc', label: 'KYC Document', subTypes: ['Aadhaar Card', 'PAN Card', 'Voter ID', 'Driving License', 'Passport'] },
  { value: 'income', label: 'Income Proof', subTypes: ['Salary Slip (Last 3 Mo)', 'Bank Statement (6 Mo)', 'ITR / Form 16', 'Cash Flow / P&L'] },
  { value: 'property', label: 'Property Document', subTypes: ['Sale Deed / Agreement', 'Patta / Khata Certificate', 'Encumbrance Certificate (EC)', 'Approved Building Plan', 'Tax Receipt'] },
  { value: 'application', label: 'Application Form', subTypes: ['Signed Application Form', 'Customer Photograph', 'Loan Agreement', 'Cheque / NACH Mandate'] },
  { value: 'other', label: 'Certificate / Other', subTypes: ['Legal Clearance', 'Valuation Report', 'NOC Certificate', 'Other'] },
]

interface Props {
  entryId: string
  entryCode: string
  onClose: () => void
  onSuccess?: () => void
}

export function DocumentAttachModal({ entryId, entryCode, onClose, onSuccess }: Props) {
  const qc = useQueryClient()
  const [tab, setTab] = useState<'upload' | 'camera'>('upload')

  // Form State
  const [category, setCategory] = useState('kyc')
  const [subType, setSubType] = useState('Aadhaar Card')
  const [customSubType, setCustomSubType] = useState('')
  const [notes, setNotes] = useState('')

  // File & Camera State
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [cameraActive, setCameraActive] = useState(false)
  const [cameraError, setCameraError] = useState<string | null>(null)
  const [capturedRaw, setCapturedRaw] = useState<string | null>(null)
  const [processed, setProcessed] = useState<ProcessedImage | null>(null)
  const [filter, setFilter] = useState<DocumentFilter>('original')
  const [processing, setProcessing] = useState(false)

  const videoRef = useRef<HTMLVideoElement | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)

  // Subtype presets
  const currentCategory = CATEGORIES.find((c) => c.value === category) || CATEGORIES[0]

  // Cleanup camera stream on unmount
  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((t) => t.stop())
      }
    }
  }, [])

  // Start Camera
  const startCamera = async () => {
    setCameraError(null)
    setCapturedRaw(null)
    setProcessed(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'environment', width: { ideal: 1920 }, height: { ideal: 1080 } },
        audio: false,
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
        await videoRef.current.play()
      }
      setCameraActive(true)
    } catch (err: any) {
      setCameraError(err.message || 'Cannot access device camera. Please check browser permissions.')
      setCameraActive(false)
    }
  }

  // Stop Camera
  const stopCamera = () => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop())
      streamRef.current = null
    }
    setCameraActive(false)
  }

  // Handle Tab Switch
  const switchTab = (nextTab: 'upload' | 'camera') => {
    setTab(nextTab)
    if (nextTab === 'camera') {
      setSelectedFile(null)
      startCamera()
    } else {
      stopCamera()
    }
  }

  // Capture Frame from Camera
  const captureFrame = async () => {
    if (!videoRef.current) return
    setProcessing(true)
    try {
      const res = await processDocumentImage(videoRef.current, filter)
      setProcessed(res)
      setCapturedRaw(res.dataUrl)
      stopCamera()
    } catch (e: any) {
      setCameraError(e.message || 'Failed to capture frame')
    } finally {
      setProcessing(false)
    }
  }

  // Retake
  const retake = () => {
    setCapturedRaw(null)
    setProcessed(null)
    startCamera()
  }

  // Change enhancement filter on captured image
  const applyFilter = async (nextFilter: DocumentFilter) => {
    setFilter(nextFilter)
    if (!capturedRaw) return
    setProcessing(true)
    try {
      const img = new Image()
      img.src = capturedRaw
      await new Promise((res) => { img.onload = res })
      const res = await processDocumentImage(img, nextFilter)
      setProcessed(res)
    } finally {
      setProcessing(false)
    }
  }

  // File selection
  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setSelectedFile(file)

    // If it's an image, preview and allow enhancement
    if (file.type.startsWith('image/')) {
      const img = new Image()
      img.src = URL.createObjectURL(file)
      await new Promise((res) => { img.onload = res })
      const res = await processDocumentImage(img, 'original')
      setProcessed(res)
      setCapturedRaw(res.dataUrl)
    } else {
      setProcessed(null)
      setCapturedRaw(null)
    }
  }

  // Upload Mutation
  const m = useMutation({
    mutationFn: async () => {
      const fd = new FormData()
      fd.append('category', category)
      const finalSubType = subType === 'Other' ? customSubType.trim() || 'Other' : subType
      if (finalSubType) fd.append('sub_type', finalSubType)
      if (notes.trim()) fd.append('notes', notes.trim())

      if (tab === 'camera' && processed) {
        fd.append('file', processed.blob, `${category}_${Date.now()}.jpg`)
      } else if (selectedFile) {
        // If image was enhanced/compressed, upload processed blob, else original file (e.g. PDF)
        if (processed && selectedFile.type.startsWith('image/')) {
          fd.append('file', processed.blob, selectedFile.name.replace(/\.[^/.]+$/, '') + '.jpg')
        } else {
          fd.append('file', selectedFile)
        }
      } else {
        throw new Error('Please choose a file or take a document photo')
      }

      const res = await api.post(`/entries/${entryId}/documents`, fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return res.data
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['entry-documents', entryId] })
      qc.invalidateQueries({ queryKey: ['entries'] })
      qc.invalidateQueries({ queryKey: ['branch-leads'] })
      stopCamera()
      onSuccess?.()
      onClose()
    },
  })

  const hasPayload = (tab === 'camera' && !!processed) || (tab === 'upload' && !!selectedFile)

  return (
    <Dialog title={`Attach Document · ${entryCode}`} onClose={() => { stopCamera(); onClose() }} wide>
      <ErrorBox error={m.error ? errorMessage(m.error) : cameraError} />

      {/* Mode Navigation */}
      <div className="flex border-b border-slate-200 mb-4">
        <button
          type="button"
          onClick={() => switchTab('upload')}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors ${
            tab === 'upload'
              ? 'border-brand-600 text-brand-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Upload size={16} /> File Upload (PDF / Image)
        </button>
        <button
          type="button"
          onClick={() => switchTab('camera')}
          className={`flex items-center gap-2 px-4 py-2.5 text-sm font-semibold border-b-2 transition-colors ${
            tab === 'camera'
              ? 'border-brand-600 text-brand-700'
              : 'border-transparent text-slate-500 hover:text-slate-800'
          }`}
        >
          <Camera size={16} /> Camera / Document Scanner
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Left Column: Capture / File Area */}
        <div className="space-y-3">
          {tab === 'upload' && (
            <div
              onClick={() => fileInputRef.current?.click()}
              className="flex flex-col items-center justify-center p-6 border-2 border-dashed border-slate-300 rounded-xl hover:border-brand-500 cursor-pointer bg-slate-50 hover:bg-white transition-all text-center min-h-[220px]"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="application/pdf,image/jpeg,image/png,image/webp"
                className="hidden"
                onChange={handleFileChange}
              />
              {selectedFile ? (
                <div className="space-y-2">
                  <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-600">
                    {selectedFile.type.includes('pdf') ? <FileText size={24} /> : <ImageIcon size={24} />}
                  </div>
                  <div className="font-medium text-slate-900 text-sm">{selectedFile.name}</div>
                  <div className="text-xs text-slate-500">{formatBytes(selectedFile.size)}</div>
                  <Button variant="secondary" small onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click() }}>
                    Choose different file
                  </Button>
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-brand-50 text-brand-600">
                    <Upload size={24} />
                  </div>
                  <div className="text-sm font-medium text-slate-800">Click to upload document or drag & drop</div>
                  <div className="text-xs text-slate-500">Supports PDF, JPG, PNG up to 15 MB</div>
                </div>
              )}
            </div>
          )}

          {tab === 'camera' && (
            <div className="relative rounded-xl overflow-hidden bg-slate-900 min-h-[240px] flex items-center justify-center">
              {cameraActive && !capturedRaw && (
                <>
                  <video ref={videoRef} autoPlay playsInline className="w-full h-64 object-cover" />
                  <div className="absolute bottom-3 inset-x-0 flex justify-center gap-3">
                    <Button variant="gold" onClick={captureFrame} disabled={processing}>
                      <Camera size={16} />
                      {processing ? 'Processing…' : 'Capture Certificate'}
                    </Button>
                  </div>
                </>
              )}

              {capturedRaw && (
                <div className="relative w-full">
                  <img
                    src={processed?.dataUrl || capturedRaw}
                    alt="Captured document"
                    className="w-full h-64 object-contain bg-slate-950"
                  />
                  <div className="absolute top-2 right-2">
                    <Button variant="secondary" small onClick={retake}>
                      <RefreshCw size={14} />
                      Retake
                    </Button>
                  </div>
                </div>
              )}

              {!cameraActive && !capturedRaw && (
                <div className="p-6 text-center space-y-3">
                  <p className="text-sm text-slate-300">Camera preview is stopped.</p>
                  <Button variant="gold" onClick={startCamera}>
                    <Camera size={16} />
                    Open Camera
                  </Button>
                </div>
              )}
            </div>
          )}

          {/* Scanner Enhancement Filters (when an image is captured or selected) */}
          {processed && (
            <div className="rounded-xl border border-slate-200 p-3 bg-white space-y-2">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-700">
                <span className="flex items-center gap-1.5"><Sliders size={14} /> Document Scanner Filter</span>
                <span className="font-mono text-slate-500">{formatBytes(processed.sizeBytes)} · {processed.width}×{processed.height}</span>
              </div>
              <div className="grid grid-cols-4 gap-1.5">
                {[
                  ['original', 'Original'],
                  ['bw', 'Sharp B&W'],
                  ['grayscale', 'Grayscale'],
                  ['enhanced', 'Color Boost'],
                ].map(([f, label]) => (
                  <button
                    key={f}
                    type="button"
                    onClick={() => applyFilter(f as DocumentFilter)}
                    className={`py-1.5 text-xs font-medium rounded-lg border text-center transition-colors ${
                      filter === f
                        ? 'border-brand-600 bg-brand-50 text-brand-700 font-semibold'
                        : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column: Document Metadata */}
        <div className="space-y-3">
          <Field label="Document Category">
            <Select
              value={category}
              onChange={(e) => {
                const cat = e.target.value
                setCategory(cat)
                const c = CATEGORIES.find((x) => x.value === cat)
                if (c && c.subTypes.length > 0) setSubType(c.subTypes[0])
              }}
            >
              {CATEGORIES.map((c) => (
                <option key={c.value} value={c.value}>{c.label}</option>
              ))}
            </Select>
          </Field>

          <Field label="Document / Certificate Type">
            <Select value={subType} onChange={(e) => setSubType(e.target.value)}>
              {currentCategory.subTypes.map((st) => (
                <option key={st} value={st}>{st}</option>
              ))}
              <option value="Other">Other (type manually)</option>
            </Select>
          </Field>

          {subType === 'Other' && (
            <Field label="Specific Document Name">
              <Input
                placeholder="e.g. Electricity Bill, Salary Certificate"
                value={customSubType}
                onChange={(e) => setCustomSubType(e.target.value)}
              />
            </Field>
          )}

          <Field label="Notes (optional)">
            <Textarea
              rows={3}
              placeholder="e.g. Validated with original; verified by BM"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
          </Field>

          <div className="rounded-lg bg-slate-50 p-3 text-xs text-slate-600 space-y-1">
            <div className="font-semibold text-slate-700">Standard Image Quality Enabled:</div>
            <div>• Auto-scaled to standard resolution (~1800px max)</div>
            <div>• Preserves stamps, seals, and signatures for verification</div>
            <div>• Stored securely on S3-compatible cloud storage</div>
          </div>
        </div>
      </div>

      <div className="mt-5 flex justify-end gap-2 border-t border-slate-200 pt-4">
        <Button variant="secondary" onClick={() => { stopCamera(); onClose() }}>
          Cancel
        </Button>
        <Button
          disabled={!hasPayload || m.isPending}
          onClick={() => m.mutate()}
        >
          {m.isPending ? 'Uploading…' : 'Attach Document'}
        </Button>
      </div>
    </Dialog>
  )
}
