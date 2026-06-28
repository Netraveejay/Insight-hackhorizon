/** Agent positions — compact zig-zag layout that scales to fit the viewport */

export const PERSONA_W = 136;
export const PERSONA_H = 188;

export function agentCenter(id: string, layout: Record<string, { x: number; y: number }>) {
  const p = layout[id];
  if (!p) return { cx: 0, cy: 0 };
  return { cx: p.x + PERSONA_W / 2, cy: p.y + 72 };
}

export function agentAnchorRight(id: string, layout: Record<string, { x: number; y: number }>) {
  const p = layout[id];
  return p ? { x: p.x + PERSONA_W, y: p.y + 72 } : { x: 0, y: 0 };
}

export function agentAnchorLeft(id: string, layout: Record<string, { x: number; y: number }>) {
  const p = layout[id];
  return p ? { x: p.x, y: p.y + 72 } : { x: 0, y: 0 };
}

export function agentAnchorBottom(id: string, layout: Record<string, { x: number; y: number }>) {
  const p = layout[id];
  return p ? { x: p.x + PERSONA_W / 2, y: p.y + 118 } : { x: 0, y: 0 };
}

export function agentAnchorTop(id: string, layout: Record<string, { x: number; y: number }>) {
  const p = layout[id];
  return p ? { x: p.x + PERSONA_W / 2, y: p.y + 20 } : { x: 0, y: 0 };
}

/** Row1 L→R · row2 R→L · row3 L→R */
export const PERSONA_LAYOUT: Record<string, { x: number; y: number }> = {
  connector: { x: 12, y: 12 },
  ingestion: { x: 168, y: 12 },
  translation: { x: 324, y: 12 },
  scoring: { x: 480, y: 12 },
  clustering: { x: 636, y: 12 },
  detection: { x: 792, y: 12 },
  root_cause: { x: 792, y: 220 },
  sla: { x: 636, y: 220 },
  insight: { x: 324, y: 428 },
  output: { x: 480, y: 428 },
  explainability: { x: 636, y: 428 },
};

export const CANVAS_W = 940;
export const CANVAS_H = 620;
