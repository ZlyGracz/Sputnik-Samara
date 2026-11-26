import { useState } from "react";

export function Mascot() {
  const [imgFailed, setImgFailed] = useState(false);

  if (!imgFailed) {
    return (
      <div className="mascot-wrap">
        <img
          src="/mascot.png"
          alt="Маскот Спутник"
          className="mascot-img"
          onError={() => setImgFailed(true)}
        />
      </div>
    );
  }

  return (
    <div className="mascot-wrap" aria-label="Маскот Спутник">
      <svg
        className="mascot-img"
        viewBox="0 0 260 280"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          <linearGradient id="sputnikBlue" x1="40" y1="20" x2="220" y2="260" gradientUnits="userSpaceOnUse">
            <stop stopColor="#2E9BFF" />
            <stop offset="1" stopColor="#0A469C" />
          </linearGradient>
        </defs>
        {/* Антенна */}
        <path d="M185 68 L215 34 L198 92 Z" fill="url(#sputnikBlue)" />
        {/* Руки */}
        <path d="M62 155 C28 145 18 110 34 95 C46 84 62 108 76 135 Z" fill="url(#sputnikBlue)" />
        <path d="M198 158 C232 162 246 196 232 214 C220 228 202 206 188 182 Z" fill="url(#sputnikBlue)" />
        {/* Тело */}
        <ellipse cx="130" cy="205" rx="64" ry="58" fill="url(#sputnikBlue)" />
        {/* Знак S на груди */}
        <path
          d="M144 186 C134 176 116 180 116 192 C116 204 146 202 146 216 C146 228 128 232 116 222"
          stroke="#FFFFFF"
          strokeWidth="8"
          strokeLinecap="round"
        />
        {/* Голова */}
        <circle cx="130" cy="108" r="68" fill="url(#sputnikBlue)" />
        {/* Экран-лицо */}
        <ellipse cx="130" cy="112" rx="50" ry="42" fill="#FFFFFF" />
        {/* Глаза */}
        <circle cx="109" cy="108" r="13" fill="#0B1F3A" />
        <circle cx="151" cy="108" r="13" fill="#0B1F3A" />
        <circle cx="104" cy="103" r="4" fill="#FFFFFF" />
        <circle cx="146" cy="103" r="4" fill="#FFFFFF" />
        {/* Улыбка */}
        <path d="M116 128 Q130 142 144 128 Z" fill="#0B1F3A" />
      </svg>
    </div>
  );
}