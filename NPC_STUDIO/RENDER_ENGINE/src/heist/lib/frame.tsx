import React, { createContext, useContext } from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';

/**
 * Frame context with a signed base offset. Unlike <Sequence>, children may see negative local
 * frames (needed while a scene is entering under a transition before its nominal start).
 */
const Base = createContext(0);

export const useF = () => useCurrentFrame() - useContext(Base);

export const Rebase: React.FC<{ by: number; children: React.ReactNode }> = ({ by, children }) => {
  const parent = useContext(Base);
  return <Base.Provider value={parent + by}>{children}</Base.Provider>;
};

/** Renders children while local frame ∈ [from, from+len); children's frames start at 0. */
export const At: React.FC<{ from: number; len?: number; children: React.ReactNode; fill?: boolean }> = ({
  from,
  len = 1e9,
  children,
  fill = true,
}) => {
  const f = useF();
  if (f < from || f >= from + len) return null;
  const inner = <Rebase by={from}>{children}</Rebase>;
  return fill ? <AbsoluteFill>{inner}</AbsoluteFill> : inner;
};
