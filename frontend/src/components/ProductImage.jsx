import { useEffect, useState } from "react";

export default function ProductImage({ imageUrl, alt, className = "" }) {
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setFailed(false);
  }, [imageUrl]);

  if (!imageUrl || failed) {
    return (
      <div
        role="img"
        aria-label={`${alt} image unavailable`}
        className={`flex items-center justify-center rounded-lg border border-border bg-[#171c28] text-xl text-slate-500 ${className}`}
      >
        ▧
      </div>
    );
  }

  return (
    <img
      src={imageUrl}
      alt={alt}
      onError={() => setFailed(true)}
      className={`rounded-lg object-cover ${className}`}
    />
  );
}
