import { useState } from 'react'
import { PhotoIcon } from '@heroicons/react/24/outline'
import { resolveBackendAssetUrl } from '@common/utils/resolveBackendAssetUrl'

type Props = {
  src: string
  alt: string
  className?: string
  /** Larger preview in gallery */
  variant?: 'thumb' | 'gallery'
}

export function IntegrityCheckScreenshot({ src, alt, className = '', variant = 'thumb' }: Props) {
  const [failed, setFailed] = useState(false)
  const url = resolveBackendAssetUrl(src)

  const box =
    variant === 'gallery'
      ? 'w-full h-40 flex flex-col items-center justify-center gap-1 text-gray-400 text-xs'
      : 'w-12 h-8 flex items-center justify-center'

  if (failed || !url) {
    return (
      <div className={`rounded border border-dashed border-gray-200 bg-gray-50 ${box} ${className}`}>
        <PhotoIcon className={variant === 'gallery' ? 'w-10 h-10 opacity-40' : 'w-4 h-4 opacity-50'} />
        {variant === 'gallery' && <span>Preview unavailable</span>}
      </div>
    )
  }

  return (
    <img
      src={url}
      alt={alt}
      className={className}
      loading="lazy"
      onError={() => setFailed(true)}
    />
  )
}
