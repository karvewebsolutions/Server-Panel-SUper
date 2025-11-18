"use client";

import { useRouter } from "next/navigation";
import { useTransition } from "react";

import { ackAlert } from "../../lib/api";

interface Props {
  id: number;
  disabled?: boolean;
}

export function AckButton({ id, disabled }: Props) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  const handleAck = () => {
    startTransition(async () => {
      await ackAlert(id);
      router.refresh();
    });
  };

  return (
    <button
      onClick={handleAck}
      disabled={disabled || isPending}
      className="text-xs px-2 py-1 rounded bg-emerald-800 text-white hover:bg-emerald-700 disabled:opacity-50"
    >
      {isPending ? "Acknowledging..." : "Acknowledge"}
    </button>
  );
}
