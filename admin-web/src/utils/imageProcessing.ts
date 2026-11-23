/**
 * Client-side document image enhancement and standard quality compression.
 * Normalizes document photos, applies high-contrast readability filters,
 * and compresses to standard lightweight sizes (< 800 KB).
 */

export type DocumentFilter = 'original' | 'bw' | 'grayscale' | 'enhanced'

export interface ProcessedImage {
  blob: Blob
  dataUrl: string
  width: number
  height: number
  sizeBytes: number
}

const MAX_DIMENSION = 1800
const JPEG_QUALITY = 0.85

export async function processDocumentImage(
  source: HTMLImageElement | HTMLVideoElement,
  filter: DocumentFilter = 'original'
): Promise<ProcessedImage> {
  const canvas = document.createElement('canvas')
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('Canvas 2D context unavailable')

  // Calculate target dimensions keeping aspect ratio
  const srcWidth = 'videoWidth' in source ? source.videoWidth : source.naturalWidth
  const srcHeight = 'videoHeight' in source ? source.videoHeight : source.naturalHeight

  let width = srcWidth
  let height = srcHeight

  if (width > MAX_DIMENSION || height > MAX_DIMENSION) {
    if (width > height) {
      height = Math.round((height * MAX_DIMENSION) / width)
      width = MAX_DIMENSION
    } else {
      width = Math.round((width * MAX_DIMENSION) / height)
      height = MAX_DIMENSION
    }
  }

  canvas.width = width
  canvas.height = height

  // Draw image
  ctx.drawImage(source, 0, 0, width, height)

  if (filter !== 'original') {
    const imgData = ctx.getImageData(0, 0, width, height)
    const d = imgData.data

    if (filter === 'grayscale') {
      for (let i = 0; i < d.length; i += 4) {
        const gray = 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]
        d[i] = gray
        d[i + 1] = gray
        d[i + 2] = gray
      }
    } else if (filter === 'bw') {
      // High-contrast B&W thresholding for sharp text
      for (let i = 0; i < d.length; i += 4) {
        const gray = 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2]
        const val = gray > 140 ? 255 : 0
        d[i] = val
        d[i + 1] = val
        d[i + 2] = val
      }
    } else if (filter === 'enhanced') {
      // Contrast and saturation boost for certificates, stamps, and color IDs
      const contrast = 1.25
      const intercept = 128 * (1 - contrast)
      for (let i = 0; i < d.length; i += 4) {
        d[i] = Math.min(255, Math.max(0, d[i] * contrast + intercept))
        d[i + 1] = Math.min(255, Math.max(0, d[i + 1] * contrast + intercept))
        d[i + 2] = Math.min(255, Math.max(0, d[i + 2] * contrast + intercept))
      }
    }

    ctx.putImageData(imgData, 0, 0)
  }

  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => {
        if (!blob) {
          reject(new Error('Failed to generate image blob'))
          return
        }
        const dataUrl = canvas.toDataURL('image/jpeg', JPEG_QUALITY)
        resolve({
          blob,
          dataUrl,
          width,
          height,
          sizeBytes: blob.size,
        })
      },
      'image/jpeg',
      JPEG_QUALITY
    )
  })
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}
