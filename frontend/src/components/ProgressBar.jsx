import React from 'react'

export function ProgressBar({ value }) {
  const bgClass =
    value > 80 ? 'bg-red-500' : value > 60 ? 'bg-yellow-500' : 'bg-green-500'

  return (
    <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
      <div
        className={`${bgClass} h-2 rounded-full`}
        style={{ width: `${value}%` }}
      />
    </div>
  )
}