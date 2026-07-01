import React, { useState } from 'react';

interface ImageWithFallbackProps extends React.ImgHTMLAttributes<HTMLImageElement> {
  fallbackSrc?: string;
}

export const ImageWithFallback: React.FC<ImageWithFallbackProps> = ({
  src,
  fallbackSrc,
  alt,
  className,
  ...props
}) => {
  const [failedSrc, setFailedSrc] = useState<string | undefined>();
  const imgSrc = src && src !== failedSrc ? src : fallbackSrc;

  if (!imgSrc) {
    return (
      <div className={`flex items-center justify-center bg-slate-50 text-xs text-slate-300 ${className || ''}`}>
        Chưa có ảnh
      </div>
    );
  }

  return (
    <img
      src={imgSrc}
      alt={alt}
      className={className}
      onError={() => setFailedSrc(src)}
      {...props}
    />
  );
};
