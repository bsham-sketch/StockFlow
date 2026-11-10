import { useEffect, useState } from "react";
import api from "../api/client";

export default function ProductImage({ imageUrl, alt, className = "" }) {
  const [src, setSrc] = useState("");

  useEffect(() => {
    let active = true;
    let objectUrl = "";
    setSrc("");
    if (!imageUrl) return () => {};

    api.get(imageUrl, { responseType: "blob" })
      .then(({ data }) => {
        if (!active) return;
        objectUrl = URL.createObjectURL(data);
        setSrc(objectUrl);
      })
      .catch(() => {
        if (active) setSrc("unavailable");
      });

    return () => {
      active = false;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [imageUrl]);

  if (!src || src === "unavailable") {
    return (
      <div
        role="img"
        aria-label={src === "unavailable" ? `${alt} image unavailable` : `${alt} image`}
        className={`flex items-center justify-center rounded-lg border border-border bg-[#171c28] text-xs text-slate-500 ${className}`}
      >
        {src === "unavailable" ? "Unavailable" : "No image"}
      </div>
    );
  }

  return <img src={src} alt={alt} className={`rounded-lg object-cover ${className}`} />;
}
