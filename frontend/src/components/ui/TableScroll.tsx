import type { ReactNode } from "react";

interface TableScrollProps {
  children: ReactNode;
  className?: string;
}

export default function TableScroll({ children, className }: TableScrollProps) {
  return <div className={["table-scroll", className].filter(Boolean).join(" ")}>{children}</div>;
}

